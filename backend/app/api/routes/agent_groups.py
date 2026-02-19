"""
Agent Groups API Routes

Group CRUD operations for organizing agents by department/team
"""

from typing import List, Optional
from uuid import UUID
import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.agent_group import AgentGroup
from app.models.agent import Agent
from app.models.knowledge_base import KnowledgeBase
from app.schemas.bonobot import (
    AgentGroupCreate,
    AgentGroupUpdate,
    AgentGroupResponse,
    AgentResponse
)

router = APIRouter()


@router.post("/projects/{project_id}/groups", response_model=AgentGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_group(
    project_id: UUID,
    group_data: AgentGroupCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new agent group in a project."""
    # Verify project exists and user has access
    stmt = select(Project).where(
        and_(
            Project.id == project_id,
            Project.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # TODO: Check permission - require manage_groups on project
    
    # Validate knowledge base IDs if provided
    if group_data.knowledge_base_ids:
        stmt = select(func.count(KnowledgeBase.id)).where(
            and_(
                KnowledgeBase.id.in_(group_data.knowledge_base_ids),
                KnowledgeBase.org_id == current_user.org_id
            )
        )
        result = await db.execute(stmt)
        valid_kb_count = result.scalar()
        
        if valid_kb_count != len(group_data.knowledge_base_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more knowledge base IDs are invalid"
            )
    
    # Create group
    group = AgentGroup(
        project_id=project_id,
        org_id=current_user.org_id,
        name=group_data.name,
        description=group_data.description,
        knowledge_base_ids=[str(kb_id) for kb_id in (group_data.knowledge_base_ids or [])],
        budget_limit=group_data.budget_limit,
        model_allowlist=group_data.model_allowlist or [],
        tool_policy=group_data.tool_policy or {"mode": "inherit", "allowed": [], "denied": []},
        canvas_position=group_data.canvas_position or {"x": 0, "y": 0},
        canvas_style=group_data.canvas_style or {"backgroundColor": "#f0f0f0", "borderColor": "#ccc"}
    )
    
    db.add(group)
    await db.commit()
    await db.refresh(group)
    
    # Get agent count for response
    stmt = select(func.count(Agent.id)).where(Agent.group_id == group.id)
    result = await db.execute(stmt)
    agent_count = result.scalar()
    
    response = AgentGroupResponse.model_validate(group)
    response.agent_count = agent_count
    
    return response


@router.get("/projects/{project_id}/groups", response_model=List[AgentGroupResponse])
async def list_agent_groups(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List agent groups in a project."""
    # Verify project exists and user has access
    stmt = select(Project).where(
        and_(
            Project.id == project_id,
            Project.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # TODO: Filter by user's group access permissions
    
    # Get groups with agent counts
    stmt = (
        select(
            AgentGroup,
            func.count(Agent.id).label("agent_count")
        )
        .outerjoin(Agent, Agent.group_id == AgentGroup.id)
        .where(AgentGroup.project_id == project_id)
        .group_by(AgentGroup.id)
        .order_by(AgentGroup.created_at.desc())
    )
    result = await db.execute(stmt)
    groups_with_counts = result.all()
    
    response = []
    for group, agent_count in groups_with_counts:
        group_data = AgentGroupResponse.model_validate(group)
        group_data.agent_count = agent_count
        response.append(group_data)
    
    return response


@router.get("/groups/{group_id}", response_model=AgentGroupResponse)
async def get_agent_group(
    group_id: UUID,
    include_knowledge_bases: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get agent group details with optional knowledge base info."""
    stmt = select(AgentGroup).where(
        and_(
            AgentGroup.id == group_id,
            AgentGroup.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent group not found"
        )
    
    # TODO: Check permission - require view access to group
    
    # Get agent count
    stmt = select(func.count(Agent.id)).where(Agent.group_id == group_id)
    result = await db.execute(stmt)
    agent_count = result.scalar()
    
    group_data = AgentGroupResponse.model_validate(group)
    group_data.agent_count = agent_count
    
    # Include knowledge base info if requested
    if include_knowledge_bases and group.knowledge_base_ids:
        stmt = select(KnowledgeBase.id, KnowledgeBase.name).where(
            KnowledgeBase.id.in_([UUID(kb_id) for kb_id in group.knowledge_base_ids])
        )
        result = await db.execute(stmt)
        kbs = result.all()
        group_data.knowledge_bases = [{"id": str(kb.id), "name": kb.name} for kb in kbs]
    
    return group_data


@router.put("/groups/{group_id}", response_model=AgentGroupResponse)
async def update_agent_group(
    group_id: UUID,
    group_data: AgentGroupUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update agent group configuration."""
    stmt = select(AgentGroup).where(
        and_(
            AgentGroup.id == group_id,
            AgentGroup.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent group not found"
        )
    
    # TODO: Check permission - require manage_groups on group's project
    
    # Validate knowledge base IDs if being updated
    if group_data.knowledge_base_ids is not None:
        if group_data.knowledge_base_ids:
            stmt = select(func.count(KnowledgeBase.id)).where(
                and_(
                    KnowledgeBase.id.in_(group_data.knowledge_base_ids),
                    KnowledgeBase.org_id == current_user.org_id
                )
            )
            result = await db.execute(stmt)
            valid_kb_count = result.scalar()
            
            if valid_kb_count != len(group_data.knowledge_base_ids):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="One or more knowledge base IDs are invalid"
                )
    
    # Update fields
    update_data = group_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "knowledge_base_ids" and value is not None:
            value = [str(kb_id) for kb_id in value]
        setattr(group, field, value)
    
    await db.commit()
    await db.refresh(group)
    
    # Get agent count for response
    stmt = select(func.count(Agent.id)).where(Agent.group_id == group_id)
    result = await db.execute(stmt)
    agent_count = result.scalar()
    
    response = AgentGroupResponse.model_validate(group)
    response.agent_count = agent_count
    
    return response


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent_group(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete agent group. Agents in the group will have their group_id set to NULL."""
    stmt = select(AgentGroup).where(
        and_(
            AgentGroup.id == group_id,
            AgentGroup.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent group not found"
        )
    
    # TODO: Check permission - require manage_groups on group's project
    
    await db.delete(group)
    await db.commit()


@router.get("/groups/{group_id}/agents", response_model=List[AgentResponse])
async def list_group_agents(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List agents in a group."""
    # Verify group exists and user has access
    stmt = select(AgentGroup).where(
        and_(
            AgentGroup.id == group_id,
            AgentGroup.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent group not found"
        )
    
    # TODO: Check permission - require view access to group
    
    # Get agents in group
    stmt = select(Agent).where(Agent.group_id == group_id).order_by(Agent.created_at.desc())
    result = await db.execute(stmt)
    agents = result.scalars().all()
    
    return [AgentResponse.model_validate(agent) for agent in agents]


@router.post("/groups/{group_id}/agents/{agent_id}/assign", status_code=status.HTTP_200_OK)
async def assign_agent_to_group(
    group_id: UUID,
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Assign an agent to a group."""
    # Verify group exists and user has access
    stmt = select(AgentGroup).where(
        and_(
            AgentGroup.id == group_id,
            AgentGroup.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent group not found"
        )
    
    # Verify agent exists, is in same project, and user has access
    stmt = select(Agent).where(
        and_(
            Agent.id == agent_id,
            Agent.project_id == group.project_id,
            Agent.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or not in same project"
        )
    
    # TODO: Check permission - require manage_agents on agent and manage_groups on group
    
    # Assign agent to group
    agent.group_id = group_id
    await db.commit()
    
    return {"message": "Agent assigned to group successfully"}


@router.post("/groups/{group_id}/agents/{agent_id}/unassign", status_code=status.HTTP_200_OK)
async def unassign_agent_from_group(
    group_id: UUID,
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove an agent from a group."""
    # Verify agent exists and is in the specified group
    stmt = select(Agent).where(
        and_(
            Agent.id == agent_id,
            Agent.group_id == group_id,
            Agent.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found in specified group"
        )
    
    # TODO: Check permission - require manage_agents on agent
    
    # Remove agent from group
    agent.group_id = None
    await db.commit()
    
    return {"message": "Agent removed from group successfully"}