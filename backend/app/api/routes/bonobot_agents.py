"""
Bonobot Agents API Routes

Agent CRUD operations and execution endpoints
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID
import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, and_, desc, or_, case, literal_column
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.redis import get_redis
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.organization import Organization
from app.models.project import Project
from app.models.agent import Agent
from app.models.agent_session import AgentSession
from app.models.agent_message import AgentMessage
from app.models.agent_connection import AgentConnection
from app.models.agent_trigger import AgentTrigger
from app.models.knowledge_base import KnowledgeBase
from app.schemas.bonobot import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentDetailResponse,
    AgentSessionResponse,
    AgentMessageResponse,
    AgentConnectionCreate,
    AgentConnectionResponse,
    AgentTriggerCreate,
    AgentTriggerResponse,
    AgentExecuteRequest,
    AgentExecuteResponse,
)
from app.services.agent_engine import AgentEngine, AgentRateLimitError

router = APIRouter()
agent_engine = AgentEngine()


@router.get("/projects/{project_id}/agents", response_model=List[AgentResponse])
async def list_agents_in_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List agents in a project."""
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
    stmt = select(Agent).where(Agent.project_id == project_id).order_by(Agent.created_at.desc())
    result = await db.execute(stmt)
    agents = result.scalars().all()
    
    return [AgentResponse.model_validate(agent) for agent in agents]


@router.post("/projects/{project_id}/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    project_id: UUID,
    agent_data: AgentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new agent in a project."""
    # Feature gate: check bonobot_plan and agent limit
    stmt = select(Organization).where(Organization.id == current_user.org_id)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    
    if not org or org.bonobot_plan == "none":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Bonobot agents require a Pro or Enterprise plan. Upgrade at getbonito.com/pricing",
                "required_tier": "pro",
                "upgrade_url": "https://getbonito.com/pricing"
            }
        )
    
    # Check agent limit (-1 = unlimited)
    if org.bonobot_agent_limit >= 0:
        stmt = select(func.count(Agent.id)).join(Project).where(
            and_(Project.org_id == current_user.org_id, Agent.status != "archived")
        )
        result = await db.execute(stmt)
        current_count = result.scalar() or 0
        if current_count >= org.bonobot_agent_limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": f"Agent limit reached ({org.bonobot_agent_limit}). Upgrade your plan for more agents.",
                    "required_tier": "enterprise",
                    "upgrade_url": "https://getbonito.com/pricing"
                }
            )
    
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
    
    # Validate group exists if provided
    if agent_data.group_id:
        from app.models.agent_group import AgentGroup
        stmt = select(AgentGroup).where(
            and_(
                AgentGroup.id == agent_data.group_id,
                AgentGroup.project_id == project_id,
                AgentGroup.org_id == current_user.org_id
            )
        )
        result = await db.execute(stmt)
        group = result.scalar_one_or_none()
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent group not found or not in same project"
            )
    
    # Validate knowledge base IDs if provided
    if agent_data.knowledge_base_ids:
        stmt = select(func.count(KnowledgeBase.id)).where(
            and_(
                KnowledgeBase.id.in_(agent_data.knowledge_base_ids),
                KnowledgeBase.org_id == current_user.org_id
            )
        )
        result = await db.execute(stmt)
        valid_kb_count = result.scalar()
        
        if valid_kb_count != len(agent_data.knowledge_base_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more knowledge base IDs are invalid"
            )
    
    # Create agent
    agent = Agent(
        project_id=project_id,
        org_id=current_user.org_id,
        group_id=agent_data.group_id,
        name=agent_data.name,
        description=agent_data.description,
        system_prompt=agent_data.system_prompt,
        model_id=agent_data.model_id,
        model_config=agent_data.agent_model_config or {},
        knowledge_base_ids=[str(kb_id) for kb_id in (agent_data.knowledge_base_ids or [])],
        tool_policy=agent_data.tool_policy or {"mode": "none", "allowed": [], "denied": [], "http_allowlist": []},
        max_turns=agent_data.max_turns,
        timeout_seconds=agent_data.timeout_seconds,
        compaction_enabled=agent_data.compaction_enabled,
        max_session_messages=agent_data.max_session_messages,
        rate_limit_rpm=agent_data.rate_limit_rpm,
        budget_alert_threshold=agent_data.budget_alert_threshold,
        autoscale_enabled=agent_data.autoscale_enabled or False,
        autoscale_config=agent_data.autoscale_config,
    )
    
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    
    return AgentResponse.model_validate(agent)


@router.get("/agents/{agent_id}", response_model=AgentDetailResponse)
async def get_agent(
    agent_id: UUID,
    include_sessions: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get agent details with optional recent sessions."""
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
    
    agent_data = AgentDetailResponse.model_validate(agent)
    
    # Include recent sessions if requested
    if include_sessions:
        stmt = (
            select(AgentSession)
            .where(AgentSession.agent_id == agent_id)
            .order_by(desc(AgentSession.last_message_at))
            .limit(10)
        )
        result = await db.execute(stmt)
        sessions = result.scalars().all()
        agent_data.recent_sessions = [AgentSessionResponse.model_validate(s) for s in sessions]
    
    # Include knowledge base info if agent has any
    if agent.knowledge_base_ids:
        stmt = select(KnowledgeBase.id, KnowledgeBase.name).where(
            KnowledgeBase.id.in_([UUID(kb_id) for kb_id in agent.knowledge_base_ids])
        )
        result = await db.execute(stmt)
        kbs = result.all()
        agent_data.knowledge_bases = [{"id": str(kb.id), "name": kb.name} for kb in kbs]
    
    return agent_data


@router.put("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update agent configuration."""
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
    
    # Validate group exists if being updated
    if agent_data.group_id is not None:
        if agent_data.group_id:  # Not None and not setting to None
            from app.models.agent_group import AgentGroup
            stmt = select(AgentGroup).where(
                and_(
                    AgentGroup.id == agent_data.group_id,
                    AgentGroup.project_id == agent.project_id,
                    AgentGroup.org_id == current_user.org_id
                )
            )
            result = await db.execute(stmt)
            group = result.scalar_one_or_none()
            
            if not group:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Agent group not found or not in same project"
                )

    # Validate knowledge base IDs if being updated
    if agent_data.knowledge_base_ids is not None:
        if agent_data.knowledge_base_ids:
            stmt = select(func.count(KnowledgeBase.id)).where(
                and_(
                    KnowledgeBase.id.in_(agent_data.knowledge_base_ids),
                    KnowledgeBase.org_id == current_user.org_id
                )
            )
            result = await db.execute(stmt)
            valid_kb_count = result.scalar()
            
            if valid_kb_count != len(agent_data.knowledge_base_ids):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="One or more knowledge base IDs are invalid"
                )
    
    # Update fields
    update_data = agent_data.model_dump(exclude_unset=True, by_alias=True)
    for field, value in update_data.items():
        if field == "knowledge_base_ids" and value is not None:
            value = [str(kb_id) for kb_id in value]
        setattr(agent, field, value)
    
    await db.commit()
    await db.refresh(agent)
    
    return AgentResponse.model_validate(agent)


