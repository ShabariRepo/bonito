"""
<<<<<<< HEAD
Logging API Routes

Provides REST endpoints for:
- Querying platform logs with filters and pagination
- Managing external log integrations
- Exporting logs in various formats
- Log analytics and statistics
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy import select, func, and_, or_, desc, asc, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.vault import vault_client
from app.models.user import User
from app.models.logging import PlatformLog, LogIntegration, LogExportJob
from app.schemas.logging import (
    LogQueryRequest, LogQueryResponse, PlatformLogResponse,
    LogIntegrationCreate, LogIntegrationUpdate, LogIntegrationResponse,
    LogIntegrationTestResult, LogExportRequest, LogExportJobResponse,
    LogStatsRequest, LogStatsResponse, LogStatsDataPoint
)
from app.services.log_integrations import integration_registry
from app.services.auth_service import get_current_user, get_current_admin_user

router = APIRouter(prefix="/logs", tags=["logging"])


# ─── Log Query Endpoints ───

@router.post("/query", response_model=LogQueryResponse)
async def query_logs(
    query_request: LogQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Query platform logs with filtering and pagination.
    
    Supports hierarchical filtering by org_id → log_type → event_type,
    plus filtering by severity, user, resources, time range, and more.
    """
    filters = query_request.filters
    org_id = current_user.org_id
    
    # Build base query
    query = select(PlatformLog).where(PlatformLog.org_id == org_id)
    count_query = select(func.count(PlatformLog.id)).where(PlatformLog.org_id == org_id)
    
    # Apply filters
    if filters.log_types:
        query = query.where(PlatformLog.log_type.in_(filters.log_types))
        count_query = count_query.where(PlatformLog.log_type.in_(filters.log_types))
    
    if filters.event_types:
        query = query.where(PlatformLog.event_type.in_(filters.event_types))
        count_query = count_query.where(PlatformLog.event_type.in_(filters.event_types))
    
    if filters.severities:
        query = query.where(PlatformLog.severity.in_(filters.severities))
        count_query = count_query.where(PlatformLog.severity.in_(filters.severities))
    
    if filters.user_ids:
        query = query.where(PlatformLog.user_id.in_(filters.user_ids))
        count_query = count_query.where(PlatformLog.user_id.in_(filters.user_ids))
    
    if filters.resource_types:
        query = query.where(PlatformLog.resource_type.in_(filters.resource_types))
        count_query = count_query.where(PlatformLog.resource_type.in_(filters.resource_types))
    
    if filters.resource_ids:
        query = query.where(PlatformLog.resource_id.in_(filters.resource_ids))
        count_query = count_query.where(PlatformLog.resource_id.in_(filters.resource_ids))
    
    if filters.actions:
        query = query.where(PlatformLog.action.in_(filters.actions))
        count_query = count_query.where(PlatformLog.action.in_(filters.actions))
    
    if filters.trace_id:
        query = query.where(PlatformLog.trace_id == filters.trace_id)
        count_query = count_query.where(PlatformLog.trace_id == filters.trace_id)
    
    if filters.start_date:
        query = query.where(PlatformLog.created_at >= filters.start_date)
        count_query = count_query.where(PlatformLog.created_at >= filters.start_date)
    
    if filters.end_date:
        query = query.where(PlatformLog.created_at < filters.end_date)
        count_query = count_query.where(PlatformLog.created_at < filters.end_date)
    
    if filters.min_duration_ms is not None:
        query = query.where(PlatformLog.duration_ms >= filters.min_duration_ms)
        count_query = count_query.where(PlatformLog.duration_ms >= filters.min_duration_ms)
    
    if filters.max_duration_ms is not None:
        query = query.where(PlatformLog.duration_ms <= filters.max_duration_ms)
        count_query = count_query.where(PlatformLog.duration_ms <= filters.max_duration_ms)
    
    if filters.min_cost is not None:
        query = query.where(PlatformLog.cost >= filters.min_cost)
        count_query = count_query.where(PlatformLog.cost >= filters.min_cost)
    
    if filters.max_cost is not None:
        query = query.where(PlatformLog.cost <= filters.max_cost)
        count_query = count_query.where(PlatformLog.cost <= filters.max_cost)
    
    # Full-text search in message and metadata
    if filters.search:
        search_term = f"%{filters.search}%"
        search_condition = or_(
            PlatformLog.message.ilike(search_term),
            PlatformLog.metadata.astext.ilike(search_term)
        )
        query = query.where(search_condition)
        count_query = count_query.where(search_condition)
    
    # Apply sorting
    sort_field = getattr(PlatformLog, query_request.sort_by, PlatformLog.created_at)
    if query_request.sort_order == "desc":
        query = query.order_by(desc(sort_field))
    else:
        query = query.order_by(asc(sort_field))
    
    # Apply pagination
    query = query.offset(query_request.offset).limit(query_request.limit)
    
    # Execute queries
    result = await db.execute(query)
    logs = result.scalars().all()
    
    count_result = await db.execute(count_query)
    total_count = count_result.scalar()
    
    # Convert to response models
    log_responses = [PlatformLogResponse.model_validate(log) for log in logs]
    
    return LogQueryResponse(
        logs=log_responses,
        total_count=total_count,
        has_more=query_request.offset + len(logs) < total_count,
        filters_applied=filters
    )


