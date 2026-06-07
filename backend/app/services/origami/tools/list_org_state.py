"""list_org_state — read-only snapshot of the user's org.

Returns providers, agents, KBs, projects, tier, and basic usage so Origami
knows what's already wired up before planning a build.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.origami.tools.base import OrigamiTool, register_tool


@register_tool
class ListOrgStateTool(OrigamiTool):
    name = "list_org_state"
    description = (
        "Return a snapshot of the user's organization: connected providers, "
        "agents, knowledge bases, projects, current subscription tier. "
        "Use this before proposing a build so you know what already exists "
        "and what the user has access to. No parameters required."
    )
    input_schema = {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }
    is_write = False

    async def execute(
        self,
        *,
        org_id: uuid.UUID,
        user: User,
        params: dict[str, Any],
        db: AsyncSession,
    ) -> dict[str, Any]:
        # Import lazily so this module loads even if a model import has a side effect.
        from app.models.cloud_provider import CloudProvider
        from app.models.agent import Agent
        from app.models.knowledge_base import KnowledgeBase
        from app.models.project import Project
        from app.services.feature_gate import feature_gate

        # Providers
        providers_result = await db.execute(
            select(CloudProvider.id, CloudProvider.provider_type, CloudProvider.status).where(
                CloudProvider.org_id == org_id
            )
        )
        providers = [
            {
                "id": str(row.id),
                "type": row.provider_type,
                "status": row.status,  # pending | active | error
                "active": row.status == "active",
            }
            for row in providers_result
        ]

        # Agents (just counts + names — full details on demand)
        agents_result = await db.execute(
            select(Agent.id, Agent.name, Agent.model_id).where(
                Agent.org_id == org_id
            ).limit(50)
        )
        agents = [
            {"id": str(row.id), "name": row.name, "model_id": row.model_id}
            for row in agents_result
        ]

        # KBs
        kbs_result = await db.execute(
            select(KnowledgeBase.id, KnowledgeBase.name, KnowledgeBase.status).where(
                KnowledgeBase.org_id == org_id
            ).limit(50)
        )
        kbs = [
            {"id": str(row.id), "name": row.name, "status": row.status}
            for row in kbs_result
        ]

        # Projects
        projects_result = await db.execute(
            select(Project.id, Project.name).where(Project.org_id == org_id).limit(50)
        )
        projects = [{"id": str(row.id), "name": row.name} for row in projects_result]

        # Subscription tier (live read)
        try:
            subscription = await feature_gate.get_organization_subscription(db, str(org_id))
            tier_name = (
                subscription["tier"].value
                if hasattr(subscription["tier"], "value")
                else str(subscription["tier"])
            )
        except Exception:
            # Defensive: if tier lookup fails, default to free
            tier_name = "free"

        return {
            "providers": providers,
            "agents": agents,
            "knowledge_bases": kbs,
            "projects": projects,
            "tier": tier_name,
            "counts": {
                "providers": len(providers),
                "agents": len(agents),
                "kbs": len(kbs),
                "projects": len(projects),
            },
        }
