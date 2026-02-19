"""
Platform Log Service — async, batched, non-blocking.

Usage:
    from app.services.log_service import log_service

    # Fire-and-forget — never blocks the caller
    await log_service.emit(
        org_id=uuid,
        log_type="gateway",
        event_type="request",
        severity="info",
        message="Processed GPT-4 request",
        metadata={"model": "gpt-4", "tokens": 150},
    )

    # On app startup:
    await log_service.start()

    # On app shutdown:
    await log_service.stop()
"""

import asyncio
import logging
import uuid
from collections import deque
from datetime import datetime, timezone, date
from typing import Optional, Dict, Any, List

from sqlalchemy import select, insert, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import get_db_session
from app.models.logging import PlatformLog, LogIntegration, LogAggregation
from app.services.log_integrations import get_integration
from app.core.vault import vault_client

logger = logging.getLogger("bonito.log_service")

# ── Constants ──

FLUSH_INTERVAL_SECONDS = 2
FLUSH_BATCH_SIZE = 100
MAX_BUFFER_SIZE = 10_000


class LogService:
    """Async buffered log service with DB write and integration dispatch."""

    def __init__(self):
        self._buffer: deque[Dict[str, Any]] = deque(maxlen=MAX_BUFFER_SIZE)
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = asyncio.Lock()

    async def start(self):
        """Start the background flush loop."""
        if self._running:
            return
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("Log service started (flush every %ds or %d events)", FLUSH_INTERVAL_SECONDS, FLUSH_BATCH_SIZE)

    async def stop(self):
        """Stop the flush loop and drain remaining logs."""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        # Final flush
        await self._flush()
        logger.info("Log service stopped")

    async def emit(
        self,
        org_id: uuid.UUID,
        log_type: str,
        event_type: str,
        severity: str = "info",
        user_id: Optional[uuid.UUID] = None,
        resource_id: Optional[uuid.UUID] = None,
        resource_type: Optional[str] = None,
        action: Optional[str] = None,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        cost: Optional[float] = None,
        trace_id: Optional[uuid.UUID] = None,
    ):
        """
        Emit a platform log event. Non-blocking — adds to buffer.
        Triggers an immediate flush if buffer hits FLUSH_BATCH_SIZE.
        """
        entry = {
            "id": uuid.uuid4(),
            "org_id": org_id,
            "log_type": log_type,
            "event_type": event_type,
            "severity": severity,
            "user_id": user_id,
            "resource_id": resource_id,
            "resource_type": resource_type,
            "action": action,
            "message": message,
            "metadata": metadata or {},
            "duration_ms": duration_ms,
            "cost": cost,
            "trace_id": trace_id,
            "created_at": datetime.now(timezone.utc),
        }
        self._buffer.append(entry)

        # If buffer is full enough, trigger immediate flush
        if len(self._buffer) >= FLUSH_BATCH_SIZE:
            asyncio.create_task(self._flush())

    async def _flush_loop(self):
        """Background loop that flushes the buffer periodically."""
        while self._running:
            try:
                await asyncio.sleep(FLUSH_INTERVAL_SECONDS)
                await self._flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Flush loop error: {e}", exc_info=True)

    async def _flush(self):
        """Drain the buffer and write to DB + integrations."""
        if not self._buffer:
            return

        async with self._lock:
            # Drain buffer
            batch: List[Dict[str, Any]] = []
            while self._buffer and len(batch) < FLUSH_BATCH_SIZE * 2:
                batch.append(self._buffer.popleft())

        if not batch:
            return

        # Write to DB
        try:
            await self._write_to_db(batch)
        except Exception as e:
            logger.error(f"Failed to write {len(batch)} logs to DB: {e}", exc_info=True)
            return  # Don't dispatch to integrations if DB write failed

        # Dispatch to integrations (async, best-effort)
        asyncio.create_task(self._dispatch_to_integrations(batch))

        # Update aggregations (async, best-effort)
        asyncio.create_task(self._update_aggregations(batch))

    async def _write_to_db(self, batch: List[Dict[str, Any]]):
        """Batch INSERT logs into platform_logs table."""
        async with get_db_session() as session:
            # Convert UUIDs and datetimes for insertion
            rows = []
            for entry in batch:
                rows.append({
                    "id": entry["id"],
                    "org_id": entry["org_id"],
                    "log_type": entry["log_type"],
                    "event_type": entry["event_type"],
                    "severity": entry["severity"],
                    "trace_id": entry.get("trace_id"),
                    "user_id": entry.get("user_id"),
                    "resource_id": entry.get("resource_id"),
                    "resource_type": entry.get("resource_type"),
                    "action": entry.get("action"),
                    "metadata": entry.get("metadata"),
                    "duration_ms": entry.get("duration_ms"),
                    "cost": entry.get("cost"),
                    "message": entry.get("message"),
                    "created_at": entry["created_at"],
                })

            stmt = insert(PlatformLog).values(rows)
            await session.execute(stmt)
            logger.debug(f"Wrote {len(rows)} logs to DB")

    async def _dispatch_to_integrations(self, batch: List[Dict[str, Any]]):
        """Fan-out logs to all enabled integrations for affected orgs."""
        # Group logs by org_id
        org_logs: Dict[uuid.UUID, List[Dict[str, Any]]] = {}
        for entry in batch:
            org_id = entry["org_id"]
            org_logs.setdefault(org_id, []).append(entry)

        for org_id, logs in org_logs.items():
            try:
                await self._dispatch_for_org(org_id, logs)
            except Exception as e:
                logger.error(f"Integration dispatch failed for org {org_id}: {e}")

    async def _dispatch_for_org(self, org_id: uuid.UUID, logs: List[Dict[str, Any]]):
        """Send logs to all enabled integrations for a specific org."""
        async with get_db_session() as session:
            result = await session.execute(
                select(LogIntegration).where(
                    LogIntegration.org_id == org_id,
                    LogIntegration.enabled == True,
                )
            )
            integrations = result.scalars().all()

        if not integrations:
            return

        # Serialize log entries for external dispatch
        serialized_logs = []
        for log in logs:
            serialized = dict(log)
            # Convert UUIDs and datetimes to strings
            for key, val in serialized.items():
                if isinstance(val, uuid.UUID):
                    serialized[key] = str(val)
                elif isinstance(val, datetime):
                    serialized[key] = val.isoformat()
            serialized_logs.append(serialized)

        # Fan-out to each integration
        tasks = []
        for integration in integrations:
            tasks.append(self._send_to_integration(integration, serialized_logs))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_to_integration(self, integration: LogIntegration, logs: List[Dict[str, Any]]):
        """Send logs to a single integration."""
        try:
            # Load credentials from Vault
            credentials = await vault_client.get_secrets(integration.credentials_path)

            provider = get_integration(
                integration.integration_type,
                integration.config or {},
                credentials,
            )
            if provider is None:
                return

            success = await provider.send_logs(logs)
            if not success:
                logger.warning(
                    f"Integration {integration.name} ({integration.integration_type}) "
                    f"failed to send {len(logs)} logs"
                )
        except Exception as e:
            logger.error(f"Integration {integration.name} error: {e}")

    async def _update_aggregations(self, batch: List[Dict[str, Any]]):
        """Update pre-computed aggregation buckets."""
        try:
            # Group by (org_id, date, hour, log_type, event_type, severity)
            buckets: Dict[tuple, Dict[str, Any]] = {}
            for entry in batch:
                created = entry["created_at"]
                key = (
                    entry["org_id"],
                    created.date(),
                    created.hour,
                    entry["log_type"],
                    entry["event_type"],
                    entry["severity"],
                )
                if key not in buckets:
                    buckets[key] = {
                        "log_count": 0,
                        "error_count": 0,
                        "total_duration_ms": 0,
                        "total_cost": 0.0,
                        "user_ids": set(),
                    }
                b = buckets[key]
                b["log_count"] += 1
                if entry["severity"] in ("error", "critical"):
                    b["error_count"] += 1
                if entry.get("duration_ms"):
                    b["total_duration_ms"] += entry["duration_ms"]
                if entry.get("cost"):
                    b["total_cost"] += entry["cost"]
                if entry.get("user_id"):
                    b["user_ids"].add(entry["user_id"])

            async with get_db_session() as session:
                for key, vals in buckets.items():
                    org_id, date_bucket, hour_bucket, log_type, event_type, severity = key

                    # Upsert using PostgreSQL ON CONFLICT
                    stmt = pg_insert(LogAggregation).values(
                        id=uuid.uuid4(),
                        org_id=org_id,
                        date_bucket=date_bucket,
                        hour_bucket=hour_bucket,
                        log_type=log_type,
                        event_type=event_type,
                        severity=severity,
                        log_count=vals["log_count"],
                        error_count=vals["error_count"],
                        total_duration_ms=vals["total_duration_ms"],
                        total_cost=vals["total_cost"],
                        unique_users=len(vals["user_ids"]),
                        last_updated=datetime.now(timezone.utc),
                    ).on_conflict_do_update(
                        index_elements=["org_id", "date_bucket", "hour_bucket", "log_type", "event_type", "severity"],
                        set_={
                            "log_count": LogAggregation.log_count + vals["log_count"],
                            "error_count": LogAggregation.error_count + vals["error_count"],
                            "total_duration_ms": LogAggregation.total_duration_ms + vals["total_duration_ms"],
                            "total_cost": LogAggregation.total_cost + vals["total_cost"],
                            "unique_users": LogAggregation.unique_users + len(vals["user_ids"]),
                            "last_updated": datetime.now(timezone.utc),
                        },
                    )
                    await session.execute(stmt)

        except Exception as e:
            logger.error(f"Aggregation update error: {e}", exc_info=True)


# Singleton instance
log_service = LogService()
