"""update_agent — modify an existing Bonobot agent in place.

All fields besides agent_id are optional; only provided fields are changed.
Common uses: tweak the system prompt, swap models, change temperature,
re-attach knowledge bases, expand tool policy.

Plan-card-gated. The user sees what changed before clicking Deploy.
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
class UpdateAgentTool(OrigamiTool):
    name = "update_agent"
    description = (
        "Modify an existing Bonobot agent. agent_id is required. Every other "
        "field is optional — only fields you pass in are changed. Use this when "
        "the user wants to tweak an agent's persona, switch models, attach more "
        "KBs, change rate limits, or adjust tool policy without recreating from "
        "scratch."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "agent_id": {"type": "string", "description": "UUID of the agent to modify"},
            "name": {"type": "string", "minLength": 1, "maxLength": 255},
            "description": {"type": "string", "maxLength": 2000},
            "system_prompt": {
                "type": "string",
                "minLength": 10,
                "maxLength": 8000,
                "description": "Replacement system prompt; pass to refine the agent's persona",
            },
            "model_id": {"type": "string"},
            "knowledge_base_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Replaces the existing KB list. Pass an empty array to clear.",
            },
            "temperature": {"type": "number", "minimum": 0, "maximum": 2},
            "max_tokens": {"type": "integer", "minimum": 64, "maximum": 8192},
            "rate_limit_rpm": {"type": "integer", "minimum": 1, "maximum": 10000},
        },
        "required": ["agent_id"],
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

        try:
            agent_id = uuid.UUID(str(params.get("agent_id")))
        except (TypeError, ValueError):
            return {"success": False, "error": "invalid_agent_id",
                    "message": "agent_id must be a valid UUID."}

        row = await db.execute(
            select(Agent).where(Agent.id == agent_id, Agent.org_id == org_id)
        )
        agent = row.scalar_one_or_none()
        if not agent:
            return {"success": False, "error": "agent_not_found",
                    "message": "Agent not found in your organization."}

        changes: list[str] = []

        def maybe_set(field: str, key: str | None = None) -> bool:
            key = key or field
            if key in params and params[key] is not None:
                setattr(agent, field, params[key])
                changes.append(field)
                return True
            return False

        maybe_set("name")
        maybe_set("description")
        maybe_set("system_prompt")
        maybe_set("model_id")
        maybe_set("rate_limit_rpm")

        if "knowledge_base_ids" in params and isinstance(params["knowledge_base_ids"], list):
            cleaned: list[str] = []
            for k in params["knowledge_base_ids"]:
                try:
                    uuid.UUID(str(k))
                    cleaned.append(str(k))
                except ValueError:
                    continue
            agent.knowledge_base_ids = cleaned
            flag_modified(agent, "knowledge_base_ids")
            changes.append("knowledge_base_ids")

        # temperature + max_tokens live inside model_config JSON dict
        mc = dict(agent.model_config or {})
        if "temperature" in params:
            mc["temperature"] = float(params["temperature"])
            changes.append("temperature")
        if "max_tokens" in params:
            mc["max_tokens"] = int(params["max_tokens"])
            changes.append("max_tokens")
        if changes and ("temperature" in changes or "max_tokens" in changes):
            agent.model_config = mc
            flag_modified(agent, "model_config")

        if not changes:
            return {"success": False, "error": "no_changes",
                    "message": "No fields to update were supplied."}

        await db.flush()
        await db.commit()

        return {
            "success": True,
            "agent_id": str(agent.id),
            "name": agent.name,
            "model_id": agent.model_id,
            "changed_fields": changes,
            "knowledge_base_ids": list(agent.knowledge_base_ids or []),
            "next_step": "Agent will pick up these changes on its next invocation.",
        }
