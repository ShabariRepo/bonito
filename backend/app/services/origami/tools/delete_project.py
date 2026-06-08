"""delete_project — hard-delete a project + cascade everything in it.

Cascades agents, connections, groups, schedules, and project tokens via
FK rules. KBs and gateway keys live at the org level and don't cascade
automatically — by default we ALSO delete the ones associated with the
project (KBs tagged with project_id in source_config, gateway keys whose
display name contains the project name). The user can opt out with
delete_associated_kbs=False / delete_associated_gateway_keys=False.

Admin-only. Plan-card-gated like every other write tool, so the user
sees the cascade preview before clicking Deploy.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import select, delete as sa_delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.origami.tools.base import OrigamiTool, register_tool


@register_tool
class DeleteProjectTool(OrigamiTool):
    name = "delete_project"
    description = (
        "PERMANENTLY delete a project and everything inside it. Agents, "
        "agent connections, agent groups, schedules, and project-scoped "
        "tokens all cascade. Knowledge bases and gateway keys associated "
        "with the project are also deleted by default (opt out via "
        "delete_associated_kbs=False or "
        "delete_associated_gateway_keys=False). Org admins only. Use this "
        "when the user explicitly asks to delete / remove / wipe a project. "
        "The plan card shows the full cascade preview before Deploy."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "UUID of the project to delete. If you only know the name, pass project_name.",
            },
            "project_name": {
                "type": "string",
                "description": "Display name of the project — resolved to a UUID server-side.",
            },
            "delete_associated_kbs": {
                "type": "boolean",
                "description": "Also delete KBs tagged with this project_id. Default true.",
            },
            "delete_associated_gateway_keys": {
                "type": "boolean",
                "description": "Also delete gateway keys whose display name contains the project name. Default true.",
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
        from app.models.project import Project
        from app.models.agent import Agent
        from app.models.agent_connection import AgentConnection
        from app.models.knowledge_base import KnowledgeBase, KBChunk, KBDocument
        from app.models.gateway import GatewayKey
        from app.models.access_token import AccessToken
        from app.models.agent_group import AgentGroup
        from app.models.agent_schedule import AgentSchedule

        # Admin check
        if getattr(user, "role", None) != "admin":
            return {
                "success": False,
                "error": "admin_required",
                "message": "Only org admins can delete projects.",
            }

        # Resolve project
        project_id_raw = params.get("project_id")
        project_name = (params.get("project_name") or "").strip()
        project: Optional[Project] = None

        if project_id_raw:
            try:
                pid = uuid.UUID(str(project_id_raw))
            except (TypeError, ValueError):
                return {"success": False, "error": "invalid_project_id",
                        "message": "project_id must be a valid UUID."}
            row = await db.execute(
                select(Project).where(Project.id == pid, Project.org_id == org_id)
            )
            project = row.scalar_one_or_none()
        elif project_name:
            row = await db.execute(
                select(Project)
                .where(Project.name == project_name, Project.org_id == org_id)
                .order_by(Project.created_at.desc())
                .limit(1)
            )
            project = row.scalar_one_or_none()
        else:
            return {"success": False, "error": "missing_project_reference",
                    "message": "Provide either project_id or project_name."}

        if not project:
            ref = project_id_raw or project_name
            return {"success": False, "error": "project_not_found",
                    "message": f"Project '{ref}' not found in your organization."}

        delete_kbs = params.get("delete_associated_kbs", True) is not False
        delete_keys = params.get("delete_associated_gateway_keys", True) is not False

        # Count what'll cascade (for the return summary)
        async def _count(model, *filters) -> int:
            r = await db.execute(select(func.count(model.id)).where(*filters))
            return int(r.scalar_one() or 0)

        agents_count = await _count(
            Agent, Agent.project_id == project.id, Agent.org_id == org_id
        )
        connections_count = await _count(
            AgentConnection,
            AgentConnection.project_id == project.id,
            AgentConnection.org_id == org_id,
        )
        groups_count = await _count(
            AgentGroup,
            AgentGroup.project_id == project.id,
            AgentGroup.org_id == org_id,
        )
        schedules_count = await _count(
            AgentSchedule,
            AgentSchedule.project_id == project.id,
            AgentSchedule.org_id == org_id,
        )
        project_tokens_count = await _count(
            AccessToken,
            AccessToken.project_id == project.id,
            AccessToken.org_id == org_id,
            AccessToken.token_type == "project",
            AccessToken.revoked_at.is_(None),
        )

        # Resolve associated KBs (by source_config.project_id tag)
        kb_rows = (await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.org_id == org_id)
        )).scalars().all()
        associated_kbs = [
            kb for kb in kb_rows
            if isinstance(kb.source_config, dict)
            and kb.source_config.get("project_id") == str(project.id)
        ]
        kbs_deleted = []
        if delete_kbs and associated_kbs:
            kb_ids = [kb.id for kb in associated_kbs]
            await db.execute(
                sa_delete(KBChunk).where(
                    KBChunk.knowledge_base_id.in_(kb_ids),
                    KBChunk.org_id == org_id,
                )
            )
            await db.execute(
                sa_delete(KBDocument).where(
                    KBDocument.knowledge_base_id.in_(kb_ids),
                    KBDocument.org_id == org_id,
                )
            )
            await db.execute(
                sa_delete(KnowledgeBase).where(
                    KnowledgeBase.id.in_(kb_ids), KnowledgeBase.org_id == org_id,
                )
            )
            kbs_deleted = [{"id": str(kb.id), "name": kb.name} for kb in associated_kbs]

        # Resolve associated gateway keys (best-effort name match)
        gk_rows = (await db.execute(
            select(GatewayKey).where(
                GatewayKey.org_id == org_id,
                GatewayKey.revoked_at.is_(None),
            )
        )).scalars().all()
        associated_keys = [
            gk for gk in gk_rows
            if project.name.lower() in (gk.name or "").lower()
        ]
        keys_deleted = []
        if delete_keys and associated_keys:
            gk_ids = [gk.id for gk in associated_keys]
            await db.execute(
                sa_delete(GatewayKey).where(
                    GatewayKey.id.in_(gk_ids), GatewayKey.org_id == org_id,
                )
            )
            keys_deleted = [
                {"id": str(gk.id), "name": gk.name, "key_prefix": gk.key_prefix}
                for gk in associated_keys
            ]

        # Finally drop the project — FK cascades take the agents etc.
        project_name_str = project.name
        project_id_str = str(project.id)
        await db.delete(project)
        await db.commit()

        return {
            "success": True,
            "deleted_project_id": project_id_str,
            "deleted_project_name": project_name_str,
            "cascaded": {
                "agents": agents_count,
                "agent_connections": connections_count,
                "agent_groups": groups_count,
                "agent_schedules": schedules_count,
                "project_tokens": project_tokens_count,
            },
            "knowledge_bases_deleted": kbs_deleted,
            "gateway_keys_deleted": keys_deleted,
            "next_step": (
                f"Project '{project_name_str}' is gone. "
                f"{agents_count} agent{'s' if agents_count != 1 else ''} "
                f"cascaded. {len(kbs_deleted)} KB / {len(keys_deleted)} "
                f"gateway key deleted alongside."
            ),
        }
