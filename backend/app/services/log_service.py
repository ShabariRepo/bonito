"""
Platform Logging Service

Provides hierarchical, high-performance logging for the Bonito platform with:
- Async/non-blocking log emission
- Batching for high throughput
- External integration forwarding
- Circuit breaker pattern for reliability
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from collections import defaultdict

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.logging import PlatformLog, LogIntegration
from app.schemas.logging import LogEntry
from app.services.log_integrations import integration_registry

logger = logging.getLogger(__name__)


class LogBatch:
    """Manages batched log writes for performance."""
    
    def __init__(self, max_size: int = 100, max_age_seconds: int = 5):
        self.max_size = max_size
        self.max_age_seconds = max_age_seconds
        self.entries: List[PlatformLog] = []
        self.created_at = time.time()
        self.lock = asyncio.Lock()
    
    async def add_entry(self, entry: PlatformLog) -> bool:
        """Add entry to batch. Returns True if batch should be flushed."""
        async with self.lock:
            self.entries.append(entry)
            return (
                len(self.entries) >= self.max_size or
                time.time() - self.created_at >= self.max_age_seconds
            )
    
    async def get_entries(self) -> List[PlatformLog]:
        """Get and clear all entries from the batch."""
        async with self.lock:
            entries = self.entries.copy()
            self.entries.clear()
            self.created_at = time.time()
            return entries


class CircuitBreaker:
    """Circuit breaker for external integrations."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open
    
    def is_open(self) -> bool:
        """Check if circuit breaker is open (blocking requests)."""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
                return False
            return True
        return False
    
    def record_success(self):
        """Record a successful operation."""
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


