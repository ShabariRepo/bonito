"""list_deleted_projects — show project manifests available for restore.

Read-only. Returns the per-org list of saved manifests with metadata
about what's inside each one (agent count, connection count, KB count)
and whether it's been restored yet.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.origami.tools.base import OrigamiTool, register_tool


@register_tool
class ListDeletedProjectsTool(OrigamiTool):
    name = "list_deleted_projects"
    description = (
        "List previously-deleted projects whose manifests are saved and "
        "available for skeleton restore via restore_project. Returns "
        "per-manifest: project name, when deleted, who deleted, agent "
        "count, connection count, KB count, and whether already restored. "
        "Use when the user asks 'what did I delete', 'what can I restore', "
        "'show me my deleted projects', or similar."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "include_restored": {
                "type": "boolean",
                "description": "Include manifests that have already been restored (default false).",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
                "description": "Max manifests to return. Default 25.",
            },
        },
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
        from app.models.project_manifest import ProjectManifest

        include_restored = bool(params.get("include_restored", False))
        limit = int(params.get("limit") or 25)
        limit = max(1, min(limit, 100))

        stmt = select(ProjectManifest).where(ProjectManifest.org_id == org_id)
        if not include_restored:
            stmt = stmt.where(ProjectManifest.restored_at.is_(None))
        stmt = stmt.order_by(ProjectManifest.deleted_at.desc()).limit(limit)

        rows = (await db.execute(stmt)).scalars().all()
        manifests = []
        for m in rows:
            payload = m.manifest or {}
            manifests.append({
                "manifest_id": str(m.id),
                "project_name": m.project_name,
                "description": m.description,
                "deleted_at": m.deleted_at.isoformat() if m.deleted_at else None,
                "deleted_by_user_id": str(m.deleted_by_user_id) if m.deleted_by_user_id else None,
                "restored": m.restored_at is not None,
                "restored_at": m.restored_at.isoformat() if m.restored_at else None,
                "restored_to_project_id": str(m.restored_to_project_id) if m.restored_to_project_id else None,
                "agent_count": len(payload.get("agents", [])),
                "connection_count": len(payload.get("connections", [])),
                "kb_count": len(payload.get("knowledge_bases", [])),
            })

        return {
            "success": True,
            "count": len(manifests),
            "manifests": manifests,
            "next_step": (
                "Restore one with: restore_project(project_name='X') "
                "or restore_project(manifest_id='Y') for a specific snapshot."
            ),
        }
