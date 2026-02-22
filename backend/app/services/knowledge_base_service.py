"""
Knowledge Base Service

Handles knowledge base resolution and inheritance from groups
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.agent_group import AgentGroup


class KnowledgeBaseService:
    """Service for resolving knowledge base access for agents."""
    
    @staticmethod
    async def get_effective_knowledge_bases(db: AsyncSession, agent: Agent) -> List[UUID]:
        """
        Get effective knowledge bases for an agent.
        
        Resolution order:
        1. If agent has explicit knowledge_base_ids, use those
        2. If agent belongs to a group, inherit from group
        3. Otherwise, no knowledge bases
        """
        
        # If agent has explicit KBs, use those
        if agent.knowledge_base_ids:
            return [UUID(kb_id) for kb_id in agent.knowledge_base_ids]
        
        # If agent belongs to a group, inherit from group
        if agent.group_id:
            stmt = select(AgentGroup).where(AgentGroup.id == agent.group_id)
            result = await db.execute(stmt)
            group = result.scalar_one_or_none()
            
            if group and group.knowledge_base_ids:
                return [UUID(kb_id) for kb_id in group.knowledge_base_ids]
        
        # No knowledge bases available
        return []
    
    @staticmethod
    async def get_group_knowledge_bases(db: AsyncSession, group_id: UUID) -> List[UUID]:
        """Get knowledge bases for a specific group."""
        stmt = select(AgentGroup).where(AgentGroup.id == group_id)
        result = await db.execute(stmt)
        group = result.scalar_one_or_none()
        
        if group and group.knowledge_base_ids:
            return [UUID(kb_id) for kb_id in group.knowledge_base_ids]
        
        return []
    
    @staticmethod
    async def update_agent_knowledge_bases(
        db: AsyncSession, 
        agent: Agent, 
        knowledge_base_ids: Optional[List[UUID]]
    ) -> None:
        """
        Update agent's knowledge base IDs.
        
        If knowledge_base_ids is None or empty, agent will inherit from group.
        If knowledge_base_ids is provided, agent will use explicit overrides.
        """
        if knowledge_base_ids:
            agent.knowledge_base_ids = [str(kb_id) for kb_id in knowledge_base_ids]
        else:
            agent.knowledge_base_ids = []  # Will inherit from group
        
        await db.commit()
        await db.refresh(agent)
    
    @staticmethod
    async def update_group_knowledge_bases(
        db: AsyncSession,
        group: AgentGroup,
        knowledge_base_ids: List[UUID]
    ) -> None:
        """Update group's knowledge base IDs."""
        group.knowledge_base_ids = [str(kb_id) for kb_id in knowledge_base_ids]
        await db.commit()
        await db.refresh(group)
    
    @staticmethod
    async def get_agents_using_knowledge_base(
        db: AsyncSession, 
        org_id: UUID, 
        knowledge_base_id: UUID
    ) -> List[Agent]:
        """
        Get all agents that use a specific knowledge base.
        This includes both direct assignment and group inheritance.
        """
        kb_id_str = str(knowledge_base_id)
        
        # Direct assignment
        stmt_direct = select(Agent).where(
            and_(
                Agent.org_id == org_id,
                Agent.knowledge_base_ids.op('?')([kb_id_str])  # JSON contains check
            )
        )
        result_direct = await db.execute(stmt_direct)
        direct_agents = result_direct.scalars().all()
        
        # Group inheritance
        stmt_groups = select(AgentGroup).where(
            and_(
                AgentGroup.org_id == org_id,
                AgentGroup.knowledge_base_ids.op('?')([kb_id_str])
            )
        )
        result_groups = await db.execute(stmt_groups)
        groups = result_groups.scalars().all()
        
        inherited_agents = []
        for group in groups:
            stmt_group_agents = select(Agent).where(
                and_(
                    Agent.group_id == group.id,
                    Agent.knowledge_base_ids == []  # Only agents that inherit (no overrides)
                )
            )
            result_group_agents = await db.execute(stmt_group_agents)
            inherited_agents.extend(result_group_agents.scalars().all())
        
        # Combine and deduplicate
        all_agents = direct_agents + inherited_agents
        seen = set()
        unique_agents = []
        for agent in all_agents:
            if agent.id not in seen:
                seen.add(agent.id)
                unique_agents.append(agent)
        
        return unique_agents
    
    @staticmethod
    async def validate_knowledge_base_access(
        db: AsyncSession,
        user_org_id: UUID,
        knowledge_base_ids: List[UUID]
    ) -> bool:
        """
        Validate that all knowledge bases belong to the user's organization.
        Returns True if all are valid, False otherwise.
        """
        from app.models.knowledge_base import KnowledgeBase
        
        if not knowledge_base_ids:
            return True
        
        stmt = select(KnowledgeBase.id).where(
            and_(
                KnowledgeBase.id.in_(knowledge_base_ids),
                KnowledgeBase.org_id == user_org_id
            )
        )
        result = await db.execute(stmt)
        valid_ids = {row[0] for row in result.all()}
        
        return len(valid_ids) == len(knowledge_base_ids)
    
    @staticmethod  
    def get_knowledge_base_summary(agent: Agent, group: Optional[AgentGroup] = None) -> dict:
        """
        Get a summary of knowledge base configuration for an agent.
        Returns dict with source and IDs.
        """
        if agent.knowledge_base_ids:
            return {
                "source": "agent_override",
                "knowledge_base_ids": [UUID(kb_id) for kb_id in agent.knowledge_base_ids],
                "inherited_from": None
            }
        elif agent.group_id and group and group.knowledge_base_ids:
            return {
                "source": "group_inherited", 
                "knowledge_base_ids": [UUID(kb_id) for kb_id in group.knowledge_base_ids],
                "inherited_from": str(agent.group_id)
            }
        else:
            return {
                "source": "none",
                "knowledge_base_ids": [],
                "inherited_from": None
            }