"""create_agent — spin up a Bonobot agent.

Bonito's agent framework lets customers deploy persona-driven LLM
workers — support bots, lead qualifiers, KB-backed assistants, etc.
Origami's create_agent wires up a default-shaped agent that can be
iterated on via the canvas later.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.origami.tools.base import OrigamiTool, register_tool


@register_tool
class CreateAgentTool(OrigamiTool):
    name = "create_agent"
    description = (
        "Create a new Bonobot agent for the user's organization. Agents are "
        "Bonito's persona-driven LLM workers — pick a model, give it a system "
        "prompt and (optionally) knowledge bases, and the customer can hit it "
        "via the gateway. Requires an existing project_id (call create_project "
        "first if the user doesn't have one). Returns agent_id for downstream "
        "wiring (link_kb_to_agent, etc)."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "minLength": 1,
                "maxLength": 255,
                "description": "Display name, e.g. 'support-bot' or 'lead-qualifier'",
            },
            "system_prompt": {
                "type": "string",
                "minLength": 10,
                "maxLength": 8000,
                "description": (
                    "The agent's persona / instructions. Be specific — "
                    "this is what defines the agent's behavior."
                ),
            },
            "model_id": {
                "type": "string",
                "description": (
                    "Model to route to (e.g. 'claude-sonnet-4-5'). Defaults "
                    "to 'auto' which lets Bonito's routing pick."
                ),
            },
            "project_id": {
                "type": "string",
                "description": "UUID of the project this agent lives in. If absent, picks the user's first project.",
            },
            "description": {
                "type": "string",
                "maxLength": 2000,
                "description": "Optional human-readable summary",
            },
            "knowledge_base_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of KB UUIDs the agent should reference (RAG)",
            },
            "temperature": {
                "type": "number",
                "minimum": 0,
                "maximum": 2,
                "description": "Sampling temperature (default 0.7)",
            },
            "max_tokens": {
                "type": "integer",
                "minimum": 64,
                "maximum": 8192,
                "description": "Max output tokens per response (default 2048)",
            },
        },
        "required": ["name", "system_prompt"],
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
        from app.models.project import Project
        from app.services.feature_gate import feature_gate

        # Tier cap on number of agents
        try:
            sub = await feature_gate.get_organization_subscription(db, str(org_id))
            tier = (sub["tier"].value if hasattr(sub["tier"], "value") else str(sub["tier"])).lower()
        except Exception:
            tier = "free"

        agent_caps = {"free": 1, "builder": 10, "starter": 2, "growth": 50, "pro": 200}
        cap = agent_caps.get(tier)
        if cap is not None:
            existing = await db.execute(
                select(func.count(Agent.id)).where(Agent.org_id == org_id)
            )
            count = int(existing.scalar_one() or 0)
            if count >= cap:
                return {
                    "success": False,
                    "error": "agent_quota_exceeded",
                    "message": f"You're at {count}/{cap} agents on the {tier} tier.",
                    "tier": tier,
                }

        name = (params.get("name") or "").strip()
        sysprompt = (params.get("system_prompt") or "").strip()
        if not name or not sysprompt:
            return {
                "success": False,
                "error": "missing_required",
                "message": "Both name and system_prompt are required.",
            }

        # Resolve project_id: explicit param OR user's first project
        project_id_raw = params.get("project_id")
        project_id: Optional[uuid.UUID] = None
        if project_id_raw:
            try:
                project_id = uuid.UUID(str(project_id_raw))
            except ValueError:
                return {
                    "success": False,
                    "error": "invalid_project_id",
                    "message": f"project_id '{project_id_raw}' is not a valid UUID.",
                }
            # Confirm project belongs to the org
            owner_check = await db.execute(
                select(Project.id).where(
                    Project.id == project_id,
                    Project.org_id == org_id,
                )
            )
            if not owner_check.scalar_one_or_none():
                return {
                    "success": False,
                    "error": "project_not_found",
                    "message": "Project not found in your organization.",
                }
        else:
            first_project = await db.execute(
                select(Project.id).where(Project.org_id == org_id).limit(1)
            )
            project_id = first_project.scalar_one_or_none()
            if not project_id:
                return {
                    "success": False,
                    "error": "no_project",
                    "message": "No projects exist yet — call create_project before create_agent.",
                }

        # KB ids
        kb_ids_raw = params.get("knowledge_base_ids") or []
        kb_ids: list[str] = []
        for k in kb_ids_raw:
            try:
                uuid.UUID(str(k))
                kb_ids.append(str(k))
            except ValueError:
                continue

        model_config: dict[str, Any] = {}
        if "temperature" in params:
            model_config["temperature"] = float(params["temperature"])
        if "max_tokens" in params:
            model_config["max_tokens"] = int(params["max_tokens"])

        agent = Agent(
            org_id=org_id,
            project_id=project_id,
            name=name,
            description=params.get("description"),
            system_prompt=sysprompt,
            model_id=params.get("model_id") or "auto",
            model_config=model_config,
            knowledge_base_ids=kb_ids,
            tool_policy={
                "mode": "none",
                "allowed": [],
                "denied": [],
                "http_allowlist": [],
            },
        )
        db.add(agent)
        await db.flush()
        await db.commit()

        return {
            "success": True,
            "agent_id": str(agent.id),
            "name": agent.name,
            "model_id": agent.model_id,
            "project_id": str(agent.project_id),
            "knowledge_base_ids": kb_ids,
            "next_step": (
                "Mint a gateway key with mint_gateway_key to call this agent, "
                "or attach more KBs with link_kb_to_agent."
            ),
        }