@router.patch("/agents/{agent_id}", response_model=AgentResponse)
async def patch_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Partial update agent configuration (alias for PUT with same semantics)."""
    return await update_agent(agent_id, agent_data, current_user, db)


@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete agent (set status to disabled)."""
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
    
    agent.status = "disabled"
    await db.commit()


@router.post("/agents/{agent_id}/execute", response_model=AgentExecuteResponse)
async def execute_agent(
    agent_id: UUID,
    request: AgentExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Execute agent with a message."""
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
    
    if agent.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent is not active"
        )
    
    redis = await get_redis()

    try:
        # Execute via agent engine with user context
        result = await agent_engine.execute(
            agent=agent,
            message=request.message,
            session_id=request.session_id,
            db=db,
            redis=redis,
            user_id=current_user.id
        )

        # Get the session ID (either existing or newly created)
        if request.session_id:
            session_id = request.session_id
        else:
            # Find the most recent session for this agent
            stmt = (
                select(AgentSession.id)
                .where(AgentSession.agent_id == agent_id)
                .order_by(desc(AgentSession.last_message_at))
                .limit(1)
            )
            db_result = await db.execute(stmt)
            session_id = db_result.scalar_one()

        # ── External orchestration: log delegation for Breadcrumbs ──
        # Best-effort — a logging failure must never kill the agent response.
        if request.parent_agent_id:
            try:
                await _log_external_delegation(
                    parent_agent_id=request.parent_agent_id,
                    target_agent_id=agent_id,
                    target_agent_name=agent.name,
                    org_id=current_user.org_id,
                    message_preview=request.message[:200],
                    db=db,
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    "Breadcrumb delegation logging failed (non-fatal): parent=%s target=%s error=%s",
                    request.parent_agent_id, agent_id, e,
                )

        return AgentExecuteResponse(
            run_id=uuid_lib.uuid4(),  # Generate a run ID
            session_id=session_id,
            agent_id=agent_id,
            content=result.content,
            tokens=result.tokens,
            cost=result.cost,
            turns=result.turns,
            model_used=result.model_used,
            security=result.security,
            created_at=agent.last_active_at or agent.updated_at
        )

    except AgentRateLimitError:
        # ── Overflow queue: enqueue instead of dropping ──
        if agent.autoscale_enabled:
            from app.services.agent_queue import enqueue_request
            queue_result = await enqueue_request(
                agent_id=agent_id,
                org_id=current_user.org_id,
                user_id=current_user.id,
                message=request.message,
                session_id=request.session_id,
                parent_agent_id=request.parent_agent_id,
                redis=redis,
            )
            if queue_result.get("queued"):
                return JSONResponse(
                    status_code=202,
                    content={
                        "status": "queued",
                        "ticket_id": queue_result["ticket_id"],
                        "position": queue_result["position"],
                        "estimated_wait_seconds": queue_result["estimated_wait_seconds"],
                        "poll_url": f"/api/agents/{agent_id}/queue/{queue_result['ticket_id']}",
                        "message": f"Agent at capacity. Request queued at position {queue_result['position']}.",
                    },
                )
        # No queue or queue full — return 429
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}"
        )


@router.get("/agents/{agent_id}/queue/{ticket_id}")
async def get_queue_status_endpoint(
    agent_id: UUID,
    ticket_id: str,
    current_user: User = Depends(get_current_user),
):
    """Poll status of a queued agent execution request."""
    from app.services.agent_queue import get_queue_status
    redis = await get_redis()
    result = await get_queue_status(ticket_id, redis)
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Queue ticket not found")
    return result


@router.get("/agents/{agent_id}/queue")
async def get_agent_queue_info(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """Get queue depth and status for an agent."""
    from app.services.agent_queue import get_agent_queue_depth
    redis = await get_redis()
    depth = await get_agent_queue_depth(agent_id, redis)
    return {"agent_id": str(agent_id), "queue_depth": depth}


@router.get("/agents/{agent_id}/sessions", response_model=List[AgentSessionResponse])
async def list_agent_sessions(
    agent_id: UUID,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List agent sessions."""
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
    
    # Get sessions
    stmt = (
        select(AgentSession)
        .where(AgentSession.agent_id == agent_id)
        .order_by(desc(AgentSession.last_message_at))
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    
    return [AgentSessionResponse.model_validate(session) for session in sessions]


@router.get("/agents/{agent_id}/sessions/{session_id}/messages", response_model=List[AgentMessageResponse])
async def get_session_messages(
    agent_id: UUID,
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get messages in a session."""
    # Verify session exists and belongs to user's agent
    stmt = (
        select(AgentSession)
        .join(Agent)
        .where(
            and_(
                AgentSession.id == session_id,
                Agent.id == agent_id,
                Agent.org_id == current_user.org_id
            )
        )
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Get messages
    stmt = (
        select(AgentMessage)
        .where(AgentMessage.session_id == session_id)
        .order_by(AgentMessage.sequence)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()
    
    return [AgentMessageResponse.model_validate(msg) for msg in messages]


# ─── Metrics ───


@router.get("/agents/{agent_id}/metrics")
async def get_agent_metrics(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get agent usage metrics."""
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

    # Count sessions
    session_count_stmt = select(func.count(AgentSession.id)).where(AgentSession.agent_id == agent_id)
    session_count = (await db.execute(session_count_stmt)).scalar() or 0

    # Recent sessions for activity timeline
    recent_stmt = (
        select(AgentSession.created_at, AgentSession.total_tokens, AgentSession.total_cost)
        .where(AgentSession.agent_id == agent_id)
        .order_by(desc(AgentSession.created_at))
        .limit(20)
    )
    recent = (await db.execute(recent_stmt)).all()

    return {
        "agent_id": str(agent.id),
        "total_runs": agent.total_runs,
        "total_tokens": agent.total_tokens,
        "total_cost": float(agent.total_cost),
        "total_sessions": session_count,
        "status": agent.status,
        "last_active_at": agent.last_active_at.isoformat() if agent.last_active_at else None,
        "recent_sessions": [
            {
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "tokens": s.total_tokens,
                "cost": float(s.total_cost) if s.total_cost else 0,
            }
            for s in recent
        ],
    }


# ─── Connections ───

@router.post("/agents/{agent_id}/connections", response_model=AgentConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_connection(
    agent_id: UUID,
    connection_data: AgentConnectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create connection from this agent to another agent."""
    # Verify source agent exists and user has access
    stmt = select(Agent).where(
        and_(
            Agent.id == agent_id,
            Agent.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    source_agent = result.scalar_one_or_none()
    
    if not source_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source agent not found"
        )
    
    # Verify target agent exists and is in same project
    stmt = select(Agent).where(
        and_(
            Agent.id == connection_data.target_agent_id,
            Agent.project_id == source_agent.project_id,
            Agent.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    target_agent = result.scalar_one_or_none()
    
    if not target_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target agent not found or not in same project"
        )
    
    # Create connection
    connection = AgentConnection(
        project_id=source_agent.project_id,
        org_id=current_user.org_id,
        source_agent_id=agent_id,
        target_agent_id=connection_data.target_agent_id,
        connection_type=connection_data.connection_type,
        label=connection_data.label,
        condition=connection_data.condition,
        enabled=connection_data.enabled
    )
    
    db.add(connection)
    await db.commit()
    await db.refresh(connection)
    
    # Add agent names
    response = AgentConnectionResponse.model_validate(connection)
    response.source_agent_name = source_agent.name
    response.target_agent_name = target_agent.name
    
    return response


@router.get("/agents/{agent_id}/connections", response_model=List[AgentConnectionResponse])
async def list_agent_connections(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List connections from this agent."""
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
    
    # Get connections — use aliased Agent for source/target to avoid duplicate join
    from sqlalchemy.orm import aliased
    SourceAgent = aliased(Agent, name="source_agent")
    TargetAgent = aliased(Agent, name="target_agent")

    stmt = (
        select(
            AgentConnection,
            SourceAgent.name.label("source_name"),
            TargetAgent.name.label("target_name")
        )
        .join(SourceAgent, AgentConnection.source_agent_id == SourceAgent.id)
        .join(TargetAgent, AgentConnection.target_agent_id == TargetAgent.id, isouter=True)
        .where(AgentConnection.source_agent_id == agent_id)
    )
    result = await db.execute(stmt)
    connections_with_names = result.all()
    
    response = []
    for connection, source_name, target_name in connections_with_names:
        conn_data = AgentConnectionResponse.model_validate(connection)
        conn_data.source_agent_name = source_name
        conn_data.target_agent_name = target_name
        response.append(conn_data)
    
    return response


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a connection."""
    stmt = select(AgentConnection).where(
        and_(
            AgentConnection.id == connection_id,
            AgentConnection.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    connection = result.scalar_one_or_none()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    await db.delete(connection)
    await db.commit()


# ─── Triggers ───

@router.post("/agents/{agent_id}/triggers", response_model=AgentTriggerResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_trigger(
    agent_id: UUID,
    trigger_data: AgentTriggerCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create trigger for agent."""
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
    
    # Create trigger
    trigger = AgentTrigger(
        agent_id=agent_id,
        org_id=current_user.org_id,
        trigger_type=trigger_data.trigger_type,
        config=trigger_data.config or {},
        enabled=trigger_data.enabled
    )
    
    db.add(trigger)
    await db.commit()
    await db.refresh(trigger)
    
    return AgentTriggerResponse.model_validate(trigger)


@router.get("/agents/{agent_id}/triggers", response_model=List[AgentTriggerResponse])
async def list_agent_triggers(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List triggers for agent."""
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
    
    # Get triggers
    stmt = select(AgentTrigger).where(AgentTrigger.agent_id == agent_id)
    result = await db.execute(stmt)
    triggers = result.scalars().all()
    
    return [AgentTriggerResponse.model_validate(trigger) for trigger in triggers]


@router.delete("/triggers/{trigger_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trigger(
    trigger_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a trigger."""
    stmt = select(AgentTrigger).where(
        and_(
            AgentTrigger.id == trigger_id,
            AgentTrigger.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    trigger = result.scalar_one_or_none()
    
    if not trigger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trigger not found"
        )
    
    await db.delete(trigger)
    await db.commit()


# ─── Breadcrumbs (Visual Trace) ───


def _parse_iso_date(date_str: Optional[str], end_of_day: bool = False) -> Optional[datetime]:
    """Parse an ISO date string into a timezone-aware datetime, or return None.

    The frontend sends plain dates like '2026-05-24' which parse as naive
    datetimes at midnight.  Agent messages are stored with timezone-aware
    timestamps (UTC), so comparing naive vs aware silently returns no rows
    in PostgreSQL.  We normalise to UTC here.

    When *end_of_day* is True and the input is a date-only string (no time
    component), the result is snapped to 23:59:59.999999 so that a
    ``date_to`` filter includes the entire day.
    """
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str)
        # date-only strings have no time component → snap to end of day
        if end_of_day and "T" not in date_str:
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {date_str}. Use ISO 8601 (e.g. 2026-01-15T00:00:00Z)."
        )


@router.get("/projects/{project_id}/breadcrumbs")
async def get_project_breadcrumbs(
    project_id: UUID,
    date_from: Optional[str] = Query(None, description="ISO 8601 start date filter"),
    date_to: Optional[str] = Query(None, description="ISO 8601 end date filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return a visual trace of agent interactions within a project.

    Produces nodes (agents) and edges (connections with interaction counts)
    suitable for rendering a React Flow diagram.
    """
    # Parse date filters
    dt_from = _parse_iso_date(date_from)
    dt_to = _parse_iso_date(date_to, end_of_day=True)

    # ── Verify project access ──
    stmt = select(Project).where(
        and_(
            Project.id == project_id,
            Project.org_id == current_user.org_id,
        )
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # ── Nodes: all agents in the project ──
    stmt = select(Agent).where(Agent.project_id == project_id).order_by(Agent.created_at)
    result = await db.execute(stmt)
    agents = result.scalars().all()
    agent_ids = [a.id for a in agents]

    # Build date-range filter conditions for agent_messages
    date_conditions = []
    if dt_from:
        date_conditions.append(AgentMessage.created_at >= dt_from)
    if dt_to:
        date_conditions.append(AgentMessage.created_at <= dt_to)

    # Per-agent message counts within the date range
    message_counts: dict[UUID, int] = {}
    if agent_ids:
        msg_count_stmt = (
            select(
                AgentSession.agent_id,
                func.count(AgentMessage.id).label("cnt"),
            )
            .join(AgentSession, AgentMessage.session_id == AgentSession.id)
            .where(AgentSession.agent_id.in_(agent_ids))
        )
        if date_conditions:
            msg_count_stmt = msg_count_stmt.where(and_(*date_conditions))
        msg_count_stmt = msg_count_stmt.group_by(AgentSession.agent_id)

        result = await db.execute(msg_count_stmt)
        for row in result.all():
            message_counts[row.agent_id] = row.cnt

    nodes = []
    for agent in agents:
        nodes.append({
            "id": str(agent.id),
            "name": agent.name,
            "description": agent.description,
            "status": agent.status,
            "model_id": agent.model_id,
            "total_runs": agent.total_runs,
            "total_cost": float(agent.total_cost),
            "last_active_at": agent.last_active_at.isoformat() if agent.last_active_at else None,
            "position": agent.canvas_position,
            "message_count": message_counts.get(agent.id, 0),
        })

    # ── Edges: connections + interaction counts ──
    stmt = select(AgentConnection).where(
        and_(
            AgentConnection.project_id == project_id,
            AgentConnection.org_id == current_user.org_id,
        )
    )
    result = await db.execute(stmt)
    connections = result.scalars().all()

    # For each connection, count invoke_agent and delegate_task interactions
    # within the date range.
    #
    # Native invoke_agent calls are recorded in TWO messages:
    #   1. role="assistant" with tool_calls=[{function:{name:"invoke_agent", arguments:{agent_id:...}}}]
    #   2. role="tool" with tool_name="invoke_agent" but tool_calls=NULL (only tool_call_id + result)
    #
    # We query ASSISTANT messages that have non-null tool_calls, then parse
    # the JSON in Python to extract function names and target agent_ids.
    # We also query TOOL messages with tool_name set (for external orchestration
    # via _log_external_delegation which sets both tool_name and tool_calls).

    interaction_map: dict[tuple[UUID, UUID], dict[str, int]] = {}

    if connections:
        source_ids = list({c.source_agent_id for c in connections})

        # Query 1: Assistant messages with tool_calls (native invoke_agent)
        assistant_stmt = (
            select(
                AgentSession.agent_id.label("source_agent_id"),
                AgentMessage.tool_calls,
            )
            .join(AgentSession, AgentMessage.session_id == AgentSession.id)
            .where(
                and_(
                    AgentSession.agent_id.in_(source_ids),
                    AgentMessage.role == "assistant",
                    AgentMessage.tool_calls.isnot(None),
                )
            )
        )
        if date_conditions:
            assistant_stmt = assistant_stmt.where(and_(*date_conditions))

        result = await db.execute(assistant_stmt)
        assistant_rows = result.all()

        for row in assistant_rows:
            if not row.tool_calls:
                continue
            calls = row.tool_calls if isinstance(row.tool_calls, list) else [row.tool_calls]
            for call in calls:
                fn = call.get("function") if isinstance(call, dict) else None
                if not fn:
                    continue
                fn_name = fn.get("name")
                if fn_name not in ("invoke_agent", "delegate_task"):
                    continue
                target_id = _extract_target_agent_id([call])
                if target_id is None:
                    continue
                key = (row.source_agent_id, target_id)
                if key not in interaction_map:
                    interaction_map[key] = {"invoke_agent": 0, "delegate_task": 0}
                interaction_map[key][fn_name] += 1

        # Query 2: Tool messages from external orchestration (_log_external_delegation)
        ext_stmt = (
            select(
                AgentSession.agent_id.label("source_agent_id"),
                AgentMessage.tool_name,
                AgentMessage.tool_calls,
            )
            .join(AgentSession, AgentMessage.session_id == AgentSession.id)
            .where(
                and_(
                    AgentSession.agent_id.in_(source_ids),
                    AgentMessage.role == "tool",
                    AgentMessage.tool_name.in_(["invoke_agent", "delegate_task"]),
                    AgentMessage.tool_calls.isnot(None),
                )
            )
        )
        if date_conditions:
            ext_stmt = ext_stmt.where(and_(*date_conditions))

        result = await db.execute(ext_stmt)
        ext_rows = result.all()

        for row in ext_rows:
            target_id = _extract_target_agent_id(row.tool_calls)
            if target_id is None:
                continue
            key = (row.source_agent_id, target_id)
            if key not in interaction_map:
                interaction_map[key] = {"invoke_agent": 0, "delegate_task": 0}
            if row.tool_name in interaction_map[key]:
                interaction_map[key][row.tool_name] += 1

    edges = []
    for conn in connections:
        key = (conn.source_agent_id, conn.target_agent_id)
        counts = interaction_map.get(key, {"invoke_agent": 0, "delegate_task": 0})
        edges.append({
            "id": str(conn.id),
            "source": str(conn.source_agent_id),
            "target": str(conn.target_agent_id),
            "connection_type": conn.connection_type,
            "label": conn.label,
            "interactions": {
                "total": counts["invoke_agent"] + counts["delegate_task"],
                "invoke_agent": counts["invoke_agent"],
                "delegate_task": counts["delegate_task"],
            },
        })

    return {
        "project_id": str(project_id),
        "date_from": date_from,
        "date_to": date_to,
        "nodes": nodes,
        "edges": edges,
    }


async def _log_external_delegation(
    parent_agent_id: UUID,
    target_agent_id: UUID,
    target_agent_name: str,
    org_id: UUID,
    message_preview: str,
    db: AsyncSession,
) -> None:
    """
    Record a synthetic invoke_agent tool-call message in the parent agent's
    most recent session.  This lets the Breadcrumbs query pick up external
    (code-orchestrated) delegations with the same format as native
    invoke_agent calls from the AgentEngine.

    If the parent agent has no session yet, one is created automatically.
    Skips silently if the parent agent doesn't exist or belongs to a
    different org (prevents cross-tenant writes).
    """
    import json as _json
    import logging as _logging

    _logger = _logging.getLogger(__name__)

    # ── Validate parent agent exists and belongs to same org ──
    parent_stmt = select(Agent).where(
        and_(
            Agent.id == parent_agent_id,
            Agent.org_id == org_id,
        )
    )
    parent_result = await db.execute(parent_stmt)
    parent_agent = parent_result.scalar_one_or_none()

    if not parent_agent:
        _logger.warning(
            "Breadcrumb skip: parent_agent_id=%s not found or wrong org=%s",
            parent_agent_id, org_id,
        )
        return

    # Find or create a session for the parent agent
    stmt = (
        select(AgentSession)
        .where(AgentSession.agent_id == parent_agent_id)
        .order_by(desc(AgentSession.last_message_at))
        .limit(1)
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        session = AgentSession(
            id=uuid_lib.uuid4(),
            agent_id=parent_agent_id,
            org_id=org_id,
            started_at=func.now(),
            last_message_at=func.now(),
            message_count=0,
        )
        db.add(session)
        await db.flush()

    # Next sequence number
    seq_stmt = (
        select(func.coalesce(func.max(AgentMessage.sequence), 0))
        .where(AgentMessage.session_id == session.id)
    )
    seq_result = await db.execute(seq_stmt)
    next_seq = seq_result.scalar() + 1

    # Create the synthetic tool-call message (same shape the engine uses)
    tool_call_payload = [{
        "id": f"ext-{uuid_lib.uuid4().hex[:12]}",
        "function": {
            "name": "invoke_agent",
            "arguments": _json.dumps({
                "agent_id": str(target_agent_id),
                "agent_name": target_agent_name,
                "message_preview": message_preview,
            }),
        },
    }]

    delegation_msg = AgentMessage(
        id=uuid_lib.uuid4(),
        session_id=session.id,
        org_id=org_id,
        role="tool",
        content=_json.dumps({
            "source": "external_orchestrator",
            "target_agent_id": str(target_agent_id),
            "target_agent_name": target_agent_name,
        }),
        tool_calls=tool_call_payload,
        tool_name="invoke_agent",
        sequence=next_seq,
    )
    db.add(delegation_msg)

    # Bump session counters
    session.message_count = (session.message_count or 0) + 1
    session.last_message_at = func.now()

    await db.flush()


def _extract_target_agent_id(tool_calls) -> Optional[UUID]:
    """
    Extract the target agent_id from a tool_calls JSON column.

    Expected shape: [{function: {name: "invoke_agent", arguments: '{"agent_id": "..."}' }}]
    The arguments value may be a JSON string or already-parsed dict.
    """
    import json as _json

    if not tool_calls:
        return None

    calls = tool_calls if isinstance(tool_calls, list) else [tool_calls]
    for call in calls:
        fn = call.get("function") if isinstance(call, dict) else None
        if not fn:
            continue
        args = fn.get("arguments")
        if args is None:
            continue
        # arguments may be a JSON-encoded string or a dict
        if isinstance(args, str):
            try:
                args = _json.loads(args)
            except (ValueError, TypeError):
                continue
        if isinstance(args, dict):
            aid = args.get("agent_id")
            if aid:
                try:
                    return UUID(str(aid))
                except (ValueError, TypeError):
                    continue
    return None


@router.get("/projects/{project_id}/breadcrumbs/agents/{agent_id}/messages")
async def get_breadcrumb_agent_messages(
    project_id: UUID,
    agent_id: UUID,
    date_from: Optional[str] = Query(None, description="ISO 8601 start date filter"),
    date_to: Optional[str] = Query(None, description="ISO 8601 end date filter"),
    role: Optional[str] = Query(None, description="Filter by role/type: user, assistant, system, tool, invoke_agent, delegate_task"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Paginated messages for a specific agent within the breadcrumbs context.

    Returns messages across all sessions for this agent, filtered by date range
    and optionally by role/interaction type.
    """
    dt_from = _parse_iso_date(date_from)
    dt_to = _parse_iso_date(date_to, end_of_day=True)

    # Verify project access
    stmt = select(Project).where(
        and_(
            Project.id == project_id,
            Project.org_id == current_user.org_id,
        )
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Verify agent belongs to this project and org
    stmt = select(Agent).where(
        and_(
            Agent.id == agent_id,
            Agent.project_id == project_id,
            Agent.org_id == current_user.org_id,
        )
    )
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found in this project",
        )

    # Build role filter conditions
    role_conditions = []
    if role:
        if role in ("user", "assistant", "system", "tool"):
            role_conditions.append(AgentMessage.role == role)
        elif role == "invoke_agent":
            # Match tool messages with tool_name OR assistant messages with invoke_agent in tool_calls
            role_conditions.append(
                or_(
                    and_(AgentMessage.role == "tool", AgentMessage.tool_name == "invoke_agent"),
                    and_(AgentMessage.role == "assistant", AgentMessage.tool_calls.isnot(None)),
                )
            )
        elif role == "delegate_task":
            role_conditions.append(
                or_(
                    and_(AgentMessage.role == "tool", AgentMessage.tool_name == "delegate_task"),
                    and_(AgentMessage.role == "assistant", AgentMessage.tool_calls.isnot(None)),
                )
            )

    # Build message query across all sessions for this agent
    msg_stmt = (
        select(AgentMessage)
        .join(AgentSession, AgentMessage.session_id == AgentSession.id)
        .where(AgentSession.agent_id == agent_id)
        .order_by(desc(AgentMessage.created_at))
    )

    if dt_from:
        msg_stmt = msg_stmt.where(AgentMessage.created_at >= dt_from)
    if dt_to:
        msg_stmt = msg_stmt.where(AgentMessage.created_at <= dt_to)
    for cond in role_conditions:
        msg_stmt = msg_stmt.where(cond)

    # Total count for pagination
    count_stmt = (
        select(func.count(AgentMessage.id))
        .join(AgentSession, AgentMessage.session_id == AgentSession.id)
        .where(AgentSession.agent_id == agent_id)
    )
    if dt_from:
        count_stmt = count_stmt.where(AgentMessage.created_at >= dt_from)
    if dt_to:
        count_stmt = count_stmt.where(AgentMessage.created_at <= dt_to)
    for cond in role_conditions:
        count_stmt = count_stmt.where(cond)

    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Fetch paginated messages
    msg_stmt = msg_stmt.limit(limit).offset(offset)
    result = await db.execute(msg_stmt)
    messages = result.scalars().all()

    return {
        "agent_id": str(agent_id),
        "project_id": str(project_id),
        "date_from": date_from,
        "date_to": date_to,
        "total": total,
        "limit": limit,
        "offset": offset,
        "messages": [
            {
                "id": str(msg.id),
                "session_id": str(msg.session_id),
                "role": msg.role,
                "content": msg.content,
                "tool_name": msg.tool_name,
                "tool_calls": msg.tool_calls,
                "tool_call_id": msg.tool_call_id,
                "model_used": msg.model_used,
                "input_tokens": msg.input_tokens,
                "output_tokens": msg.output_tokens,
                "cost": float(msg.cost) if msg.cost else None,
                "latency_ms": msg.latency_ms,
                "sequence": msg.sequence,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
            for msg in messages
        ],
    }


@router.get("/projects/{project_id}/breadcrumbs/edges/{source_agent_id}/{target_agent_id}/messages")
async def get_breadcrumb_edge_messages(
    project_id: UUID,
    source_agent_id: UUID,
    target_agent_id: UUID,
    date_from: Optional[str] = Query(None, description="ISO 8601 start date filter"),
    date_to: Optional[str] = Query(None, description="ISO 8601 end date filter"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Messages exchanged between two agents along an edge.

    Returns delegation messages (invoke_agent / delegate_task) from
    the source agent's sessions that target the specified target agent.
    Also returns the corresponding tool-result messages.
    """
    import json as _json

    dt_from = _parse_iso_date(date_from)
    dt_to = _parse_iso_date(date_to, end_of_day=True)

    # Verify project access
    stmt = select(Project).where(
        and_(Project.id == project_id, Project.org_id == current_user.org_id)
    )
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Verify both agents belong to this project
    for aid in (source_agent_id, target_agent_id):
        stmt = select(Agent).where(
            and_(Agent.id == aid, Agent.project_id == project_id, Agent.org_id == current_user.org_id)
        )
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found in this project")

    # Fetch ALL candidate messages from the source agent's sessions that
    # could be delegation messages (assistant with tool_calls, or tool with
    # tool_name set).  We filter in Python because the target agent ID is
    # buried inside a JSON column.
    candidate_stmt = (
        select(AgentMessage)
        .join(AgentSession, AgentMessage.session_id == AgentSession.id)
        .where(
            and_(
                AgentSession.agent_id == source_agent_id,
                or_(
                    and_(AgentMessage.role == "assistant", AgentMessage.tool_calls.isnot(None)),
                    and_(
                        AgentMessage.role == "tool",
                        AgentMessage.tool_name.in_(["invoke_agent", "delegate_task"]),
                        AgentMessage.tool_calls.isnot(None),
                    ),
                ),
            )
        )
        .order_by(desc(AgentMessage.created_at))
    )
    if dt_from:
        candidate_stmt = candidate_stmt.where(AgentMessage.created_at >= dt_from)
    if dt_to:
        candidate_stmt = candidate_stmt.where(AgentMessage.created_at <= dt_to)

    result = await db.execute(candidate_stmt)
    candidates = result.scalars().all()

    # Filter in Python: keep only messages that reference the target agent
    matching = []
    target_str = str(target_agent_id)
    for msg in candidates:
        extracted = _extract_target_agent_id(msg.tool_calls)
        if extracted and str(extracted) == target_str:
            matching.append(msg)

    total = len(matching)
    page = matching[offset : offset + limit]

    # Look up source/target agent names
    src_stmt = select(Agent.name).where(Agent.id == source_agent_id)
    tgt_stmt = select(Agent.name).where(Agent.id == target_agent_id)
    src_name = (await db.execute(src_stmt)).scalar() or "Unknown"
    tgt_name = (await db.execute(tgt_stmt)).scalar() or "Unknown"

    return {
        "source_agent_id": str(source_agent_id),
        "source_agent_name": src_name,
        "target_agent_id": str(target_agent_id),
        "target_agent_name": tgt_name,
        "project_id": str(project_id),
        "date_from": date_from,
        "date_to": date_to,
        "total": total,
        "limit": limit,
        "offset": offset,
        "messages": [
            {
                "id": str(msg.id),
                "session_id": str(msg.session_id),
                "role": msg.role,
                "content": msg.content,
                "tool_name": msg.tool_name,
                "tool_calls": msg.tool_calls,
                "tool_call_id": msg.tool_call_id,
                "model_used": msg.model_used,
                "input_tokens": msg.input_tokens,
                "output_tokens": msg.output_tokens,
                "cost": float(msg.cost) if msg.cost else None,
                "latency_ms": msg.latency_ms,
                "sequence": msg.sequence,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
            for msg in page
        ],
    }


# ─── Scaling / HPA Endpoints ───


@router.get("/agents/{agent_id}/scaling")
async def get_scaling_status(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current autoscaling status for an agent."""
    from app.services.agent_autoscaler import get_scaling_status as _get_scaling_status

    redis = await get_redis()

    stmt = select(Agent).where(
        and_(Agent.id == agent_id, Agent.org_id == current_user.org_id)
    )
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return await _get_scaling_status(agent, redis)


@router.get("/agents/{agent_id}/scaling/events")
async def list_scaling_events(
    agent_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List scaling events for an agent."""
    from app.models.agent_scaling_event import AgentScalingEvent

    # Verify agent access
    stmt = select(Agent).where(
        and_(Agent.id == agent_id, Agent.org_id == current_user.org_id)
    )
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Count
    count_stmt = select(func.count()).select_from(AgentScalingEvent).where(
        AgentScalingEvent.agent_id == agent_id
    )
    total = (await db.execute(count_stmt)).scalar()

    # Fetch
    events_stmt = (
        select(AgentScalingEvent)
        .where(AgentScalingEvent.agent_id == agent_id)
        .order_by(desc(AgentScalingEvent.created_at))
        .offset(offset)
        .limit(limit)
    )
    events = (await db.execute(events_stmt)).scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "events": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "previous_capacity": e.previous_capacity,
                "new_capacity": e.new_capacity,
                "replica_count": e.replica_count,
                "trigger_utilization": float(e.trigger_utilization),
                "details": e.details,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
    }


@router.post("/agents/{agent_id}/scaling/configure")
async def configure_scaling(
    agent_id: UUID,
    config: Dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Configure autoscaling for an agent. Enterprise+ only."""
    from app.services.feature_gate import feature_gate

    # Feature gate check
    await feature_gate.require_feature(db, str(current_user.org_id), "agent_hpa")

    stmt = select(Agent).where(
        and_(Agent.id == agent_id, Agent.org_id == current_user.org_id)
    )
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Validate config values
    threshold = config.get("capacity_threshold", 0.6)
    scale_down = config.get("scale_down_threshold", 0.3)
    max_replicas = config.get("max_replicas", 5)

    if not (0.1 <= threshold <= 0.95):
        raise HTTPException(status_code=422, detail="capacity_threshold must be between 0.1 and 0.95")
    if not (0.05 <= scale_down < threshold):
        raise HTTPException(status_code=422, detail="scale_down_threshold must be between 0.05 and less than capacity_threshold")
    if not (1 <= max_replicas <= 10):
        raise HTTPException(status_code=422, detail="max_replicas must be between 1 and 10")

    enabled = config.get("enabled", True)
    agent.autoscale_enabled = enabled
    agent.autoscale_config = {
        "capacity_threshold": threshold,
        "scale_down_threshold": scale_down,
        "scale_down_cooldown_seconds": config.get("scale_down_cooldown_seconds", 300),
        "max_replicas": max_replicas,
        "mode": config.get("mode", "virtual"),
    }
    await db.flush()

    return {
        "agent_id": str(agent.id),
        "autoscale_enabled": agent.autoscale_enabled,
        "autoscale_config": agent.autoscale_config,
    }


@router.post("/agents/{agent_id}/scaling/manual")
async def manual_scale(
    agent_id: UUID,
    action: Dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually scale an agent up or down. Enterprise+ only."""
    from app.services.feature_gate import feature_gate
    from app.services.agent_autoscaler import get_effective_rpm, _log_scaling_event

    await feature_gate.require_feature(db, str(current_user.org_id), "agent_hpa")

    redis = await get_redis()

    stmt = select(Agent).where(
        and_(Agent.id == agent_id, Agent.org_id == current_user.org_id)
    )
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    direction = action.get("direction", "up")
    current_rpm = await get_effective_rpm(agent, redis)

    if direction == "up":
        max_rpm = (agent.autoscale_config or {}).get("max_replicas", 5) * agent.rate_limit_rpm
        new_rpm = min(current_rpm * 2, max_rpm)
    elif direction == "down":
        new_rpm = max(agent.rate_limit_rpm, current_rpm // 2)
    else:
        raise HTTPException(status_code=422, detail="direction must be 'up' or 'down'")

    import time
    rpm_key = f"agent_hpa:rpm:{agent.id}"
    if new_rpm <= agent.rate_limit_rpm:
        await redis.delete(rpm_key)
        new_rpm = agent.rate_limit_rpm
    else:
        await redis.set(rpm_key, str(new_rpm), ex=300)

    await _log_scaling_event(
        agent_id=agent.id,
        org_id=agent.org_id,
        event_type=f"manual_scale_{direction}",
        previous_capacity=current_rpm,
        new_capacity=new_rpm,
        utilization=0.0,
    )

    return {
        "agent_id": str(agent.id),
        "previous_rpm": current_rpm,
        "new_rpm": new_rpm,
        "direction": direction,
    }