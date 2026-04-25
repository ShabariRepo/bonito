"""
API routes for platform logging and observability.

Provides:
  - Log querying with hierarchical + deep filters (model, provider, endpoint, IP)
  - Audit log querying with hash chain verification (SOC2 CC9.2)
  - Log export (async CSV/JSON)
  - Log statistics for dashboards
  - Log integration CRUD and connectivity testing
  - Frontend event ingestion proxy for Helios
"""

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.vault import vault_client
from app.api.dependencies import get_current_user, require_admin
from app.models.user import User
from app.models.logging import PlatformLog, LogIntegration, LogExportJob, LogAggregation
from app.models.audit import AuditLog
from app.schemas.logging import (
    PlatformLogResponse,
    PlatformLogListResponse,
    LogIntegrationCreate,
    LogIntegrationUpdate,
    LogIntegrationResponse,
    LogIntegrationListResponse,
    LogIntegrationTestResult,
    LogExportRequest,
    LogExportJobResponse,
    LogStatsResponse,
    LogStatsBucket,
)
from app.services.log_integrations import get_integration

# ── Routers ──

router = APIRouter(tags=["logs"])
integration_router = APIRouter(tags=["log-integrations"])
audit_router = APIRouter(tags=["audit-logs"])


# ═══════════════════════════════════════════
# Log Querying
# ═══════════════════════════════════════════