@router.get("/trace/{trace_id}", response_model=List[PlatformLogResponse])
async def get_logs_by_trace(
    trace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get all logs for a specific trace ID."""
    result = await db.execute(
        select(PlatformLog)
        .where(
            and_(
                PlatformLog.org_id == current_user.org_id,
                PlatformLog.trace_id == trace_id
            )
        )
        .order_by(PlatformLog.created_at)
    )
    logs = result.scalars().all()
    return [PlatformLogResponse.model_validate(log) for log in logs]


# ─── Export Endpoints ───

@router.post("/export", response_model=LogExportJobResponse)
async def create_export_job(
    export_request: LogExportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create an async log export job."""
    # Create export job record
    export_job = LogExportJob(
        org_id=current_user.org_id,
        user_id=current_user.id,
        export_format=export_request.export_format,
        filters=export_request.filters.model_dump()
    )
    
    db.add(export_job)
    await db.commit()
    await db.refresh(export_job)
    
    # Queue background processing
    background_tasks.add_task(
        _process_export_job, 
        export_job.id, 
        export_request.include_metadata,
        export_request.email_when_complete
    )
    
    return LogExportJobResponse.model_validate(export_job)


@router.get("/export/{job_id}", response_model=LogExportJobResponse)
async def get_export_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get export job status."""
    result = await db.execute(
        select(LogExportJob)
        .where(
            and_(
                LogExportJob.id == job_id,
                LogExportJob.org_id == current_user.org_id
            )
        )
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    
    return LogExportJobResponse.model_validate(job)


@router.get("/exports", response_model=List[LogExportJobResponse])
async def list_export_jobs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(50, ge=1, le=100)
):
    """List export jobs for the current user."""
    result = await db.execute(
        select(LogExportJob)
        .where(LogExportJob.user_id == current_user.id)
        .order_by(desc(LogExportJob.created_at))
        .limit(limit)
    )
    jobs = result.scalars().all()
    return [LogExportJobResponse.model_validate(job) for job in jobs]


# ─── Integration Management Endpoints ───

@router.post("/integrations", response_model=LogIntegrationResponse)
async def create_integration(
    integration_data: LogIntegrationCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new log integration."""
    # Validate integration type
    if not integration_registry.get_handler(integration_data.integration_type):
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported integration type: {integration_data.integration_type}"
        )
    
    # Store credentials in Vault
    credentials_path = f"log_integrations/{current_user.org_id}/{uuid.uuid4()}"
    await vault_client.write_secret(credentials_path, integration_data.credentials)
    
    # Create integration record
    integration = LogIntegration(
        org_id=current_user.org_id,
        name=integration_data.name,
        integration_type=integration_data.integration_type,
        config=integration_data.config,
        credentials_path=credentials_path,
        enabled=integration_data.enabled
    )
    
    db.add(integration)
    await db.commit()
    await db.refresh(integration)
    
    return LogIntegrationResponse.model_validate(integration)


@router.get("/integrations", response_model=List[LogIntegrationResponse])
async def list_integrations(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db_session)
):
    """List all log integrations for the organization."""
    result = await db.execute(
        select(LogIntegration)
        .where(LogIntegration.org_id == current_user.org_id)
        .order_by(LogIntegration.created_at)
    )
    integrations = result.scalars().all()
    return [LogIntegrationResponse.model_validate(integration) for integration in integrations]


