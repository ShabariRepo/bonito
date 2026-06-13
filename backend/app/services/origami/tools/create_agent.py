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
                    "to 'auto' which lets Bonito's routing pick. NOTE: this "
                    "field is sometimes called `model` colloquially — both "
                    "names are accepted."
                ),
            },
            "model": {
                "type": "string",
                "description": "Alias for model_id (accepted because models call it `model` half the time).",
            },
            "project_id": {
                "type": "string",
                "description": "UUID of the project this agent lives in. If you only know the project's display name, pass `project_name` instead. If neither is given, picks the user's first project.",
            },
            "project_name": {
                "type": "string",
                "description": "Display name of the project — resolved to a UUID server-side. Use this when the user references a project by name (e.g. 'foundations-matchmaker').",
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

        # Resolve project_id robustly. The model isn't reliable about
        # which field it uses, so accept the project reference from EITHER
        # `project_id` or `project_name`, and treat a non-UUID project_id
        # as a name (the common failure: model passes the display name in
        # the project_id field, or an unresolved ${step_N.project_id}
        # template that should be a name). Resolution order:
        #   1. project_id that's a valid UUID, owned by the org
        #   2. any non-UUID project reference (from project_id OR
        #      project_name) resolved as a display name
        #   3. fall back to the org's most-recently-created project
        project_id_raw = params.get("project_id")
        project_name = (params.get("project_name") or "").strip()
        project_id: Optional[uuid.UUID] = None

        # Treat a non-UUID project_id as a name candidate.
        name_candidate = project_name
        if project_id_raw:
            try:
                candidate_uuid = uuid.UUID(str(project_id_raw))
                owner_check = await db.execute(
                    select(Project.id).where(
                        Project.id == candidate_uuid,
                        Project.org_id == org_id,
                    )
                )
                if owner_check.scalar_one_or_none():
                    project_id = candidate_uuid
                # If the UUID is well-formed but not in this org, fall
                # through to name/fallback resolution rather than erroring.
            except (ValueError, TypeError):
                # project_id wasn't a UUID — treat its string as a name.
                if not name_candidate:
                    name_candidate = str(project_id_raw).strip()

        if project_id is None and name_candidate:
            # Names aren't unique — take the most recent match instead of
            # crashing on scalar_one_or_none when duplicates exist.
            row = await db.execute(
                select(Project.id).where(
                    Project.name == name_candidate,
                    Project.org_id == org_id,
                ).order_by(Project.created_at.desc()).limit(1)
            )
            project_id = row.scalars().first()

        if project_id is None:
            # Last resort: the org's most recent project. Better to put
            # the agent SOMEWHERE deployable than to hard-fail a build.
            fallback = await db.execute(
                select(Project.id)
                .where(Project.org_id == org_id)
                .order_by(Project.created_at.desc())
                .limit(1)
            )
            project_id = fallback.scalar_one_or_none()
            if project_id is None:
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

        # Accept `model` as an alias for `model_id` — the LLM emits both
        # depending on the day. Prefer the explicit one if both are set.
        resolved_model_id = (
            params.get("model_id")
            or params.get("model")
            or "auto"
        )

        agent = Agent(
            org_id=org_id,
            project_id=project_id,
            name=name,
            description=params.get("description"),
            system_prompt=sysprompt,
            model_id=resolved_model_id,
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