@router.get("/logs", response_model=PlatformLogListResponse)
async def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    log_type: Optional[str] = None,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[uuid.UUID] = None,
    trace_id: Optional[uuid.UUID] = None,
    search: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    # Deep filters (Phase 3) — query JSONB metadata fields
    model: Optional[str] = Query(None, description="Filter by AI model name"),
    provider: Optional[str] = Query(None, description="Filter by provider (bedrock, azure, openai, etc.)"),
    agent_id: Optional[uuid.UUID] = Query(None, description="Filter by agent resource_id"),
    endpoint: Optional[str] = Query(None, description="Filter by API endpoint path"),
    ip_address: Optional[str] = Query(None, description="Filter by client IP address"),
    request_id: Optional[str] = Query(None, description="Filter by X-Request-ID"),
    action: Optional[str] = Query(None, description="Filter by action (create, read, update, delete, execute)"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Query platform logs with hierarchical + deep filtering. Scoped to user's org."""
    base = select(PlatformLog).where(PlatformLog.org_id == user.org_id)

    if log_type:
        base = base.where(PlatformLog.log_type == log_type)
    if event_type:
        base = base.where(PlatformLog.event_type == event_type)
    if severity:
        base = base.where(PlatformLog.severity == severity)
    if user_id:
        base = base.where(PlatformLog.user_id == user_id)
    if resource_type:
        base = base.where(PlatformLog.resource_type == resource_type)
    if resource_id:
        base = base.where(PlatformLog.resource_id == resource_id)
    if trace_id:
        base = base.where(PlatformLog.trace_id == trace_id)
    if search:
        base = base.where(PlatformLog.message.ilike(f"%{search}%"))
    if date_from:
        base = base.where(PlatformLog.created_at >= date_from)
    if date_to:
        base = base.where(PlatformLog.created_at <= date_to)
    if action:
        base = base.where(PlatformLog.action == action)

    # Deep filters — JSONB metadata queries
    if model:
        base = base.where(PlatformLog.event_metadata["model"].astext == model)
    if provider:
        base = base.where(PlatformLog.event_metadata["provider"].astext == provider)
    if agent_id:
        base = base.where(PlatformLog.resource_id == agent_id, PlatformLog.resource_type == "agent")
    if endpoint:
        base = base.where(PlatformLog.event_metadata["endpoint"].astext == endpoint)
    if ip_address:
        base = base.where(PlatformLog.event_metadata["ip"].astext == ip_address)
    if request_id:
        base = base.where(PlatformLog.event_metadata["request_id"].astext == request_id)

    # Total count
    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Paginated results
    items_q = base.order_by(PlatformLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(items_q)
    items = result.scalars().all()

    return PlatformLogListResponse(items=items, total=total, page=page, page_size=page_size)


# ═══════════════════════════════════════════
# Log Export
# ═══════════════════════════════════════════

@router.get("/logs/export", response_model=LogExportJobResponse)
async def export_logs(
    format: str = Query("csv", regex="^(csv|json)$"),
    log_type: Optional[str] = None,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    resource_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Trigger an async log export job. Returns the job for status polling."""
    filters = {}
    if log_type:
        filters["log_type"] = log_type
    if event_type:
        filters["event_type"] = event_type
    if severity:
        filters["severity"] = severity
    if date_from:
        filters["date_from"] = date_from.isoformat()
    if date_to:
        filters["date_to"] = date_to.isoformat()
    if resource_type:
        filters["resource_type"] = resource_type

    job = LogExportJob(
        org_id=user.org_id,
        user_id=user.id,
        export_format=format,
        filters=filters,
        status="pending",
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    return job


# ═══════════════════════════════════════════
# Log Statistics
# ═══════════════════════════════════════════

@router.get("/logs/stats", response_model=LogStatsResponse)
async def log_stats(
    range_days: int = Query(7, ge=1, le=90, alias="range"),
    log_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get log volume statistics from pre-computed aggregations."""
    since = datetime.now(timezone.utc) - timedelta(days=range_days)
    since_date = since.date()

    base = select(LogAggregation).where(
        LogAggregation.org_id == user.org_id,
        LogAggregation.date_bucket >= since_date,
    )
    if log_type:
        base = base.where(LogAggregation.log_type == log_type)

    result = await db.execute(base)
    aggs = result.scalars().all()

    # Build response
    total_logs = sum(a.log_count for a in aggs)
    total_errors = sum(a.error_count for a in aggs)

    # Time series (daily buckets)
    time_series_map: dict = {}
    by_type: dict = {}
    by_severity: dict = {}

    for a in aggs:
        day_key = a.date_bucket.isoformat()
        if day_key not in time_series_map:
            time_series_map[day_key] = {"date": day_key, "count": 0, "error_count": 0}
        time_series_map[day_key]["count"] += a.log_count
        time_series_map[day_key]["error_count"] += a.error_count

        if a.log_type:
            by_type[a.log_type] = by_type.get(a.log_type, 0) + a.log_count
        if a.severity:
            by_severity[a.severity] = by_severity.get(a.severity, 0) + a.log_count

    time_series = sorted(time_series_map.values(), key=lambda x: x["date"])

    return LogStatsResponse(
        total_logs=total_logs,
        total_errors=total_errors,
        time_series=[LogStatsBucket(**ts) for ts in time_series],
        by_type=by_type,
        by_severity=by_severity,
        range_days=range_days,
    )


# ═══════════════════════════════════════════
# Log Integrations CRUD
# ═══════════════════════════════════════════

@integration_router.post("/log-integrations", response_model=LogIntegrationResponse, status_code=status.HTTP_201_CREATED)
async def create_integration(
    body: LogIntegrationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Create a new log integration. Credentials are stored in Vault."""
    integration_id = uuid.uuid4()
    creds_path = f"log-integrations/{integration_id}"

    # Store credentials in Vault
    try:
        await vault_client.put_secrets(creds_path, body.credentials)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store credentials: {str(e)}",
        )

    integration = LogIntegration(
        id=integration_id,
        org_id=user.org_id,
        name=body.name,
        integration_type=body.integration_type.value,
        config=body.config,
        credentials_path=creds_path,
        enabled=body.enabled,
    )
    db.add(integration)
    await db.flush()
    await db.refresh(integration)

    return integration


@integration_router.get("/log-integrations", response_model=LogIntegrationListResponse)
async def list_integrations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all log integrations for the user's organization."""
    result = await db.execute(
        select(LogIntegration)
        .where(LogIntegration.org_id == user.org_id)
        .order_by(LogIntegration.created_at.desc())
    )
    items = result.scalars().all()
    return LogIntegrationListResponse(items=items, total=len(items))


@integration_router.put("/log-integrations/{integration_id}", response_model=LogIntegrationResponse)
async def update_integration(
    integration_id: uuid.UUID,
    body: LogIntegrationUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Update a log integration. Optionally update credentials."""
    result = await db.execute(
        select(LogIntegration).where(
            LogIntegration.id == integration_id,
            LogIntegration.org_id == user.org_id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    if body.name is not None:
        integration.name = body.name
    if body.config is not None:
        integration.config = body.config
    if body.enabled is not None:
        integration.enabled = body.enabled
    if body.credentials is not None:
        try:
            await vault_client.put_secrets(integration.credentials_path, body.credentials)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update credentials: {str(e)}",
            )

    await db.flush()
    await db.refresh(integration)
    return integration


@integration_router.delete("/log-integrations/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(
    integration_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Delete a log integration."""
    result = await db.execute(
        select(LogIntegration).where(
            LogIntegration.id == integration_id,
            LogIntegration.org_id == user.org_id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    await db.delete(integration)
    await db.flush()


@integration_router.post("/log-integrations/{integration_id}/test", response_model=LogIntegrationTestResult)
async def test_integration(
    integration_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Test connectivity of a log integration."""
    result = await db.execute(
        select(LogIntegration).where(
            LogIntegration.id == integration_id,
            LogIntegration.org_id == user.org_id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Load credentials
    try:
        credentials = await vault_client.get_secrets(integration.credentials_path)
    except Exception as e:
        credentials = {}

    provider = get_integration(integration.integration_type, integration.config or {}, credentials)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown integration type: {integration.integration_type}",
        )

    now = datetime.now(timezone.utc)
    success, message = await provider.test_connection()

    # Update test status
    integration.last_test_status = "success" if success else "failed"
    integration.last_test_message = message
    integration.last_test_at = now
    await db.flush()

    return LogIntegrationTestResult(success=success, message=message, tested_at=now)


# ═══════════════════════════════════════════
# Audit Logs (SOC2 CC7.2 / CC9.2)
# ═══════════════════════════════════════════

class AuditLogResponse(BaseModel):
    id: uuid.UUID
    org_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details_json: Optional[dict] = None
    ip_address: Optional[str] = None
    user_name: Optional[str] = None
    entry_hash: str = ""
    prev_hash: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int


class HashChainVerifyResponse(BaseModel):
    valid: bool
    total_entries: int
    broken_at_index: Optional[int] = None
    broken_entry_id: Optional[uuid.UUID] = None
    message: str


@audit_router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user_id: Optional[uuid.UUID] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    ip_address: Optional[str] = None,
    request_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    status_code: Optional[int] = Query(None, description="Filter by response status code"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Query audit logs with deep filtering. Admin only. Scoped to user's org."""
    base = select(AuditLog).where(AuditLog.org_id == user.org_id)

    if user_id:
        base = base.where(AuditLog.user_id == user_id)
    if action:
        base = base.where(AuditLog.action == action)
    if resource_type:
        base = base.where(AuditLog.resource_type == resource_type)
    if ip_address:
        base = base.where(AuditLog.ip_address == ip_address)
    if date_from:
        base = base.where(AuditLog.created_at >= date_from)
    if date_to:
        base = base.where(AuditLog.created_at <= date_to)
    if request_id:
        base = base.where(AuditLog.details_json["request_id"].astext == request_id)
    if status_code is not None:
        base = base.where(AuditLog.details_json["status_code"].as_integer() == status_code)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar_one()

    items_q = base.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(items_q)
    items = result.scalars().all()

    return AuditLogListResponse(items=items, total=total, page=page, page_size=page_size)


@audit_router.post("/audit-logs/verify", response_model=HashChainVerifyResponse)
async def verify_audit_chain(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Verify the tamper-evident hash chain for audit logs. SOC2 CC9.2 evidence."""
    base = (
        select(AuditLog)
        .where(AuditLog.org_id == user.org_id)
        .order_by(AuditLog.created_at.asc())
    )
    if date_from:
        base = base.where(AuditLog.created_at >= date_from)
    if date_to:
        base = base.where(AuditLog.created_at <= date_to)

    result = await db.execute(base)
    entries = result.scalars().all()

    if not entries:
        return HashChainVerifyResponse(
            valid=True, total_entries=0, message="No audit entries in range"
        )

    prev_hash = ""
    for idx, entry in enumerate(entries):
        # Skip entries without hash (pre-migration)
        if not entry.entry_hash:
            prev_hash = ""
            continue

        # Recompute the expected hash
        hash_input = "|".join([
            entry.prev_hash or "",
            str(entry.org_id or ""),
            str(entry.user_id or ""),
            entry.action,
            entry.resource_type,
            (entry.details_json or {}).get("path", ""),
            str((entry.details_json or {}).get("status_code", "")),
            entry.created_at.isoformat(),
        ])
        expected_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        if entry.entry_hash != expected_hash:
            return HashChainVerifyResponse(
                valid=False,
                total_entries=len(entries),
                broken_at_index=idx,
                broken_entry_id=entry.id,
                message=f"Hash chain broken at entry {idx} (id={entry.id}): expected {expected_hash[:16]}..., got {entry.entry_hash[:16]}...",
            )

        # Verify chain linkage
        if entry.prev_hash != prev_hash and prev_hash and entry.prev_hash:
            return HashChainVerifyResponse(
                valid=False,
                total_entries=len(entries),
                broken_at_index=idx,
                broken_entry_id=entry.id,
                message=f"Chain linkage broken at entry {idx}: prev_hash mismatch",
            )

        prev_hash = entry.entry_hash

    return HashChainVerifyResponse(
        valid=True,
        total_entries=len(entries),
        message=f"Hash chain verified: {len(entries)} entries, all valid",
    )


# ═══════════════════════════════════════════
# Frontend Event Ingestion (Phase 4)
# ═══════════════════════════════════════════

class FrontendEvent(BaseModel):
    level: str = Field(pattern="^(info|warning|error|critical)$")
    message: str = Field(max_length=2000)
    logger: str = Field(default="bonito.frontend", max_length=200)
    request_id: Optional[str] = None
    exception: Optional[dict] = None
    extra: Optional[dict] = None


class FrontendEventBatch(BaseModel):
    events: List[FrontendEvent] = Field(max_length=50)


@router.post("/frontend-events", status_code=status.HTTP_202_ACCEPTED)
async def ingest_frontend_events(
    batch: FrontendEventBatch,
    user: User = Depends(get_current_user),
):
    """
    Ingest structured frontend events and forward to GCS sink for Helios.

    Rate limited to 50 events per request. Events are tagged with the
    authenticated user's org_id for multi-tenant isolation in Helios.
    """
    try:
        from app.core.gcs_log_sink import get_gcs_sink
        sink = get_gcs_sink()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GCS log sink not available",
        )

    for event in batch.events:
        sink.emit(
            level=event.level,
            message=event.message,
            logger_name=event.logger,
            request_id=event.request_id,
            user_id=str(user.id),
            org_id=str(user.org_id),
            exception=event.exception,
            extra={
                "source": "frontend",
                "log_type": "frontend",
                **(event.extra or {}),
            },
        )

    return {"accepted": len(batch.events)}
