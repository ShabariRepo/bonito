"""create_project — group agents and budgets together.

Projects in Bonito are how customers organize multi-tenant builds:
one project per end-customer of theirs, per environment, etc. Each
project carries a monthly budget cap (optional).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.origami.tools.base import OrigamiTool, register_tool


@register_tool
class CreateProjectTool(OrigamiTool):
    name = "create_project"
    description = (
        "Create a new project for the user's organization. Projects group "
        "agents and budgets together — useful when the user is building "
        "multiple agents for different customers, environments, or teams. "
        "Returns project_id which can be passed to create_agent's project_id."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "minLength": 1,
                "maxLength": 255,
                "description": "Display name, e.g. 'shopify-prod' or 'memorycreative-peller'",
            },
            "description": {
                "type": "string",
                "maxLength": 2000,
                "description": "Optional one-liner about what this project is for",
            },
            "monthly_budget_usd": {
                "type": "number",
                "minimum": 0,
                "description": "Optional monthly spend cap in USD",
            },
        },
        "required": ["name"],
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
        from app.models.project import Project

        # Tier cap (Free=1 / Builder=1 / Growth=3 / Pro=5 / Enterprise+=unlimited)
        project_caps = {"free": 1, "builder": 1, "starter": 1, "growth": 3, "pro": 5}
        from app.services.feature_gate import feature_gate
        try:
            sub = await feature_gate.get_organization_subscription(db, str(org_id))
            tier = (sub["tier"].value if hasattr(sub["tier"], "value") else str(sub["tier"])).lower()
        except Exception:
            tier = "free"

        cap = project_caps.get(tier)
        if cap is not None:
            existing = await db.execute(
                select(func.count(Project.id)).where(Project.org_id == org_id)
            )
            count = int(existing.scalar_one() or 0)
            if count >= cap:
                return {
                    "success": False,
                    "error": "project_quota_exceeded",
                    "message": f"You're at {count}/{cap} projects on the {tier} tier.",
                    "tier": tier,
                }

        name = (params.get("name") or "").strip()
        if not name:
            return {"success": False, "error": "missing_name", "message": "Project name is required."}

        proj = Project(
            org_id=org_id,
            name=name,
            description=params.get("description"),
            status="active",
        )
        budget = params.get("monthly_budget_usd")
        if budget is not None:
            from decimal import Decimal
            try:
                proj.budget_monthly = Decimal(str(budget))
            except Exception:
                pass

        db.add(proj)
        await db.flush()
        await db.commit()

        return {
            "success": True,
            "project_id": str(proj.id),
            "name": proj.name,
            "status": proj.status,
            "monthly_budget_usd": float(proj.budget_monthly) if proj.budget_monthly else None,
            "next_step": "Create agents in this project via create_agent with project_id.",
        }
