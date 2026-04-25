"""
Convenience wrappers to emit platform logs from key application flows.

These are thin helpers around log_service.emit() that provide a consistent
interface for each feature area. Each emitter writes to both the LogService
(PostgreSQL + integrations) and the GCS sink (for Helios ingestion).

Usage:
    from app.services.log_emitters import emit_auth_event, emit_gateway_event

    await emit_auth_event(org_id, user_id, "login_success", metadata={"ip": "1.2.3.4"})
"""

import logging
import uuid
from typing import Optional, Dict, Any

from app.services.log_service import log_service

logger = logging.getLogger(__name__)


def _emit_to_gcs(
    log_type: str,
    event_type: str,
    severity: str,
    message: Optional[str],
    org_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    metadata: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[int] = None,
    cost: Optional[float] = None,
    trace_id: Optional[uuid.UUID] = None,
) -> None:
    """Forward a log event to the GCS sink for Helios ingestion."""
    try:
        from app.core.gcs_log_sink import get_gcs_sink
        sink = get_gcs_sink()
        sink.emit(
            level=severity,
            message=message or f"{log_type}.{event_type}",
            logger_name=f"bonito.{log_type}",
            user_id=str(user_id) if user_id else None,
            org_id=str(org_id) if org_id else None,
            extra={
                "log_type": log_type,
                "event_type": event_type,
                "trace_id": str(trace_id) if trace_id else None,
                **(metadata or {}),
            },
        )
    except Exception:
        pass  # GCS emission is best-effort; never block the caller


# ── Gateway Events ──

async def emit_gateway_event(
    org_id: uuid.UUID,
    event_type: str,
    *,
    severity: str = "info",
    user_id: Optional[uuid.UUID] = None,
    resource_id: Optional[uuid.UUID] = None,
    resource_type: str = "model",
    action: str = "execute",
    message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[int] = None,
    cost: Optional[float] = None,
    trace_id: Optional[uuid.UUID] = None,
):
    """Log a gateway/proxy event (request, error, rate_limit, etc.)."""
    await log_service.emit(
        org_id=org_id,
        log_type="gateway",
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        resource_id=resource_id,
        resource_type=resource_type,
        action=action,
        message=message,
        metadata=metadata,
        duration_ms=duration_ms,
        cost=cost,
        trace_id=trace_id,
    )
    _emit_to_gcs("gateway", event_type, severity, message, org_id, user_id, metadata, duration_ms, cost, trace_id)


# ── Auth Events ──

async def emit_auth_event(
    org_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    event_type: str,
    *,
    severity: str = "info",
    message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Log an auth event (login_success, login_failed, logout, token_refresh, sso, etc.)."""
    await log_service.emit(
        org_id=org_id,
        log_type="auth",
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        resource_type="user",
        resource_id=user_id,
        action="execute",
        message=message,
        metadata=metadata,
    )
    _emit_to_gcs("auth", event_type, severity, message, org_id, user_id, metadata)


# ── Agent Events ──

async def emit_agent_event(
    org_id: uuid.UUID,
    event_type: str,
    *,
    severity: str = "info",
    user_id: Optional[uuid.UUID] = None,
    resource_id: Optional[uuid.UUID] = None,
    message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[int] = None,
    cost: Optional[float] = None,
    trace_id: Optional[uuid.UUID] = None,
):
    """Log an agent execution event (start, complete, error, tool_use)."""
    await log_service.emit(
        org_id=org_id,
        log_type="agent",
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        resource_id=resource_id,
        resource_type="agent",
        action="execute",
        message=message,
        metadata=metadata,
        duration_ms=duration_ms,
        cost=cost,
        trace_id=trace_id,
    )
    _emit_to_gcs("agent", event_type, severity, message, org_id, user_id, metadata, duration_ms, cost, trace_id)


# ── Knowledge Base Events ──

async def emit_kb_event(
    org_id: uuid.UUID,
    event_type: str,
    *,
    severity: str = "info",
    user_id: Optional[uuid.UUID] = None,
    resource_id: Optional[uuid.UUID] = None,
    action: str = "execute",
    message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[int] = None,
):
    """Log a knowledge base event (upload, search, delete)."""
    await log_service.emit(
        org_id=org_id,
        log_type="kb",
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        resource_id=resource_id,
        resource_type="knowledge_base",
        action=action,
        message=message,
        metadata=metadata,
        duration_ms=duration_ms,
    )
    _emit_to_gcs("kb", event_type, severity, message, org_id, user_id, metadata, duration_ms)


# ── Admin Events ──

async def emit_admin_event(
    org_id: uuid.UUID,
    event_type: str,
    *,
    severity: str = "info",
    user_id: Optional[uuid.UUID] = None,
    resource_id: Optional[uuid.UUID] = None,
    resource_type: str = "config",
    action: str = "update",
    message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Log an admin action (user_invite, role_change, config_change, etc.)."""
    await log_service.emit(
        org_id=org_id,
        log_type="admin",
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        resource_id=resource_id,
        resource_type=resource_type,
        action=action,
        message=message,
        metadata=metadata,
    )
    _emit_to_gcs("admin", event_type, severity, message, org_id, user_id, metadata)


# ── Deployment Events ──

async def emit_deployment_event(
    org_id: uuid.UUID,
    event_type: str,
    *,
    severity: str = "info",
    user_id: Optional[uuid.UUID] = None,
    resource_id: Optional[uuid.UUID] = None,
    action: str = "update",
    message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[int] = None,
):
    """Log a deployment event (deploy, scale, status_change)."""
    await log_service.emit(
        org_id=org_id,
        log_type="deployment",
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        resource_id=resource_id,
        resource_type="deployment",
        action=action,
        message=message,
        metadata=metadata,
        duration_ms=duration_ms,
    )
    _emit_to_gcs("deployment", event_type, severity, message, org_id, user_id, metadata, duration_ms)