class LogService:
    """High-performance logging service for the Bonito platform."""
    
    def __init__(self):
        self.batch = LogBatch()
        self.integration_circuit_breakers: Dict[str, CircuitBreaker] = defaultdict(CircuitBreaker)
        self.background_task: Optional[asyncio.Task] = None
        self.shutdown_event = asyncio.Event()
        self._start_background_processor()
    
    def _start_background_processor(self):
        """Start the background batch processing task."""
        if self.background_task and not self.background_task.done():
            return
        
        self.background_task = asyncio.create_task(self._batch_processor())
        logger.info("Started log service background processor")
    
    async def _batch_processor(self):
        """Background task to process log batches."""
        while not self.shutdown_event.is_set():
            try:
                # Check if batch should be flushed
                should_flush = (
                    time.time() - self.batch.created_at >= self.batch.max_age_seconds or
                    len(self.batch.entries) >= self.batch.max_size
                )
                
                if should_flush and self.batch.entries:
                    await self._flush_batch()
                
                # Sleep briefly before next check
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in log batch processor: {e}")
                await asyncio.sleep(5)  # Back off on errors
    
    async def _flush_batch(self):
        """Flush current batch to database and external integrations."""
        entries = await self.batch.get_entries()
        if not entries:
            return
        
        start_time = time.time()
        
        try:
            # Write to database
            async with get_db_session() as db:
                db.add_all(entries)
                await db.commit()
            
            # Forward to external integrations
            await self._forward_to_integrations(entries)
            
            logger.debug(
                f"Flushed {len(entries)} log entries in "
                f"{(time.time() - start_time) * 1000:.1f}ms"
            )
            
        except Exception as e:
            logger.error(f"Failed to flush log batch: {e}")
            # TODO: Implement dead letter queue for failed batches
    
    async def _forward_to_integrations(self, entries: List[PlatformLog]):
        """Forward log entries to configured external integrations."""
        # Group entries by organization for efficient integration lookup
        org_entries = defaultdict(list)
        for entry in entries:
            org_entries[entry.org_id].append(entry)
        
        # Process each organization's entries
        for org_id, org_logs in org_entries.items():
            try:
                await self._forward_org_logs(org_id, org_logs)
            except Exception as e:
                logger.error(f"Failed to forward logs for org {org_id}: {e}")
    
    async def _forward_org_logs(self, org_id: uuid.UUID, entries: List[PlatformLog]):
        """Forward logs for a specific organization to its integrations."""
        async with get_db_session() as db:
            # Get enabled integrations for this org
            result = await db.execute(
                select(LogIntegration).where(
                    and_(
                        LogIntegration.org_id == org_id,
                        LogIntegration.enabled == True
                    )
                )
            )
            integrations = result.scalars().all()
            
            # Forward to each integration
            for integration in integrations:
                await self._forward_to_integration(integration, entries)
    
    async def _forward_to_integration(self, integration: LogIntegration, entries: List[PlatformLog]):
        """Forward logs to a specific external integration."""
        integration_key = f"{integration.org_id}:{integration.id}"
        circuit_breaker = self.integration_circuit_breakers[integration_key]
        
        # Check circuit breaker
        if circuit_breaker.is_open():
            logger.debug(f"Skipping integration {integration.name} - circuit breaker open")
            return
        
        try:
            # Get integration handler
            handler = integration_registry.get_handler(integration.integration_type)
            if not handler:
                logger.warning(f"No handler found for integration type: {integration.integration_type}")
                return
            
            # Forward logs
            await handler.send_logs(integration, entries)
            circuit_breaker.record_success()
            
        except Exception as e:
            logger.error(f"Failed to forward logs to {integration.name}: {e}")
            circuit_breaker.record_failure()
    
    async def emit(
        self,
        org_id: uuid.UUID,
        log_type: str,
        event_type: str,
        severity: str,
        user_id: Optional[uuid.UUID] = None,
        resource_id: Optional[uuid.UUID] = None,
        resource_type: Optional[str] = None,
        action: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        cost: Optional[float] = None,
        trace_id: Optional[uuid.UUID] = None,
        message: Optional[str] = None
    ):
        """
        Emit a log entry to the platform logging system.
        
        This is the primary interface for logging throughout the platform.
        Logs are batched and processed asynchronously for high performance.
        
        Args:
            org_id: Organization ID (top level of hierarchy)
            log_type: Feature area (gateway, agent, auth, admin, kb, deployment, billing)
            event_type: Specific event within the feature area
            severity: Log severity (debug, info, warn, error, critical)
            user_id: User who performed the action (optional)
            resource_id: Resource being acted upon (optional)
            resource_type: Type of resource (optional)
            action: Action performed (optional)
            metadata: Event-specific structured data (optional)
            duration_ms: Operation duration in milliseconds (optional)
            cost: Cost associated with the operation (optional)
            trace_id: Distributed tracing ID (optional)
            message: Human-readable log message (optional)
        """
        try:
            # Create log entry
            entry = PlatformLog(
                org_id=org_id,
                log_type=log_type,
                event_type=event_type,
                severity=severity,
                user_id=user_id,
                resource_id=resource_id,
                resource_type=resource_type,
                action=action,
                metadata=metadata,
                duration_ms=duration_ms,
                cost=cost,
                trace_id=trace_id,
                message=message,
                created_at=datetime.now(timezone.utc)
            )
            
            # Add to batch
            should_flush = await self.batch.add_entry(entry)
            
            # Immediate flush for critical errors
            if severity == "critical" or should_flush:
                await self._flush_batch()
                
        except Exception as e:
            # Logging should never break the application
            logger.error(f"Failed to emit log entry: {e}")
    
    async def emit_gateway_request(
        self,
        org_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        model: str,
        provider: str,
        status: str,
        duration_ms: int,
        cost: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
        error_message: Optional[str] = None,
        trace_id: Optional[uuid.UUID] = None
    ):
        """Convenience method for logging gateway requests."""
        severity = "error" if status == "error" else "info"
        
        await self.emit(
            org_id=org_id,
            log_type="gateway",
            event_type="request",
            severity=severity,
            user_id=user_id,
            action="execute",
            metadata={
                "model": model,
                "provider": provider,
                "status": status,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "error_message": error_message
            },
            duration_ms=duration_ms,
            cost=cost,
            trace_id=trace_id,
            message=f"Gateway request to {model} via {provider} - {status}"
        )
    
    async def emit_auth_event(
        self,
        org_id: uuid.UUID,
        event_type: str,  # login, logout, token_refresh, sso_auth, failed_auth
        user_id: Optional[uuid.UUID],
        success: bool,
        metadata: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None
    ):
        """Convenience method for logging authentication events."""
        severity = "warn" if not success else "info"
        
        await self.emit(
            org_id=org_id,
            log_type="auth",
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            action="authenticate",
            metadata=metadata or {},
            message=message
        )
    
    async def emit_admin_action(
        self,
        org_id: uuid.UUID,
        admin_user_id: uuid.UUID,
        event_type: str,  # user_invite, role_change, config_change, policy_update
        target_user_id: Optional[uuid.UUID] = None,
        resource_id: Optional[uuid.UUID] = None,
        resource_type: Optional[str] = None,
        action: str = "update",
        metadata: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None
    ):
        """Convenience method for logging admin actions."""
        await self.emit(
            org_id=org_id,
            log_type="admin",
            event_type=event_type,
            severity="info",
            user_id=admin_user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            action=action,
            metadata=metadata or {},
            message=message
        )
    
    async def emit_kb_event(
        self,
        org_id: uuid.UUID,
        event_type: str,  # upload, search, delete, ingestion
        user_id: Optional[uuid.UUID],
        kb_id: Optional[uuid.UUID] = None,
        document_id: Optional[uuid.UUID] = None,
        action: str = "read",
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None
    ):
        """Convenience method for logging knowledge base events."""
        await self.emit(
            org_id=org_id,
            log_type="kb",
            event_type=event_type,
            severity="info",
            user_id=user_id,
            resource_id=kb_id or document_id,
            resource_type="kb" if kb_id else "document",
            action=action,
            duration_ms=duration_ms,
            metadata=metadata or {},
            message=message
        )
    
    async def emit_agent_event(
        self,
        org_id: uuid.UUID,
        event_type: str,  # execute, tool_use, error
        user_id: Optional[uuid.UUID],
        agent_id: Optional[uuid.UUID] = None,
        execution_id: Optional[uuid.UUID] = None,
        duration_ms: Optional[int] = None,
        cost: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
        trace_id: Optional[uuid.UUID] = None
    ):
        """Convenience method for logging agent events."""
        severity = "error" if event_type == "error" else "info"
        
        await self.emit(
            org_id=org_id,
            log_type="agent",
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            resource_id=agent_id,
            resource_type="agent",
            action="execute",
            duration_ms=duration_ms,
            cost=cost,
            metadata=metadata or {},
            trace_id=trace_id,
            message=message
        )
    
    async def shutdown(self):
        """Gracefully shutdown the logging service."""
        logger.info("Shutting down log service...")
        
        # Signal shutdown
        self.shutdown_event.set()
        
        # Flush remaining entries
        await self._flush_batch()
        
        # Wait for background task to complete
        if self.background_task:
            try:
                await asyncio.wait_for(self.background_task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("Background task did not complete within timeout")
                self.background_task.cancel()
        
        logger.info("Log service shutdown complete")


# Global log service instance
log_service = LogService()


# Convenience functions for common logging patterns
async def log_gateway_request(
    org_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    model: str,
    provider: str,
    status: str,
    duration_ms: int,
    cost: float,
    **kwargs
):
    """Log a gateway request."""
    await log_service.emit_gateway_request(
        org_id, user_id, model, provider, status, duration_ms, cost, **kwargs
    )


async def log_auth_event(
    org_id: uuid.UUID,
    event_type: str,
    user_id: Optional[uuid.UUID],
    success: bool,
    **kwargs
):
    """Log an authentication event."""
    await log_service.emit_auth_event(org_id, event_type, user_id, success, **kwargs)


async def log_admin_action(
    org_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    event_type: str,
    **kwargs
):
    """Log an admin action."""
    await log_service.emit_admin_action(org_id, admin_user_id, event_type, **kwargs)


async def log_kb_event(
    org_id: uuid.UUID,
    event_type: str,
    user_id: Optional[uuid.UUID],
    **kwargs
):
    """Log a knowledge base event."""
    await log_service.emit_kb_event(org_id, event_type, user_id, **kwargs)


async def log_agent_event(
    org_id: uuid.UUID,
    event_type: str,
    user_id: Optional[uuid.UUID],
    **kwargs
):
    """Log an agent event."""
    await log_service.emit_agent_event(org_id, event_type, user_id, **kwargs)