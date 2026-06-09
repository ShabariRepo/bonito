"""connect_agents — wire two existing Bonobot agents together.

Creates an AgentConnection row of one of four kinds:

  handoff     — source agent transfers the conversation to target
  escalation  — source asks target for help on a hard case
  data_feed   — source pushes structured output into target
  trigger     — source's completion fires target as a follow-up

Both agents must live in the same project (the row carries a single
project_id) and the user's org. Accepts either UUIDs or display names
for source/target — names are resolved server-side, scoped to the
caller's org so cross-tenant wiring is impossible.

Plan-card-gated. Used heavily for hub-and-spoke topologies where a
central router/intake agent delegates to specialist spokes.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.origami.tools.base import OrigamiTool, register_tool


_VALID_TYPES = {"handoff", "escalation", "data_feed", "trigger"}


@register_tool
class ConnectAgentsTool(OrigamiTool):
    name = "connect_agents"
    description = (
        "Wire two existing Bonobot agents together with a directional "
        "connection. Used to build agent topologies — hub-and-spoke "
        "(central router handoff-ing to specialist spokes), escalation "
        "chains (tier-1 → tier-2 → tier-3 support), data pipelines "
        "(extractor → enricher → publisher), or trigger graphs (job "
        "completion fires the next agent). Both agents must already "
        "exist in the same project. Pass either UUIDs (agent_id) or "
        "display names (agent_name) for source and target."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "source_agent_id": {
                "type": "string",
                "description": "UUID of the source agent (the one initiating the connection).",
            },
            "source_agent_name": {
                "type": "string",
                "description": "Display name of the source agent — resolved to a UUID server-side.",
            },
            "target_agent_id": {
                "type": "string",
                "description": "UUID of the target agent (the one receiving the handoff/escalation/feed/trigger).",
            },
            "target_agent_name": {
                "type": "string",
                "description": "Display name of the target agent — resolved to a UUID server-side.",
            },
            "from_agent_id": {
                "type": "string",
                "description": "Alias for source_agent_id. Accepted because models often use from/to terminology.",
            },
            "from_agent_name": {
                "type": "string",
                "description": "Alias for source_agent_name.",
            },
            "to_agent_id": {
                "type": "string",
                "description": "Alias for target_agent_id.",
            },
            "to_agent_name": {
                "type": "string",
                "description": "Alias for target_agent_name.",
            },
            "connection_type": {
                "type": "string",
                "enum": sorted(_VALID_TYPES),
                "description": (
                    "Kind of wiring: 'handoff' (transfer the conversation), "
                    "'escalation' (ask for help), 'data_feed' (push structured "
                    "output), or 'trigger' (fire as a follow-up job)."
                ),
            },
            "label": {
                "type": "string",
                "maxLength": 255,
                "description": "Optional human-readable label shown on the canvas edge.",
            },
        },
        "required": ["connection_type"],
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
        from app.models.agent_connection import AgentConnection

        connection_type = (params.get("connection_type") or "").strip().lower()
        if connection_type not in _VALID_TYPES:
            return {
                "success": False,
                "error": "invalid_connection_type",
                "message": (
                    f"connection_type must be one of: {sorted(_VALID_TYPES)}."
                ),
            }

        # Accept from_*/to_* as aliases for source_*/target_* — models
        # routinely use the friendlier names. Prefer the canonical name
        # if both are set.
        source_uuid = params.get("source_agent_id") or params.get("from_agent_id")
        source_name = (
            params.get("source_agent_name")
            or params.get("from_agent_name")
            or ""
        ).strip()
        target_uuid = params.get("target_agent_id") or params.get("to_agent_id")
        target_name = (
            params.get("target_agent_name")
            or params.get("to_agent_name")
            or ""
        ).strip()

        source = await _resolve_agent(
            db, org_id=org_id, uuid_raw=source_uuid, name=source_name, role="source",
        )
        if isinstance(source, dict):
            return source

        target = await _resolve_agent(
            db, org_id=org_id, uuid_raw=target_uuid, name=target_name, role="target",
        )
        if isinstance(target, dict):
            return target

        if source.id == target.id:
            return {
                "success": False,
                "error": "self_loop",
                "message": "source and target must be different agents.",
            }

        if source.project_id != target.project_id:
            return {
                "success": False,
                "error": "different_projects",
                "message": (
                    "Both agents must belong to the same project. "
                    f"source='{source.name}' is in project {source.project_id}, "
                    f"target='{target.name}' is in project {target.project_id}."
                ),
            }
        if not source.project_id:
            return {
                "success": False,
                "error": "no_project",
                "message": "Both agents must belong to a project (neither has one set).",
            }

        # Idempotent: if the same (source, target, type) row already exists,
        # return it instead of creating a duplicate.
        existing = await db.execute(
            select(AgentConnection).where(
                AgentConnection.org_id == org_id,
                AgentConnection.source_agent_id == source.id,
                AgentConnection.target_agent_id == target.id,
                AgentConnection.connection_type == connection_type,
            )
        )
        prior = existing.scalar_one_or_none()
        if prior:
            return {
                "success": True,
                "already_exists": True,
                "connection_id": str(prior.id),
                "source_agent_id": str(source.id),
                "target_agent_id": str(target.id),
                "source_agent_name": source.name,
                "target_agent_name": target.name,
                "connection_type": connection_type,
                "label": prior.label,
            }

        conn = AgentConnection(
            org_id=org_id,
            project_id=source.project_id,
            source_agent_id=source.id,
            target_agent_id=target.id,
            connection_type=connection_type,
            label=(params.get("label") or None),
            enabled=True,
        )
        db.add(conn)
        await db.flush()
        await db.commit()

        return {
            "success": True,
            "connection_id": str(conn.id),
            "source_agent_id": str(source.id),
            "target_agent_id": str(target.id),
            "source_agent_name": source.name,
            "target_agent_name": target.name,
            "connection_type": connection_type,
            "label": conn.label,
            "next_step": (
                "Visible on the canvas under this project. Re-call with the "
                "same source/target/type for idempotency, or use a different "
                "type to add a parallel edge."
            ),
        }


async def _resolve_agent(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    uuid_raw: Optional[str],
    name: str,
    role: str,
):
    """Resolve an agent by UUID or display name, scoped to the org.

    Returns the Agent on success, or an error envelope (dict) on failure
    that the caller can return directly.
    """
    from app.models.agent import Agent

    if uuid_raw:
        try:
            aid = uuid.UUID(str(uuid_raw))
        except (TypeError, ValueError):
            return {
                "success": False,
                "error": f"invalid_{role}_agent_id",
                "message": f"{role}_agent_id must be a valid UUID.",
            }
        row = await db.execute(
            select(Agent).where(Agent.id == aid, Agent.org_id == org_id)
        )
        agent = row.scalar_one_or_none()
    elif name:
        # Names CAN duplicate across an org (no unique constraint). Pick the
        # most recently created so chained writes in the same plan always
        # find the agent that was just created earlier in the plan.
        row = await db.execute(
            select(Agent)
            .where(Agent.name == name, Agent.org_id == org_id)
            .order_by(Agent.created_at.desc())
            .limit(1)
        )
        agent = row.scalar_one_or_none()
    else:
        return {
            "success": False,
            "error": f"missing_{role}_agent_reference",
            "message": (
                f"Provide either {role}_agent_id (UUID) or "
                f"{role}_agent_name (display name)."
            ),
        }

    if not agent:
        ref = uuid_raw or name
        return {
            "success": False,
            "error": f"{role}_agent_not_found",
            "message": f"{role} agent '{ref}' not found in your organization.",
        }
    return agent
