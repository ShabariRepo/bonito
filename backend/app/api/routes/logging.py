"""
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