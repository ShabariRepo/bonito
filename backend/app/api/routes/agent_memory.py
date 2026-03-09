"""
Agent Memory API Routes

Routes for managing agent memories and search functionality.
"""

from typing import List, Optional
from uuid import UUID
import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.agent import Agent
from app.schemas.bonobot import (
    AgentMemoryCreate,
    AgentMemoryUpdate,
    AgentMemoryResponse,
    AgentMemorySearchRequest,
    AgentMemorySearchResponse,
)
from app.services.agent_memory_service import AgentMemoryService

router = APIRouter()
memory_service = AgentMemoryService()


@router.post("/agents/{agent_id}/memories", response_model=AgentMemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_memory(
    agent_id: UUID,
    memory_data: AgentMemoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new memory for an agent."""
    
    # Verify agent exists and user has access
    from sqlalchemy import select, and_
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
    
    try:
        memory = await memory_service.store_memory(
            agent_id=agent_id,
            memory_type=memory_data.memory_type,
            content=memory_data.content,
            importance_score=memory_data.importance_score,
            metadata=memory_data.metadata or {},
            db=db
        )
        
        return AgentMemoryResponse.model_validate(memory)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create memory: {str(e)}"
        )


@router.get("/agents/{agent_id}/memories", response_model=List[AgentMemoryResponse])
async def list_agent_memories(
    agent_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    memory_type: Optional[str] = Query(None),
    order_by: str = Query("created_at", regex="^(created_at|importance|accessed|updated)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List agent memories with pagination and filtering."""
    
    # Verify agent access
    from sqlalchemy import select, and_
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
    
    memories = await memory_service.get_agent_memories(
        agent_id=agent_id,
        limit=limit,
        offset=offset,
        memory_type=memory_type,
        order_by=order_by,
        db=db
    )
    
    return [AgentMemoryResponse.model_validate(memory) for memory in memories]


@router.post("/agents/{agent_id}/memories/search", response_model=AgentMemorySearchResponse)
async def search_agent_memories(
    agent_id: UUID,
    search_request: AgentMemorySearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Search agent memories using vector similarity."""
    
    # Verify agent access
    from sqlalchemy import select, and_
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
    
    try:
        memories = await memory_service.search_memories(
            agent_id=agent_id,
            query=search_request.query,
            limit=search_request.limit,
            memory_types=search_request.memory_types,
            min_importance=search_request.min_importance,
            db=db
        )
        
        return AgentMemorySearchResponse(
            memories=[AgentMemoryResponse.model_validate(memory) for memory in memories],
            query=search_request.query,
            total_found=len(memories)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Memory search failed: {str(e)}"
        )


@router.put("/agents/{agent_id}/memories/{memory_id}", response_model=AgentMemoryResponse)
async def update_agent_memory(
    agent_id: UUID,
    memory_id: UUID,
    memory_data: AgentMemoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing agent memory."""
    
    # Verify agent access
    from sqlalchemy import select, and_
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
    
    try:
        update_data = memory_data.model_dump(exclude_unset=True)
        memory = await memory_service.update_memory(
            memory_id=memory_id,
            agent_id=agent_id,
            db=db,
            **update_data
        )
        
        return AgentMemoryResponse.model_validate(memory)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update memory: {str(e)}"
        )


@router.delete("/agents/{agent_id}/memories/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent_memory(
    agent_id: UUID,
    memory_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an agent memory."""
    
    # Verify agent access
    from sqlalchemy import select, and_
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
    
    deleted = await memory_service.delete_memory(
        memory_id=memory_id,
        agent_id=agent_id,
        db=db
    )
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found"
        )


@router.get("/agents/{agent_id}/memories/stats")
async def get_agent_memory_stats(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get agent memory statistics."""
    
    # Verify agent access
    from sqlalchemy import select, and_
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
    
    stats = await memory_service.get_memory_statistics(
        agent_id=agent_id,
        db=db
    )
    
    return stats


@router.post("/agents/{agent_id}/sessions/{session_id}/extract-memories", response_model=List[AgentMemoryResponse])
async def extract_memories_from_session(
    agent_id: UUID,
    session_id: UUID,
    max_memories: int = Query(5, ge=1, le=10),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Extract important memories from a conversation session."""
    
    # Verify agent and session access
    from sqlalchemy import select, and_
    from app.models.agent_session import AgentSession
    
    stmt = select(AgentSession).where(
        and_(
            AgentSession.id == session_id,
            AgentSession.agent_id == agent_id,
            AgentSession.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    try:
        memories = await memory_service.extract_memories_from_conversation(
            session=session,
            max_memories=max_memories,
            db=db
        )
        
        return [AgentMemoryResponse.model_validate(memory) for memory in memories]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract memories: {str(e)}"
        )