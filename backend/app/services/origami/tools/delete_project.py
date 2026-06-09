"""delete_project — hard-delete a project + write a manifest for restore.

Workflow:
1. Snapshot the project structure (agents, connections, KB associations)
   into the project_manifests table.
2. Hard-delete agents, connections, project (SQL-level so cascade rules
   fire correctly — the ORM delete-then-commit path had a session issue
   that caused the deletes to not persist when called in a loop).
3. Optionally delete project-tagged KBs.
4. Optionally revoke (not hard-delete — gateway_requests FK doesn't
   cascade) gateway keys named after the project.

Admin-only. Plan-card-gated. Manifest is persisted so restore_project
can rebuild the skeleton later.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from datetime import datetime, timezone
from sqlalchemy import select, delete as sa_delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.origami.tools.base import OrigamiTool, register_tool

logger = logging.getLogger(__name__)


@register_tool
class DeleteProjectTool(OrigamiTool):
    name = "delete_project"
    description = (
        "PERMANENTLY delete a project and everything inside it. Cascades "
        "agents, agent connections, agent groups, schedules, and project "
        "tokens. Tagged knowledge bases are deleted by default (opt out "
        "via delete_associated_kbs=False). Gateway keys named after the "
        "project are revoked (opt out via delete_associated_gateway_keys"
        "=False). Org admins only. Use when the user explicitly asks to "
        "delete / remove / wipe a project. A manifest is saved so the "
        "skeleton (project + agents + connections) can be one-click "
        "restored later via restore_project."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string"},
            "project_name": {"type": "string"},
            "delete_associated_kbs": {"type": "boolean"},
            "delete_associated_gateway_keys": {"type": "boolean"},
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
        from app.models.project_manifest import ProjectManifest

        if getattr(user, "role", None) != "admin":
            return {"success": False, "error": "admin_required",
                    "message": "Only org admins can delete projects."}

        # ── Resolve project ────────────────────────────────────────────
        project_id_raw = params.get("project_id")
        project_name = (params.get("project_name") or "").strip()
        project: Optional[Project] = None

        if project_id_raw:
            try:
                pid = uuid.UUID(str(project_id_raw))
            except (TypeError, ValueError):
                return {"success": False, "error": "invalid_project_id",
                        "message": "project_id must be a valid UUID."}
            project = (await db.execute(
                select(Project).where(Project.id == pid, Project.org_id == org_id)
            )).scalar_one_or_none()
        elif project_name:
            project = (await db.execute(
                select(Project)
                .where(Project.name == project_name, Project.org_id == org_id)
                .order_by(Project.created_at.desc())
                .limit(1)
            )).scalar_one_or_none()
        else:
            return {"success": False, "error": "missing_project_reference",
                    "message": "Provide either project_id or project_name."}

        if not project:
            ref = project_id_raw or project_name
            return {"success": False, "error": "project_not_found",
                    "message": f"Project '{ref}' not found in your organization."}

        delete_kbs = params.get("delete_associated_kbs", True) is not False
        delete_keys = params.get("delete_associated_gateway_keys", True) is not False

        # ── Snapshot for manifest ──────────────────────────────────────
        agents = (await db.execute(
            select(Agent).where(Agent.project_id == project.id, Agent.org_id == org_id)
        )).scalars().all()
        connections = (await db.execute(
            select(AgentConnection).where(
                AgentConnection.project_id == project.id,
                AgentConnection.org_id == org_id,
            )
        )).scalars().all()
        agent_by_id = {a.id: a for a in agents}

        manifest_agents = []
        for a in agents:
            manifest_agents.append({
                "name": a.name,
                "description": a.description,
                "system_prompt": a.system_prompt,
                "model_id": a.model_id,
                "model_config": a.model_config or {},
                "tool_policy": a.tool_policy or {},
                "rate_limit_rpm": a.rate_limit_rpm,
                "knowledge_base_names": [],  # filled below
            })
        # Map KB ids → KB names so the manifest survives KB deletes/renames
        all_kbs_now = (await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.org_id == org_id)
        )).scalars().all()
        kb_id_to_name = {str(kb.id): kb.name for kb in all_kbs_now}
        for i, a in enumerate(agents):
            kb_ids = a.knowledge_base_ids or []
            manifest_agents[i]["knowledge_base_names"] = [
                kb_id_to_name[kid] for kid in kb_ids if kid in kb_id_to_name
            ]

        manifest_connections = [
            {
                "source_agent_name": agent_by_id[c.source_agent_id].name if c.source_agent_id in agent_by_id else None,
                "target_agent_name": agent_by_id[c.target_agent_id].name if c.target_agent_id in agent_by_id else None,
                "connection_type": c.connection_type,
                "label": c.label,
            }
            for c in connections
            if c.source_agent_id in agent_by_id and c.target_agent_id in agent_by_id
        ]

        # KBs tagged with this project_id
        tagged_kbs = [
            kb for kb in all_kbs_now
            if isinstance(kb.source_config, dict)
            and kb.source_config.get("project_id") == str(project.id)
        ]
        manifest_kb_names = [{"name": kb.name, "description": kb.description} for kb in tagged_kbs]

        manifest_payload = {
            "version": 1,
            "project": {
                "name": project.name,
                "description": project.description,
            },
            "agents": manifest_agents,
            "connections": manifest_connections,
            "knowledge_bases": manifest_kb_names,
        }

        # Persist manifest BEFORE deletion
        manifest_row = ProjectManifest(
            org_id=org_id,
            project_name=project.name,
            description=project.description,
            manifest=manifest_payload,
            deleted_by_user_id=user.id,
        )
        db.add(manifest_row)
        await db.flush()
        manifest_id = str(manifest_row.id)

        # ── Delete in order (SQL-level so cascade rules fire) ──────────
        await db.execute(
            sa_delete(AgentConnection).where(
                AgentConnection.project_id == project.id,
                AgentConnection.org_id == org_id,
            )
        )
        await db.execute(
            sa_delete(Agent).where(
                Agent.project_id == project.id, Agent.org_id == org_id
            )
        )

        kbs_deleted: list[dict[str, str]] = []
        if delete_kbs and tagged_kbs:
            kb_ids = [kb.id for kb in tagged_kbs]
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
                    KnowledgeBase.id.in_(kb_ids),
                    KnowledgeBase.org_id == org_id,
                )
            )
            kbs_deleted = [{"id": str(kb.id), "name": kb.name} for kb in tagged_kbs]

        keys_revoked: list[dict[str, str]] = []
        if delete_keys:
            now = datetime.now(timezone.utc)
            matching_keys = (await db.execute(
                select(GatewayKey).where(
                    GatewayKey.org_id == org_id,
                    GatewayKey.revoked_at.is_(None),
                    GatewayKey.name.ilike(f"%{project.name}%"),
                )
            )).scalars().all()
            if matching_keys:
                await db.execute(
                    update(GatewayKey)
                    .where(GatewayKey.id.in_([k.id for k in matching_keys]))
                    .values(revoked_at=now)
                )
                keys_revoked = [
                    {"id": str(k.id), "name": k.name, "key_prefix": k.key_prefix}
                    for k in matching_keys
                ]

        # Finally drop the project
        project_name_str = project.name
        project_id_str = str(project.id)
        await db.execute(
            sa_delete(Project).where(Project.id == project.id, Project.org_id == org_id)
        )
        await db.commit()

        return {
            "success": True,
            "deleted_project_id": project_id_str,
            "deleted_project_name": project_name_str,
            "manifest_id": manifest_id,
            "cascaded": {
                "agents": len(agents),
                "agent_connections": len(connections),
            },
            "knowledge_bases_deleted": kbs_deleted,
            "gateway_keys_revoked": keys_revoked,
            "next_step": (
                f"Project '{project_name_str}' deleted. Saved a manifest "
                f"(id={manifest_id}). Run restore_project with this "
                f"project_name to rebuild the skeleton — agents and "
                f"connections come back, KB content and gateway keys "
                f"need to be re-uploaded / re-minted."
            ),
        }