@router.put("/integrations/{integration_id}", response_model=LogIntegrationResponse)
async def update_integration(
    integration_id: uuid.UUID,
    integration_data: LogIntegrationUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update a log integration."""
    result = await db.execute(
        select(LogIntegration)
        .where(
            and_(
                LogIntegration.id == integration_id,
                LogIntegration.org_id == current_user.org_id
            )
        )
    )
    integration = result.scalar_one_or_none()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    # Update fields
    if integration_data.name is not None:
        integration.name = integration_data.name
    
    if integration_data.config is not None:
        integration.config = integration_data.config
    
    if integration_data.enabled is not None:
        integration.enabled = integration_data.enabled
    
    if integration_data.credentials is not None:
        # Update credentials in Vault
        await vault_client.write_secret(integration.credentials_path, integration_data.credentials)
    
    await db.commit()
    await db.refresh(integration)
    
    return LogIntegrationResponse.model_validate(integration)


@router.delete("/integrations/{integration_id}")
async def delete_integration(
    integration_id: uuid.UUID,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a log integration."""
    result = await db.execute(
        select(LogIntegration)
        .where(
            and_(
                LogIntegration.id == integration_id,
                LogIntegration.org_id == current_user.org_id
            )
        )
    )
    integration = result.scalar_one_or_none()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    # Clean up Vault credentials
    try:
        await vault_client.delete_secret(integration.credentials_path)
    except Exception as e:
        # Log but don't fail the deletion
        pass
    
    await db.delete(integration)
    await db.commit()
    
    return {"message": "Integration deleted successfully"}


@router.post("/integrations/{integration_id}/test", response_model=LogIntegrationTestResult)
async def test_integration(
    integration_id: uuid.UUID,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Test connectivity to a log integration."""
    result = await db.execute(
        select(LogIntegration)
        .where(
            and_(
                LogIntegration.id == integration_id,
                LogIntegration.org_id == current_user.org_id
            )
        )
    )
    integration = result.scalar_one_or_none()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    # Get handler and test connection
    handler = integration_registry.get_handler(integration.integration_type)
    if not handler:
        raise HTTPException(
            status_code=400,
            detail=f"No handler available for integration type: {integration.integration_type}"
        )
    
    test_result = await handler.test_connection(integration)
    
    # Update integration with test results
    integration.last_test_status = "success" if test_result["success"] else "failed"
    integration.last_test_message = test_result["message"]
    integration.last_test_at = datetime.now(timezone.utc)
    await db.commit()
    
    return LogIntegrationTestResult(**test_result)


# ─── Statistics and Analytics Endpoints ───

@router.post("/stats", response_model=LogStatsResponse)
async def get_log_statistics(
    stats_request: LogStatsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get log statistics and analytics."""
    # This is a simplified implementation
    # In production, this should use the log_aggregations table for performance
    
    filters = stats_request.filters
    org_id = current_user.org_id
    
    # Build base query with group by
    group_fields = []
    select_fields = []
    
    for field in stats_request.group_by:
        if field == "log_type":
            group_fields.append(PlatformLog.log_type)
            select_fields.append(PlatformLog.log_type.label("log_type"))
        elif field == "event_type":
            group_fields.append(PlatformLog.event_type)
            select_fields.append(PlatformLog.event_type.label("event_type"))
        elif field == "severity":
            group_fields.append(PlatformLog.severity)
            select_fields.append(PlatformLog.severity.label("severity"))
    
    # Add metric calculations
    metric_fields = []
    for metric in stats_request.metrics:
        if metric == "count":
            metric_fields.append(func.count(PlatformLog.id).label("count"))
        elif metric == "error_rate":
            metric_fields.append(
                (func.sum(func.case((PlatformLog.severity.in_(["error", "critical"]), 1), else_=0)) * 100.0 / func.count(PlatformLog.id)).label("error_rate")
            )
        elif metric == "avg_duration":
            metric_fields.append(func.avg(PlatformLog.duration_ms).label("avg_duration"))
        elif metric == "total_cost":
            metric_fields.append(func.sum(PlatformLog.cost).label("total_cost"))
    
    # Build query
    query = select(*(select_fields + metric_fields)).where(PlatformLog.org_id == org_id)
    
    # Apply filters (similar to query_logs)
    if filters.log_types:
        query = query.where(PlatformLog.log_type.in_(filters.log_types))
    if filters.start_date:
        query = query.where(PlatformLog.created_at >= filters.start_date)
    if filters.end_date:
        query = query.where(PlatformLog.created_at < filters.end_date)
    
    # Group by specified fields
    if group_fields:
        query = query.group_by(*group_fields)
    
    # Execute query
    result = await db.execute(query)
    rows = result.fetchall()
    
    # Convert to response format
    data_points = []
    for row in rows:
        dimensions = {}
        metrics = {}
        
        for field in stats_request.group_by:
            dimensions[field] = getattr(row, field, None)
        
        for metric in stats_request.metrics:
            value = getattr(row, metric, 0)
            metrics[metric] = float(value) if value is not None else 0.0
        
        data_points.append(LogStatsDataPoint(
            dimensions=dimensions,
            metrics=metrics
        ))
    
    # Get total record count
    count_result = await db.execute(
        select(func.count(PlatformLog.id)).where(PlatformLog.org_id == org_id)
    )
    total_records = count_result.scalar()
    
    return LogStatsResponse(
        data=data_points,
        total_records=total_records,
        filters_applied=filters
    )


# ─── Helper Functions ───

async def _process_export_job(job_id: uuid.UUID, include_metadata: bool, email_when_complete: bool):
    """Background task to process log export jobs."""
    # TODO: Implement actual export processing
    # This would:
    # 1. Query logs based on filters
    # 2. Generate file in requested format (CSV, JSON, etc.)
    # 3. Store file and update job status
    # 4. Send email notification if requested
    pass
=======
API routes for platform logging and observability.

Provides:
  - Log querying with hierarchical filters
  - Log export (async CSV/JSON)
  - Log statistics for dashboards
  - Log integration CRUD and connectivity testing
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.vault import vault_client
from app.api.dependencies import get_current_user, require_admin
from app.models.user import User
from app.models.logging import PlatformLog, LogIntegration, LogExportJob, LogAggregation
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
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Query platform logs with hierarchical filtering. Scoped to user's org."""
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
>>>>>>> main
