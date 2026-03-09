"""
Agent Memory Service

Handles persistent memory storage and retrieval for agents using vector search.
Integrates with existing pgvector infrastructure from AI Context.
"""

import asyncio
import json
import uuid
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.models.agent import Agent
from app.models.agent import Agent
from app.models.agent_memory import AgentMemory
from app.models.agent_session import AgentSession
from app.models.agent_message import AgentMessage
from app.services.kb_ingestion import EmbeddingGenerator  # Reuse existing embedding service

logger = logging.getLogger(__name__)


class AgentMemoryService:
    """Service for managing agent memories with vector search capabilities."""
    
    def __init__(self):
        self.embedding_dimension = 768  # OpenAI embedding dimension
        
    async def store_memory(
        self,
        agent_id: uuid.UUID,
        memory_type: str,
        content: str,
        db: AsyncSession,
        importance_score: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
        source_session_id: Optional[uuid.UUID] = None,
        source_message_id: Optional[uuid.UUID] = None
    ) -> AgentMemory:
        """Store a new memory for an agent with vector embedding."""
        
        # Get agent to validate it exists and get project/org info
        stmt = select(Agent).where(Agent.id == agent_id)
        result = await db.execute(stmt)
        agent = result.scalar_one_or_none()
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Generate embedding for the content
        try:
            embedding_gen = EmbeddingGenerator(agent.org_id)
            embeddings = await embedding_gen.generate_embeddings([content])
            embedding = embeddings[0] if embeddings else None
        except Exception as e:
            logger.warning(f"Failed to generate embedding for memory: {e}")
            embedding = None
        
        # Create memory record (without embedding - set via raw SQL to avoid asyncpg vector type issues)
        memory = AgentMemory(
            agent_id=agent_id,
            project_id=agent.project_id,
            org_id=agent.org_id,
            memory_type=memory_type,
            content=content,
            extra_data=metadata or {},
            importance_score=importance_score,
            source_session_id=source_session_id,
            source_message_id=source_message_id
        )
        
        db.add(memory)
        await db.commit()
        await db.refresh(memory)
        
        # Set embedding via raw SQL to work around asyncpg/pgvector type mapping
        if embedding:
            try:
                embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                await db.execute(
                    text("UPDATE agent_memories SET embedding = :emb::vector WHERE id = :id"),
                    {"emb": embedding_str, "id": str(memory.id)}
                )
                await db.commit()
            except Exception as e:
                logger.warning(f"Failed to store embedding for memory {memory.id}: {e}")
        
        logger.info(f"Stored memory {memory.id} for agent {agent_id} (type: {memory_type})")
        return memory
    
    async def search_memories(
        self,
        agent_id: uuid.UUID,
        query: str,
        db: AsyncSession,
        limit: int = 10,
        memory_types: Optional[List[str]] = None,
        min_importance: Optional[float] = None
    ) -> List[AgentMemory]:
        """Search agent memories using vector similarity and filters."""
        
        try:
            # Generate embedding for the query
            # Get agent to get org_id for embedding generation
            agent_stmt = select(Agent).where(Agent.id == agent_id)
            agent_result = await db.execute(agent_stmt)
            agent = agent_result.scalar_one_or_none()
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")
                
            embedding_gen = EmbeddingGenerator(agent.org_id)
            embeddings = await embedding_gen.generate_embeddings([query])
            query_embedding = embeddings[0] if embeddings else None
            
            if not query_embedding:
                raise ValueError("Failed to generate query embedding")
        except Exception as e:
            logger.warning(f"Failed to generate embedding for search query: {e}")
            # Fall back to text search if embedding fails
            return await self._text_search_memories(
                agent_id, query, db, limit, memory_types, min_importance
            )
        
        # Use raw SQL for vector similarity search (same pattern as KB chunks)
        query_vec_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
        
        type_filter = ""
        params = {"agent_id": str(agent_id), "query_vec": query_vec_str, "limit": limit}
        
        if memory_types:
            type_filter += " AND m.memory_type = ANY(:types)"
            params["types"] = memory_types
        
        if min_importance is not None:
            type_filter += " AND m.importance_score >= :min_importance"
            params["min_importance"] = min_importance
        
        sql = text(f"""
            SELECT m.id, m.agent_id, m.project_id, m.org_id, m.memory_type, m.content,
                   m.metadata AS extra_data, m.importance_score, m.access_count,
                   m.source_session_id, m.source_message_id, m.last_accessed_at,
                   m.created_at, m.updated_at,
                   1 - (m.embedding <=> CAST(:query_vec AS vector)) AS similarity_score
            FROM agent_memories m
            WHERE m.agent_id = :agent_id::uuid
              AND m.embedding IS NOT NULL
              {type_filter}
            ORDER BY m.embedding <=> CAST(:query_vec AS vector)
            LIMIT :limit
        """)
        
        result = await db.execute(sql, params)
        rows = result.fetchall()
        
        # Convert rows to AgentMemory objects
        memories = []
        memory_ids = []
        for row in rows:
            memory = AgentMemory(
                id=row.id, agent_id=row.agent_id, project_id=row.project_id,
                org_id=row.org_id, memory_type=row.memory_type, content=row.content,
                extra_data=row.extra_data, importance_score=row.importance_score,
                access_count=row.access_count, source_session_id=row.source_session_id,
                source_message_id=row.source_message_id, last_accessed_at=row.last_accessed_at,
                created_at=row.created_at, updated_at=row.updated_at
            )
            memories.append(memory)
            memory_ids.append(row.id)
        
        # Update access count for retrieved memories
        if memory_ids:
            await db.execute(
                text("UPDATE agent_memories SET access_count = access_count + 1, last_accessed_at = NOW() WHERE id = ANY(:ids)"),
                {"ids": memory_ids}
            )
            await db.commit()
        
        logger.info(f"Found {len(memories)} memories for agent {agent_id} with query: {query[:100]}")
        return memories
    
    async def _text_search_memories(
        self,
        agent_id: uuid.UUID,
        query: str,
        db: AsyncSession,
        limit: int = 10,
        memory_types: Optional[List[str]] = None,
        min_importance: Optional[float] = None
    ) -> List[AgentMemory]:
        """Fallback text-based search when vector search is not available."""
        
        conditions = [AgentMemory.agent_id == agent_id]
        
        if memory_types:
            conditions.append(AgentMemory.memory_type.in_(memory_types))
        
        if min_importance is not None:
            conditions.append(AgentMemory.importance_score >= min_importance)
        
        # Use PostgreSQL full-text search
        conditions.append(
            or_(
                AgentMemory.content.ilike(f"%{query}%"),
                func.to_tsvector('english', AgentMemory.content).match(query)
            )
        )
        
        stmt = (
            select(AgentMemory)
            .where(and_(*conditions))
            .order_by(desc(AgentMemory.importance_score), desc(AgentMemory.created_at))
            .limit(limit)
        )
        
        result = await db.execute(stmt)
        memories = result.scalars().all()
        
        # Update access count
        if memories:
            memory_ids = [m.id for m in memories]
            update_stmt = (
                text("UPDATE agent_memories SET access_count = access_count + 1, last_accessed_at = NOW() WHERE id = ANY(:ids)")
            )
            await db.execute(update_stmt, {"ids": memory_ids})
            await db.commit()
        
        return list(memories)
    
    async def get_agent_memories(
        self,
        agent_id: uuid.UUID,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        memory_type: Optional[str] = None,
        order_by: str = "created_at"
    ) -> List[AgentMemory]:
        """Get agent memories with pagination and filtering."""
        
        conditions = [AgentMemory.agent_id == agent_id]
        
        if memory_type:
            conditions.append(AgentMemory.memory_type == memory_type)
        
        # Order by options
        if order_by == "importance":
            order_clause = desc(AgentMemory.importance_score)
        elif order_by == "accessed":
            order_clause = desc(AgentMemory.last_accessed_at)
        elif order_by == "updated":
            order_clause = desc(AgentMemory.updated_at)
        else:  # default to created_at
            order_clause = desc(AgentMemory.created_at)
        
        stmt = (
            select(AgentMemory)
            .where(and_(*conditions))
            .order_by(order_clause)
            .limit(limit)
            .offset(offset)
        )
        
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    async def update_memory(
        self,
        memory_id: uuid.UUID,
        agent_id: uuid.UUID,
        db: AsyncSession,
        content: Optional[str] = None,
        importance_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentMemory:
        """Update an existing memory."""
        
        stmt = select(AgentMemory).where(
            and_(
                AgentMemory.id == memory_id,
                AgentMemory.agent_id == agent_id
            )
        )
        result = await db.execute(stmt)
        memory = result.scalar_one_or_none()
        
        if not memory:
            raise ValueError(f"Memory {memory_id} not found for agent {agent_id}")
        
        # Update fields
        if content is not None:
            memory.content = content
            # Regenerate embedding if content changed
            try:
                agent_stmt = select(Agent).where(Agent.id == agent_id)
                agent_result = await db.execute(agent_stmt)
                agent = agent_result.scalar_one_or_none()
                if agent:
                    embedding_gen = EmbeddingGenerator(agent.org_id)
                    embeddings = await embedding_gen.generate_embeddings([content])
                    if embeddings and embeddings[0]:
                        embedding_str = "[" + ",".join(str(x) for x in embeddings[0]) + "]"
                        await db.execute(
                            text("UPDATE agent_memories SET embedding = :emb::vector WHERE id = :id"),
                            {"emb": embedding_str, "id": str(memory_id)}
                        )
            except Exception as e:
                logger.warning(f"Failed to update embedding: {e}")
        
        if importance_score is not None:
            memory.importance_score = importance_score
        
        if metadata is not None:
            memory.extra_data = metadata
        
        await db.commit()
        await db.refresh(memory)
        
        logger.info(f"Updated memory {memory_id} for agent {agent_id}")
        return memory
    
    async def delete_memory(
        self,
        memory_id: uuid.UUID,
        agent_id: uuid.UUID,
        db: AsyncSession
    ) -> bool:
        """Delete a memory."""
        
        stmt = select(AgentMemory).where(
            and_(
                AgentMemory.id == memory_id,
                AgentMemory.agent_id == agent_id
            )
        )
        result = await db.execute(stmt)
        memory = result.scalar_one_or_none()
        
        if not memory:
            return False
        
        await db.delete(memory)
        await db.commit()
        
        logger.info(f"Deleted memory {memory_id} for agent {agent_id}")
        return True
    
    async def extract_memories_from_conversation(
        self,
        session: AgentSession,
        db: AsyncSession,
        max_memories: int = 5
    ) -> List[AgentMemory]:
        """Extract important memories from a conversation session using AI analysis."""
        
        # Get the conversation messages
        stmt = (
            select(AgentMessage)
            .where(AgentMessage.session_id == session.id)
            .order_by(AgentMessage.sequence)
        )
        result = await db.execute(stmt)
        messages = result.scalars().all()
        
        if not messages:
            return []
        
        # Build conversation text
        conversation = []
        for msg in messages:
            if msg.role in ["user", "assistant"] and msg.content:
                role = "Human" if msg.role == "user" else "Assistant"
                conversation.append(f"{role}: {msg.content}")
        
        if not conversation:
            return []
        
        conversation_text = "\n".join(conversation)
        
        # Use AI to extract key facts and insights
        try:
            from app.services.gateway import chat_completion as gateway_chat_completion
            
            extraction_prompt = f"""
            Analyze this conversation and extract key memories that the agent should remember for future interactions.
            Focus on:
            - Important facts about the user or their preferences
            - Key insights or patterns discovered
            - Significant decisions or outcomes
            - Context that would be valuable in future conversations
            
            Return a JSON array of up to {max_memories} memories, each with:
            - "type": one of "fact", "pattern", "interaction", "preference", "context"
            - "content": clear, concise description of what to remember
            - "importance": score from 1-10 indicating how important this memory is
            
            Conversation:
            {conversation_text}
            
            Return only the JSON array, no other text.
            """
            
            response = await gateway_chat_completion(
                messages=[{"role": "user", "content": extraction_prompt}],
                model="gpt-4-turbo-preview",
                org_id=session.org_id,
                max_tokens=1000,
                temperature=0.1
            )
            
            if not response.get("choices"):
                return []
            
            content = response["choices"][0]["message"]["content"]
            
            # Parse the JSON response
            try:
                memories_data = json.loads(content.strip())
                if not isinstance(memories_data, list):
                    return []
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse memory extraction response: {content}")
                return []
            
            # Create memory objects
            created_memories = []
            for memory_data in memories_data:
                if not isinstance(memory_data, dict):
                    continue
                
                try:
                    memory = await self.store_memory(
                        agent_id=session.agent_id,
                        memory_type=memory_data.get("type", "context"),
                        content=memory_data["content"],
                        importance_score=float(memory_data.get("importance", 1.0)),
                        source_session_id=session.id,
                        db=db
                    )
                    created_memories.append(memory)
                except (KeyError, ValueError) as e:
                    logger.warning(f"Invalid memory data: {memory_data}, error: {e}")
                    continue
            
            logger.info(f"Extracted {len(created_memories)} memories from session {session.id}")
            return created_memories
            
        except Exception as e:
            logger.error(f"Failed to extract memories from conversation: {e}")
            return []
    
    async def get_memory_statistics(
        self,
        agent_id: uuid.UUID,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Get statistics about an agent's memory."""
        
        # Total count and memory types
        stmt = (
            select(
                func.count(AgentMemory.id).label("total_count"),
                func.count(AgentMemory.memory_type).filter(AgentMemory.memory_type == "fact").label("fact_count"),
                func.count(AgentMemory.memory_type).filter(AgentMemory.memory_type == "pattern").label("pattern_count"),
                func.count(AgentMemory.memory_type).filter(AgentMemory.memory_type == "interaction").label("interaction_count"),
                func.count(AgentMemory.memory_type).filter(AgentMemory.memory_type == "preference").label("preference_count"),
                func.count(AgentMemory.memory_type).filter(AgentMemory.memory_type == "context").label("context_count"),
                func.avg(AgentMemory.importance_score).label("avg_importance"),
                func.sum(AgentMemory.access_count).label("total_access_count")
            )
            .where(AgentMemory.agent_id == agent_id)
        )
        result = await db.execute(stmt)
        stats = result.first()
        
        # Recent activity
        recent_stmt = (
            select(AgentMemory)
            .where(AgentMemory.agent_id == agent_id)
            .order_by(desc(AgentMemory.created_at))
            .limit(5)
        )
        recent_result = await db.execute(recent_stmt)
        recent_memories = recent_result.scalars().all()
        
        return {
            "total_memories": stats.total_count or 0,
            "by_type": {
                "fact": stats.fact_count or 0,
                "pattern": stats.pattern_count or 0,
                "interaction": stats.interaction_count or 0,
                "preference": stats.preference_count or 0,
                "context": stats.context_count or 0,
            },
            "average_importance": float(stats.avg_importance or 0),
            "total_access_count": stats.total_access_count or 0,
            "recent_memories": [
                {
                    "id": str(m.id),
                    "type": m.memory_type,
                    "content": m.content[:100] + "..." if len(m.content) > 100 else m.content,
                    "created_at": m.created_at.isoformat(),
                }
                for m in recent_memories
            ]
        }