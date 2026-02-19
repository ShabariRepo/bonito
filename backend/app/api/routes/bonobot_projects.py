"""
Bonobot Projects API Routes

Project CRUD operations and project graph visualization
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.agent import Agent
from app.models.agent_connection import AgentConnection
from app.models.agent_trigger import AgentTrigger
from app.schemas.bonobot import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectGraphResponse,
    GraphNode,
    GraphEdge
)

router = APIRouter()


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List projects for the current organization."""
    # Get projects with agent count
    stmt = (
        select(
            Project,
            func.count(Agent.id).label("agent_count")
        )
        .outerjoin(Agent)
        .where(Project.org_id == current_user.org_id)
        .group_by(Project.id)
        .order_by(Project.created_at.desc())
    )
    
    result = await db.execute(stmt)
    projects_with_counts = result.all()
    
    response = []
    for project, agent_count in projects_with_counts:
        project_data = ProjectResponse.model_validate(project)
        project_data.agent_count = agent_count
        response.append(project_data)
    
    return response


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new project."""
    project = Project(
        org_id=current_user.org_id,
        name=project_data.name,
        description=project_data.description,
        budget_monthly=project_data.budget_monthly,
        settings=project_data.settings or {}
    )
    
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    return ProjectResponse.model_validate(project)


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get project details."""
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
    
    # Get agent count
    stmt = select(func.count(Agent.id)).where(Agent.project_id == project_id)
    result = await db.execute(stmt)
    agent_count = result.scalar()
    
    project_data = ProjectResponse.model_validate(project)
    project_data.agent_count = agent_count
    
    return project_data


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update project."""
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
    
    # Update fields
    update_data = project_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    await db.commit()
    await db.refresh(project)
    
    return ProjectResponse.model_validate(project)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete project (set status to archived)."""
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
    
    project.status = "archived"
    await db.commit()


@router.get("/projects/{project_id}/graph", response_model=ProjectGraphResponse)
async def get_project_graph(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get project graph data for React Flow visualization."""
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
    
    # Get agents
    stmt = select(Agent).where(Agent.project_id == project_id)
    result = await db.execute(stmt)
    agents = result.scalars().all()
    
    # Get triggers
    stmt = (
        select(AgentTrigger, Agent.name.label("agent_name"))
        .join(Agent)
        .where(Agent.project_id == project_id)
    )
    result = await db.execute(stmt)
    triggers_with_agents = result.all()
    
    # Get connections
    stmt = (
        select(
            AgentConnection,
            Agent.name.label("source_agent_name"),
            Agent.name.label("target_agent_name")
        )
        .join(Agent, AgentConnection.source_agent_id == Agent.id)
        .join(Agent, AgentConnection.target_agent_id == Agent.id, isouter=True)
        .where(AgentConnection.project_id == project_id)
    )
    result = await db.execute(stmt)
    connections = result.all()
    
    # Build nodes
    nodes = []
    
    # Agent nodes
    for agent in agents:
        node_data = {
            "id": str(agent.id),
            "name": agent.name,
            "description": agent.description,
            "status": agent.status,
            "model_id": agent.model_id,
            "knowledge_base_count": len(agent.knowledge_base_ids) if agent.knowledge_base_ids else 0,
            "total_runs": agent.total_runs,
            "total_cost": float(agent.total_cost),
            "last_active_at": agent.last_active_at.isoformat() if agent.last_active_at else None,
        }
        
        nodes.append(GraphNode(
            id=agent.id,
            type="agent",
            data=node_data,
            position={"x": 100, "y": 100}  # TODO: Store positions in metadata
        ))
    
    # Trigger nodes
    for trigger, agent_name in triggers_with_agents:
        node_data = {
            "id": str(trigger.id),
            "trigger_type": trigger.trigger_type,
            "config": trigger.config,
            "enabled": trigger.enabled,
            "agent_name": agent_name,
            "last_fired_at": trigger.last_fired_at.isoformat() if trigger.last_fired_at else None,
        }
        
        nodes.append(GraphNode(
            id=trigger.id,
            type="trigger",
            data=node_data,
            position={"x": 50, "y": 50}  # TODO: Store positions
        ))
    
    # Build edges
    edges = []
    
    # Connection edges
    for connection, source_name, target_name in connections:
        edge_data = {
            "connection_type": connection.connection_type,
            "label": connection.label or connection.connection_type,
            "enabled": connection.enabled,
            "source_name": source_name,
            "target_name": target_name,
        }
        
        edges.append(GraphEdge(
            id=connection.id,
            source=connection.source_agent_id,
            target=connection.target_agent_id,
            type="connection",
            data=edge_data
        ))
    
    # Trigger edges (trigger → agent)
    for trigger, agent_name in triggers_with_agents:
        edge_data = {
            "trigger_type": trigger.trigger_type,
            "label": trigger.trigger_type,
            "enabled": trigger.enabled,
        }
        
        edges.append(GraphEdge(
            id=UUID(f"trigger-{trigger.id}"),  # Generate unique ID
            source=trigger.id,
            target=trigger.agent_id,
            type="trigger",
            data=edge_data
        ))
    
    return ProjectGraphResponse(
        project_id=project_id,
        nodes=nodes,
        edges=edges
    )