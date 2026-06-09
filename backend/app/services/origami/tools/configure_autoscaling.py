"""configure_autoscaling — enable or tune agent HPA from chat.

Wraps the existing POST /agents/{id}/scaling/configure logic. Lets a
user say "scale my deal-intake agent to 10 replicas under load" and
have it actually fire. Enterprise+ only — tier-gated through
feature_gate.require_feature("agent_hpa") at execution time.

Default config (matches the API defaults):
- capacity_threshold = 0.6 (start scaling at 60% RPM utilization)
- scale_down_threshold = 0.3 (scale back down at 30%)
- scale_down_cooldown_seconds = 300
- max_replicas = 5 (user-overridable up to 10)
- mode = "virtual" (Phase 1 — Redis-based RPM doubling)
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.origami.tools.base import OrigamiTool, register_tool


@register_tool
class ConfigureAutoscalingTool(OrigamiTool):
    name = "configure_autoscaling"
    description = (
        "INVOKE THIS TOOL whenever the user says 'set up auto-scaling', "
        "'enable HPA', 'scale my agent', 'scale X to N replicas', 'turn on "
        "autoscaling for Y', or any variant. Configures Bonito's agent HPA "
        "(horizontal pod autoscaler) for a specific agent. Enterprise+ "
        "only; the tool returns a tier-upgrade prompt if the org is on a "
        "lower tier. Defaults: 60% utilization threshold, 30% scale-down, "
        "5-min cooldown, 5 max replicas, virtual mode. The user can "
        "override max_replicas (up to 10) and threshold."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "string",
                "description": "UUID of the agent. If you only know the name, pass agent_name.",
            },
            "agent_name": {
                "type": "string",
                "description": "Display name of the agent — resolved to a UUID server-side.",
            },
            "enabled": {
                "type": "boolean",
                "description": "Turn autoscaling on (default true) or off (false to disable).",
            },
            "max_replicas": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "description": "Maximum effective replicas. Default 5. Hard cap 10.",
            },
            "capacity_threshold": {
                "type": "number",
                "minimum": 0.1,
                "maximum": 0.95,
                "description": "Utilization (0.0-1.0) that triggers scale-up. Default 0.6.",
            },
            "scale_down_threshold": {
                "type": "number",
                "minimum": 0.05,
                "maximum": 0.9,
                "description": "Utilization that triggers scale-down. Must be < capacity_threshold. Default 0.3.",
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
        from app.services.feature_gate import feature_gate

        # ── Tier gate ─────────────────────────────────────────────────
        try:
            await feature_gate.require_feature(db, str(org_id), "agent_hpa")
        except Exception as e:
            try:
                sub = await feature_gate.get_organization_subscription(db, str(org_id))
                tier = (sub["tier"].value if hasattr(sub["tier"], "value") else str(sub["tier"])).lower()
            except Exception:
                tier = "free"
            return {
                "success": False,
                "error": "feature_gated",
                "tier": tier,
                "required_tier": "enterprise",
                "message": (
                    f"Agent HPA (autoscaling) is an Enterprise feature. "
                    f"You're on the {tier} tier. Upgrade at getbonito.com/pricing "
                    f"or contact sales."
                ),
            }

        # ── Resolve agent ─────────────────────────────────────────────
        agent_id_raw = params.get("agent_id")
        agent_name = (params.get("agent_name") or "").strip()
        agent: Optional[Agent] = None

        if agent_id_raw:
            try:
                aid = uuid.UUID(str(agent_id_raw))
            except (TypeError, ValueError):
                return {"success": False, "error": "invalid_agent_id",
                        "message": "agent_id must be a valid UUID."}
            agent = (await db.execute(
                select(Agent).where(Agent.id == aid, Agent.org_id == org_id)
            )).scalar_one_or_none()
        elif agent_name:
            agent = (await db.execute(
                select(Agent)
                .where(Agent.name == agent_name, Agent.org_id == org_id)
                .order_by(Agent.created_at.desc())
                .limit(1)
            )).scalar_one_or_none()
        else:
            return {"success": False, "error": "missing_agent_reference",
                    "message": "Provide either agent_id or agent_name."}

        if not agent:
            ref = agent_id_raw or agent_name
            return {"success": False, "error": "agent_not_found",
                    "message": f"Agent '{ref}' not found in your organization."}

        # ── Validate config (mirrors the API) ─────────────────────────
        enabled = params.get("enabled")
        if enabled is None:
            enabled = True
        threshold = float(params.get("capacity_threshold") or 0.6)
        scale_down = float(params.get("scale_down_threshold") or 0.3)
        max_replicas = int(params.get("max_replicas") or 5)

        if not (0.1 <= threshold <= 0.95):
            return {"success": False, "error": "invalid_threshold",
                    "message": "capacity_threshold must be between 0.1 and 0.95."}
        if not (0.05 <= scale_down < threshold):
            return {"success": False, "error": "invalid_scale_down",
                    "message": "scale_down_threshold must be between 0.05 and less than capacity_threshold."}
        if not (1 <= max_replicas <= 10):
            return {"success": False, "error": "invalid_max_replicas",
                    "message": "max_replicas must be between 1 and 10."}

        agent.autoscale_enabled = enabled
        agent.autoscale_config = {
            "capacity_threshold": threshold,
            "scale_down_threshold": scale_down,
            "scale_down_cooldown_seconds": 300,
            "max_replicas": max_replicas,
            "mode": "virtual",
        }
        await db.flush()
        await db.commit()

        return {
            "success": True,
            "agent_id": str(agent.id),
            "agent_name": agent.name,
            "autoscale_enabled": agent.autoscale_enabled,
            "autoscale_config": agent.autoscale_config,
            "next_step": (
                f"Autoscaling {'enabled' if enabled else 'disabled'} for "
                f"{agent.name}. Effective RPM will double in Redis when "
                f"utilization crosses {int(threshold*100)}% (up to "
                f"{max_replicas}x base). Scale-down kicks in below "
                f"{int(scale_down*100)}% after a 5-min cooldown."
            ),
        }
