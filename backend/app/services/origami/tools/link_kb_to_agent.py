"""link_kb_to_agent — give an existing agent access to a KB.

Appends a kb_id to the agent's knowledge_base_ids list. Both must belong
to the user's org (the org check is enforced server-side; the model can't
inject org_id).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.user import User
from app.services.origami.tools.base import OrigamiTool, register_tool


@register_tool
class LinkKbToAgentTool(OrigamiTool):
    name = "link_kb_to_agent"
    description = (
        "Attach an existing knowledge base to an existing agent so the agent "
        "can reference its content during inference (RAG). Both the KB and "
        "the agent must already exist in the user's organization. If the KB "
        "is already linked, this is a no-op."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "string",
                "description": "UUID of the agent to attach the KB to",
            },
            "kb_id": {
                "type": "string",
                "description": "UUID of the knowledge base to attach",
            },
        },
        "required": ["agent_id", "kb_id"],
        "additionalProperties": False,
    }
    is_write = True

    async def execute(
        self,
        *,
        org_id: uuid.UUID,
        user: User,
        params: dict[str, Any],
        db: AsyncSession,
    ) -> dict[str, Any]:
        from app.models.agent import Agent
        from app.models.knowledge_base import KnowledgeBase

        try:
            agent_id = uuid.UUID(str(params.get("agent_id")))
            kb_id = uuid.UUID(str(params.get("kb_id")))
        except (TypeError, ValueError):
            return {
                "success": False,
                "error": "invalid_uuid",
                "message": "Both agent_id and kb_id must be valid UUIDs.",
            }

        # Fetch agent, scoped to the user's org (no cross-tenant link)
        agent_row = await db.execute(
            select(Agent).where(Agent.id == agent_id, Agent.org_id == org_id)
        )
        agent = agent_row.scalar_one_or_none()
        if not agent:
            return {
                "success": False,
                "error": "agent_not_found",
                "message": "Agent not found in your organization.",
            }

        # Same check for the KB
        kb_row = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id, KnowledgeBase.org_id == org_id
            )
        )
        kb = kb_row.scalar_one_or_none()
        if not kb:
            return {
                "success": False,
                "error": "kb_not_found",
                "message": "Knowledge base not found in your organization.",
            }

        existing = list(agent.knowledge_base_ids or [])
        kb_id_str = str(kb_id)
        if kb_id_str in existing:
            return {
                "success": True,
                "already_linked": True,
                "agent_id": str(agent.id),
                "kb_id": kb_id_str,
                "knowledge_base_ids": existing,
            }

        existing.append(kb_id_str)
        agent.knowledge_base_ids = existing
        # JSON column — tell SQLAlchemy the list contents changed
        flag_modified(agent, "knowledge_base_ids")
        await db.flush()
        await db.commit()

        return {
            "success": True,
            "agent_id": str(agent.id),
            "agent_name": agent.name,
            "kb_id": kb_id_str,
            "kb_name": kb.name,
            "knowledge_base_ids": existing,
            "next_step": "The agent will now retrieve from this KB on every inference call.",
        }
