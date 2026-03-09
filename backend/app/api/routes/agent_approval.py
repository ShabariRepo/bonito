"""
Agent Approval API Routes

Routes for managing approval queues and human-in-the-loop workflows.
"""

from typing import List, Optional
from uuid import UUID
import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.agent import Agent
from app.models.agent_approval import AgentApprovalAction, AgentApprovalConfig
from app.schemas.bonobot import (
    AgentApprovalActionResponse,
    AgentApprovalActionReviewRequest,
    AgentApprovalConfigCreate,
    AgentApprovalConfigUpdate,
    AgentApprovalConfigResponse,
    ApprovalQueueSummaryResponse,
)
from app.services.agent_approval_service import AgentApprovalService

router = APIRouter()
approval_service = AgentApprovalService()


@router.get("/organizations/{org_id}/approvals/queue", response_model=List[AgentApprovalActionResponse])
async def get_approval_queue(
    org_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    agent_id: Optional[UUID] = Query(None),
    action_type: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None, regex="^(low|medium|high|critical)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get pending approval actions in the queue."""
    
    # Verify user has access to this organization
    if current_user.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # TODO: Add role-based permission check for viewing approval queue
    
    pending_approvals = await approval_service.get_pending_approvals(
        org_id=org_id,
        limit=limit,
        offset=offset,
        agent_id=agent_id,
        action_type=action_type,
        risk_level=risk_level,
        db=db
    )
    
    # Enrich with agent and user names
    responses = []
    for approval in pending_approvals:
        # Get agent name
        agent_stmt = select(Agent.name).where(Agent.id == approval.agent_id)
        agent_result = await db.execute(agent_stmt)
        agent_name = agent_result.scalar_one_or_none()
        
        # Get requester name if available
        requester_name = None
        if approval.requested_by:
            user_stmt = select(User.name).where(User.id == approval.requested_by)
            user_result = await db.execute(user_stmt)
            requester_name = user_result.scalar_one_or_none()
        
        approval_response = AgentApprovalActionResponse.model_validate(approval)
        approval_response.agent_name = agent_name
        approval_response.requester_name = requester_name
        
        responses.append(approval_response)
    
    return responses


@router.get("/organizations/{org_id}/approvals/summary", response_model=ApprovalQueueSummaryResponse)
async def get_approval_queue_summary(
    org_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get approval queue summary statistics."""
    
    # Verify user has access to this organization
    if current_user.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    summary = await approval_service.get_approval_queue_summary(
        org_id=org_id,
        db=db
    )
    
    return ApprovalQueueSummaryResponse(**summary)


@router.post("/approvals/{action_id}/review", response_model=AgentApprovalActionResponse)
async def review_approval_action(
    action_id: UUID,
    review_request: AgentApprovalActionReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Review (approve/reject) an approval action."""
    
    # Get the action to verify access
    stmt = select(AgentApprovalAction).where(
        and_(
            AgentApprovalAction.id == action_id,
            AgentApprovalAction.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    action = result.scalar_one_or_none()
    
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval action not found"
        )
    
    # TODO: Add role-based permission check for approving actions
    
    try:
        reviewed_action = await approval_service.review_approval_action(
            action_id=action_id,
            reviewer_id=current_user.id,
            decision=review_request.action,
            review_notes=review_request.review_notes,
            db=db
        )
        
        # If approved, execute the action
        if review_request.action == "approve":
            try:
                await approval_service.execute_approved_action(
                    action_id=action_id,
                    db=db
                )
            except Exception as e:
                # Log the execution error but still return the approval
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to execute approved action {action_id}: {e}")
        
        # Enrich response with names
        agent_stmt = select(Agent.name).where(Agent.id == reviewed_action.agent_id)
        agent_result = await db.execute(agent_stmt)
        agent_name = agent_result.scalar_one_or_none()
        
        response = AgentApprovalActionResponse.model_validate(reviewed_action)
        response.agent_name = agent_name
        response.reviewer_name = current_user.name
        
        return response
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to review approval action: {str(e)}"
        )


@router.get("/approvals/{action_id}", response_model=AgentApprovalActionResponse)
async def get_approval_action(
    action_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get details of a specific approval action."""
    
    stmt = select(AgentApprovalAction).where(
        and_(
            AgentApprovalAction.id == action_id,
            AgentApprovalAction.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    action = result.scalar_one_or_none()
    
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval action not found"
        )
    
    # Enrich with names
    agent_stmt = select(Agent.name).where(Agent.id == action.agent_id)
    agent_result = await db.execute(agent_stmt)
    agent_name = agent_result.scalar_one_or_none()
    
    requester_name = None
    if action.requested_by:
        user_stmt = select(User.name).where(User.id == action.requested_by)
        user_result = await db.execute(user_stmt)
        requester_name = user_result.scalar_one_or_none()
    
    reviewer_name = None
    if action.reviewed_by:
        reviewer_stmt = select(User.name).where(User.id == action.reviewed_by)
        reviewer_result = await db.execute(reviewer_stmt)
        reviewer_name = reviewer_result.scalar_one_or_none()
    
    response = AgentApprovalActionResponse.model_validate(action)
    response.agent_name = agent_name
    response.requester_name = requester_name
    response.reviewer_name = reviewer_name
    
    return response


@router.post("/agents/{agent_id}/approval-configs", response_model=AgentApprovalConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_approval_config(
    agent_id: UUID,
    config_data: AgentApprovalConfigCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create or update approval configuration for an agent action type."""
    
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
    
    # TODO: Add role-based permission check for managing approval configs
    
    try:
        config = await approval_service.create_approval_config(
            agent_id=agent_id,
            action_type=config_data.action_type,
            requires_approval=config_data.requires_approval,
            auto_approve_conditions=config_data.auto_approve_conditions,
            timeout_hours=config_data.timeout_hours,
            required_approvers=config_data.required_approvers,
            risk_assessment_rules=config_data.risk_assessment_rules,
            db=db
        )
        
        return AgentApprovalConfigResponse.model_validate(config)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create approval config: {str(e)}"
        )


@router.get("/agents/{agent_id}/approval-configs", response_model=List[AgentApprovalConfigResponse])
async def list_agent_approval_configs(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List approval configurations for an agent."""
    
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
    
    # Get configs
    configs_stmt = select(AgentApprovalConfig).where(AgentApprovalConfig.agent_id == agent_id)
    configs_result = await db.execute(configs_stmt)
    configs = configs_result.scalars().all()
    
    return [AgentApprovalConfigResponse.model_validate(config) for config in configs]


@router.get("/approval-configs/{config_id}", response_model=AgentApprovalConfigResponse)
async def get_approval_config(
    config_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific approval configuration."""
    
    stmt = select(AgentApprovalConfig).where(
        and_(
            AgentApprovalConfig.id == config_id,
            AgentApprovalConfig.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval config not found"
        )
    
    return AgentApprovalConfigResponse.model_validate(config)


@router.put("/approval-configs/{config_id}", response_model=AgentApprovalConfigResponse)
async def update_approval_config(
    config_id: UUID,
    config_data: AgentApprovalConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an approval configuration."""
    
    stmt = select(AgentApprovalConfig).where(
        and_(
            AgentApprovalConfig.id == config_id,
            AgentApprovalConfig.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval config not found"
        )
    
    # TODO: Add role-based permission check
    
    # Update fields
    update_data = config_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(config, field):
            setattr(config, field, value)
    
    await db.commit()
    await db.refresh(config)
    
    return AgentApprovalConfigResponse.model_validate(config)


@router.delete("/approval-configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_approval_config(
    config_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an approval configuration."""
    
    stmt = select(AgentApprovalConfig).where(
        and_(
            AgentApprovalConfig.id == config_id,
            AgentApprovalConfig.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval config not found"
        )
    
    # TODO: Add role-based permission check
    
    await db.delete(config)
    await db.commit()


@router.post("/approvals/expire-old")
async def expire_old_approvals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Expire old approval actions (admin endpoint)."""
    
    # TODO: Add admin role check
    
    expired_count = await approval_service.expire_old_approvals(db)
    
    return {
        "message": f"Expired {expired_count} approval actions",
        "expired_count": expired_count
    }


@router.get("/organizations/{org_id}/approvals/history")
async def get_approval_history(
    org_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    agent_id: Optional[UUID] = Query(None),
    action_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None, regex="^(pending|approved|rejected|expired|executed)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get approval history with filtering (admin endpoint)."""
    
    # Verify user has access to this organization
    if current_user.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # TODO: Add admin role check
    
    # Build filter conditions
    conditions = [AgentApprovalAction.org_id == org_id]
    
    if agent_id:
        conditions.append(AgentApprovalAction.agent_id == agent_id)
    
    if action_type:
        conditions.append(AgentApprovalAction.action_type == action_type)
    
    if status:
        conditions.append(AgentApprovalAction.status == status)
    
    # Get approval actions
    stmt = (
        select(AgentApprovalAction)
        .where(and_(*conditions))
        .order_by(AgentApprovalAction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    result = await db.execute(stmt)
    actions = result.scalars().all()
    
    # Enrich with names
    responses = []
    for action in actions:
        # Get agent name
        agent_stmt = select(Agent.name).where(Agent.id == action.agent_id)
        agent_result = await db.execute(agent_stmt)
        agent_name = agent_result.scalar_one_or_none()
        
        # Get requester name if available
        requester_name = None
        if action.requested_by:
            user_stmt = select(User.name).where(User.id == action.requested_by)
            user_result = await db.execute(user_stmt)
            requester_name = user_result.scalar_one_or_none()
        
        # Get reviewer name if available
        reviewer_name = None
        if action.reviewed_by:
            reviewer_stmt = select(User.name).where(User.id == action.reviewed_by)
            reviewer_result = await db.execute(reviewer_stmt)
            reviewer_name = reviewer_result.scalar_one_or_none()
        
        action_response = AgentApprovalActionResponse.model_validate(action)
        action_response.agent_name = agent_name
        action_response.requester_name = requester_name
        action_response.reviewer_name = reviewer_name
        
        responses.append(action_response)
    
    return responses