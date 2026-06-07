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
                "description": "UUID of the agent. If you only know the agent's name, pass `agent_name` instead.",
            },
            "agent_name": {
                "type": "string",
                "description": "Display name of the agent — resolved to a UUID server-side.",
            },
            "kb_id": {
                "type": "string",
                "description": "UUID of the knowledge base. If you only know the KB's name, pass `kb_name` instead.",
            },
            "kb_name": {
                "type": "string",
                "description": "Display name of the KB — resolved to a UUID server-side.",
            },
        },
        "required": [],
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

        agent = None
        kb = None

        agent_id_raw = params.get("agent_id")
        agent_name = (params.get("agent_name") or "").strip()
        # If both are passed and they disagree, refuse — the LLM is confused
        # and silently preferring one would link the wrong resource.
        if agent_id_raw and agent_name:
            check = await db.execute(
                select(Agent).where(Agent.org_id == org_id, Agent.name == agent_name)
            )
            named = check.scalar_one_or_none()
            if named and str(named.id) != str(agent_id_raw):
                return {
                    "success": False,
                    "error": "agent_id_name_mismatch",
                    "message": (
                        f"agent_id '{agent_id_raw}' and agent_name "
                        f"'{agent_name}' refer to different agents. Pass "
                        f"only one, or make them agree."
                    ),
                }
        if agent_id_raw:
            try:
                agent_id = uuid.UUID(str(agent_id_raw))
            except (TypeError, ValueError):
                return {"success": False, "error": "invalid_agent_id",
                        "message": "agent_id must be a valid UUID."}
            agent_row = await db.execute(
                select(Agent).where(Agent.id == agent_id, Agent.org_id == org_id)
            )
            agent = agent_row.scalar_one_or_none()
        elif agent_name:
            agent_row = await db.execute(
                select(Agent).where(Agent.name == agent_name, Agent.org_id == org_id)
            )
            agent = agent_row.scalar_one_or_none()
        else:
            return {"success": False, "error": "missing_agent_reference",
                    "message": "Provide either agent_id (UUID) or agent_name."}

        if not agent:
            ref = agent_id_raw or agent_name
            return {"success": False, "error": "agent_not_found",
                    "message": f"Agent '{ref}' not found in your organization."}

        kb_id_raw = params.get("kb_id")
        kb_name = (params.get("kb_name") or "").strip()
        if kb_id_raw and kb_name:
            from app.models.knowledge_base import KnowledgeBase
            check_kb = await db.execute(
                select(KnowledgeBase).where(
                    KnowledgeBase.org_id == org_id,
                    KnowledgeBase.name == kb_name,
                )
            )
            named_kb = check_kb.scalar_one_or_none()
            if named_kb and str(named_kb.id) != str(kb_id_raw):
                return {
                    "success": False,
                    "error": "kb_id_name_mismatch",
                    "message": (
                        f"kb_id '{kb_id_raw}' and kb_name '{kb_name}' refer "
                        f"to different KBs. Pass only one, or make them agree."
                    ),
                }
        if kb_id_raw:
            try:
                kb_id = uuid.UUID(str(kb_id_raw))
            except (TypeError, ValueError):
                return {"success": False, "error": "invalid_kb_id",
                        "message": "kb_id must be a valid UUID."}
            kb_row = await db.execute(
                select(KnowledgeBase).where(
                    KnowledgeBase.id == kb_id, KnowledgeBase.org_id == org_id
                )
            )
            kb = kb_row.scalar_one_or_none()
        elif kb_name:
            kb_row = await db.execute(
                select(KnowledgeBase).where(
                    KnowledgeBase.name == kb_name, KnowledgeBase.org_id == org_id
                )
            )
            kb = kb_row.scalar_one_or_none()
        else:
            return {"success": False, "error": "missing_kb_reference",
                    "message": "Provide either kb_id (UUID) or kb_name."}

        if not kb:
            ref = kb_id_raw or kb_name
            return {"success": False, "error": "kb_not_found",
                    "message": f"Knowledge base '{ref}' not found in your organization."}

        kb_id_str = str(kb.id)

        existing = list(agent.knowledge_base_ids or [])
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
