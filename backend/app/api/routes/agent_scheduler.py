"""
Agent Scheduler API Routes

Routes for managing agent schedules and viewing execution history.
"""

from typing import List, Optional
from uuid import UUID
import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.agent import Agent
from app.models.agent_schedule import AgentSchedule
from app.schemas.bonobot import (
    AgentScheduleCreate,
    AgentScheduleUpdate,
    AgentScheduleResponse,
    ScheduledExecutionResponse,
    ScheduledExecutionTriggerRequest,
)
from app.services.agent_scheduler_service import AgentSchedulerService

router = APIRouter()
scheduler_service = AgentSchedulerService()


@router.post("/agents/{agent_id}/schedules", response_model=AgentScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_schedule(
    agent_id: UUID,
    schedule_data: AgentScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new schedule for an agent."""
    
    # Verify agent exists and user has access
    stmt = select(Agent).where(
        and_(
            Agent.id == agent_id,
            Agent.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Feature gate: check if organization has scheduled execution enabled
    # TODO: Add feature gate check here
    
    try:
        schedule = await scheduler_service.create_schedule(
            agent_id=agent_id,
            name=schedule_data.name,
            cron_expression=schedule_data.cron_expression,
            task_prompt=schedule_data.task_prompt,
            description=schedule_data.description,
            output_config=schedule_data.output_config,
            enabled=schedule_data.enabled,
            timezone_str=schedule_data.timezone,
            max_retries=schedule_data.max_retries,
            retry_delay_minutes=schedule_data.retry_delay_minutes,
            timeout_minutes=schedule_data.timeout_minutes,
            db=db
        )
        
        return AgentScheduleResponse.model_validate(schedule)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create schedule: {str(e)}"
        )


@router.get("/agents/{agent_id}/schedules", response_model=List[AgentScheduleResponse])
async def list_agent_schedules(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all schedules for an agent."""
    
    # Verify agent access
    stmt = select(Agent).where(
        and_(
            Agent.id == agent_id,
            Agent.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Get schedules for this agent
    stmt = select(AgentSchedule).where(AgentSchedule.agent_id == agent_id)
    result = await db.execute(stmt)
    schedules = result.scalars().all()
    
    return [AgentScheduleResponse.model_validate(schedule) for schedule in schedules]


@router.get("/schedules/{schedule_id}", response_model=AgentScheduleResponse)
async def get_schedule(
    schedule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific schedule."""
    
    stmt = select(AgentSchedule).where(
        and_(
            AgentSchedule.id == schedule_id,
            AgentSchedule.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    return AgentScheduleResponse.model_validate(schedule)


@router.put("/schedules/{schedule_id}", response_model=AgentScheduleResponse)
async def update_schedule(
    schedule_id: UUID,
    schedule_data: AgentScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing schedule."""
    
    # Verify schedule exists and user has access
    stmt = select(AgentSchedule).where(
        and_(
            AgentSchedule.id == schedule_id,
            AgentSchedule.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    try:
        update_data = schedule_data.model_dump(exclude_unset=True)
        updated_schedule = await scheduler_service.update_schedule(
            schedule_id=schedule_id,
            db=db,
            **update_data
        )
        
        return AgentScheduleResponse.model_validate(updated_schedule)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update schedule: {str(e)}"
        )


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a schedule."""
    
    # Verify schedule exists and user has access
    stmt = select(AgentSchedule).where(
        and_(
            AgentSchedule.id == schedule_id,
            AgentSchedule.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    deleted = await scheduler_service.delete_schedule(
        schedule_id=schedule_id,
        db=db
    )
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete schedule"
        )


@router.post("/schedules/{schedule_id}/trigger", response_model=ScheduledExecutionResponse)
async def trigger_schedule_execution(
    schedule_id: UUID,
    trigger_request: ScheduledExecutionTriggerRequest = ScheduledExecutionTriggerRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger a schedule execution."""
    
    # Verify schedule exists and user has access
    stmt = select(AgentSchedule).where(
        and_(
            AgentSchedule.id == schedule_id,
            AgentSchedule.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    try:
        # Temporarily override the prompt if provided
        if trigger_request.override_prompt:
            original_prompt = schedule.task_prompt
            schedule.task_prompt = trigger_request.override_prompt
        
        redis = await get_redis()
        execution = await scheduler_service.execute_schedule(
            schedule=schedule,
            db=db,
            redis=redis,
            force_execution=True
        )
        
        # Restore original prompt if it was overridden
        if trigger_request.override_prompt:
            schedule.task_prompt = original_prompt
            await db.commit()
        
        return ScheduledExecutionResponse.model_validate(execution)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute schedule: {str(e)}"
        )


@router.get("/schedules/{schedule_id}/executions", response_model=List[ScheduledExecutionResponse])
async def list_schedule_executions(
    schedule_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, regex="^(pending|running|completed|failed|timeout)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List execution history for a schedule."""
    
    # Verify schedule exists and user has access
    stmt = select(AgentSchedule).where(
        and_(
            AgentSchedule.id == schedule_id,
            AgentSchedule.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    executions = await scheduler_service.get_schedule_executions(
        schedule_id=schedule_id,
        limit=limit,
        offset=offset,
        status=status,
        db=db
    )
    
    return [ScheduledExecutionResponse.model_validate(execution) for execution in executions]


@router.get("/organizations/{org_id}/schedules/due")
async def get_due_schedules(
    org_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get schedules that are due for execution (admin endpoint)."""
    
    # Only allow access if user is in the specified org
    if current_user.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # TODO: Add admin role check
    
    due_schedules = await scheduler_service.get_due_schedules(db=db, limit=limit)
    
    # Filter by organization
    org_schedules = [s for s in due_schedules if s.org_id == org_id]
    
    return [AgentScheduleResponse.model_validate(schedule) for schedule in org_schedules]


@router.get("/agents/{agent_id}/schedules/stats")
async def get_agent_schedule_stats(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get agent schedule statistics."""
    
    # Verify agent access
    stmt = select(Agent).where(
        and_(
            Agent.id == agent_id,
            Agent.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Get schedule statistics
    from sqlalchemy import func
    from app.models.agent_schedule import ScheduledExecution
    
    stats_stmt = select(
        func.count(AgentSchedule.id).label("total_schedules"),
        func.count(AgentSchedule.id).filter(AgentSchedule.enabled == True).label("enabled_schedules"),
        func.sum(AgentSchedule.run_count).label("total_runs"),
        func.sum(AgentSchedule.failure_count).label("total_failures")
    ).where(AgentSchedule.agent_id == agent_id)
    
    stats_result = await db.execute(stats_stmt)
    stats = stats_result.first()
    
    # Get recent executions
    recent_executions_stmt = (
        select(ScheduledExecution)
        .join(AgentSchedule, ScheduledExecution.schedule_id == AgentSchedule.id)
        .where(AgentSchedule.agent_id == agent_id)
        .order_by(ScheduledExecution.scheduled_at.desc())
        .limit(10)
    )
    
    recent_result = await db.execute(recent_executions_stmt)
    recent_executions = recent_result.scalars().all()
    
    return {
        "agent_id": str(agent_id),
        "total_schedules": stats.total_schedules or 0,
        "enabled_schedules": stats.enabled_schedules or 0,
        "total_runs": stats.total_runs or 0,
        "total_failures": stats.total_failures or 0,
        "success_rate": (
            ((stats.total_runs - stats.total_failures) / stats.total_runs * 100)
            if stats.total_runs and stats.total_runs > 0
            else 0
        ),
        "recent_executions": [
            {
                "id": str(exec.id),
                "schedule_id": str(exec.schedule_id),
                "status": exec.status,
                "scheduled_at": exec.scheduled_at.isoformat(),
                "completed_at": exec.completed_at.isoformat() if exec.completed_at else None,
                "tokens_used": exec.tokens_used,
                "cost": float(exec.cost) if exec.cost else None,
            }
            for exec in recent_executions
        ]
    }