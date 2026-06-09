"""restore_project — one-click skeleton restore from a saved manifest.

When delete_project removes a project, it writes a ProjectManifest row
with the project + agents + connections + KB-association structure.
This tool reads the most recent un-restored manifest for a project
name (or by manifest_id) and rebuilds:

  ✓ Project (new UUID)
  ✓ Agents (same names, prompts, models, configs)
  ✓ Agent connections (same handoff/escalation graph)
  ✓ KB stubs (auto-created empty; same names as before)
  ✓ Agent ↔ KB links (re-wired)

What it does NOT restore:
  ✗ KB documents + chunks (user re-uploads via upload_to_kb)
  ✗ Gateway keys (user re-mints — security; keys can't be cloned)
  ✗ Tokens, schedules, approvals (re-create explicitly)

Admin-only. Marks the manifest as restored on success so the same
manifest isn't accidentally redeployed twice.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.user import User
from app.services.origami.tools.base import OrigamiTool, register_tool

logger = logging.getLogger(__name__)


@register_tool
class RestoreProjectTool(OrigamiTool):
    name = "restore_project"
    description = (
        "Rebuild a previously-deleted project from its saved manifest. "
        "Creates a fresh project with the same name, re-creates every "
        "agent (same prompts, models, configs), re-wires all the "
        "connections, auto-creates empty stubs for the KBs that were "
        "attached, and re-links agent ↔ KB associations. Skips KB "
        "content (you re-upload) and gateway keys (you re-mint). Use "
        "when the user says 'restore my X project', 'bring back X', "
        "'redeploy X', or similar. Admin only."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "manifest_id": {
                "type": "string",
                "description": "Specific manifest UUID to restore from. If omitted, the most recent un-restored manifest for project_name is used.",
            },
            "project_name": {
                "type": "string",
                "description": "Name of the deleted project to restore. Resolves to the most recent matching manifest.",
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
        from app.models.project_manifest import ProjectManifest
        from app.models.project import Project
        from app.models.agent import Agent
        from app.models.agent_connection import AgentConnection
        from app.models.knowledge_base import KnowledgeBase

        if getattr(user, "role", None) != "admin":
            return {"success": False, "error": "admin_required",
                    "message": "Only org admins can restore projects."}

        # ── Resolve manifest ───────────────────────────────────────────
        manifest_id_raw = params.get("manifest_id")
        project_name = (params.get("project_name") or "").strip()
        manifest: Optional[ProjectManifest] = None

        if manifest_id_raw:
            try:
                mid = uuid.UUID(str(manifest_id_raw))
            except (TypeError, ValueError):
                return {"success": False, "error": "invalid_manifest_id",
                        "message": "manifest_id must be a valid UUID."}
            manifest = (await db.execute(
                select(ProjectManifest).where(
                    ProjectManifest.id == mid, ProjectManifest.org_id == org_id
                )
            )).scalar_one_or_none()
        elif project_name:
            manifest = (await db.execute(
                select(ProjectManifest)
                .where(
                    ProjectManifest.org_id == org_id,
                    ProjectManifest.project_name == project_name,
                    ProjectManifest.restored_at.is_(None),
                )
                .order_by(ProjectManifest.deleted_at.desc())
                .limit(1)
            )).scalar_one_or_none()
        else:
            return {"success": False, "error": "missing_manifest_reference",
                    "message": "Provide either manifest_id or project_name."}

        if not manifest:
            ref = manifest_id_raw or project_name
            return {"success": False, "error": "manifest_not_found",
                    "message": f"No restorable manifest found for '{ref}'."}

        payload = manifest.manifest
        if not isinstance(payload, dict) or "project" not in payload:
            return {"success": False, "error": "malformed_manifest",
                    "message": "Manifest payload is missing required fields."}

        proj_meta = payload.get("project", {})

        # ── Recreate project ──────────────────────────────────────────
        new_project = Project(
            org_id=org_id,
            name=proj_meta.get("name") or manifest.project_name,
            description=proj_meta.get("description"),
            status="active",
        )
        db.add(new_project)
        await db.flush()
        new_project_id = new_project.id

        # ── Recreate KB stubs ─────────────────────────────────────────
        kb_name_to_id: dict[str, uuid.UUID] = {}
        kbs_created: list[dict[str, str]] = []
        for kb_meta in payload.get("knowledge_bases", []):
            name = kb_meta.get("name")
            if not name:
                continue
            # Re-use existing KB by name if present
            existing = (await db.execute(
                select(KnowledgeBase).where(
                    KnowledgeBase.org_id == org_id,
                    KnowledgeBase.name == name,
                )
            )).scalar_one_or_none()
            if existing:
                kb_name_to_id[name] = existing.id
                kbs_created.append({"id": str(existing.id), "name": name, "status": "reused-existing"})
            else:
                stub = KnowledgeBase(
                    org_id=org_id,
                    name=name,
                    description=(kb_meta.get("description")
                                 or "Restored from manifest — re-upload documents."),
                    source_type="upload",
                    source_config={"project_id": str(new_project_id)},
                    embedding_model="auto",
                    status="pending",
                )
                db.add(stub)
                await db.flush()
                kb_name_to_id[name] = stub.id
                kbs_created.append({"id": str(stub.id), "name": name, "status": "stub-created"})

        # ── Recreate agents ───────────────────────────────────────────
        agent_name_to_id: dict[str, uuid.UUID] = {}
        agents_created: list[dict[str, str]] = []
        for a_meta in payload.get("agents", []):
            kb_names = a_meta.get("knowledge_base_names", [])
            kb_ids = [str(kb_name_to_id[n]) for n in kb_names if n in kb_name_to_id]
            agent = Agent(
                org_id=org_id,
                project_id=new_project_id,
                name=a_meta.get("name", "unnamed"),
                description=a_meta.get("description"),
                system_prompt=a_meta.get("system_prompt", ""),
                model_id=a_meta.get("model_id", "auto"),
                model_config=a_meta.get("model_config") or {},
                knowledge_base_ids=kb_ids,
                tool_policy=a_meta.get("tool_policy") or {
                    "mode": "none", "allowed": [], "denied": [], "http_allowlist": [],
                },
                rate_limit_rpm=a_meta.get("rate_limit_rpm", 30),
            )
            db.add(agent)
            await db.flush()
            agent_name_to_id[agent.name] = agent.id
            agents_created.append({"id": str(agent.id), "name": agent.name})

        # ── Recreate connections ──────────────────────────────────────
        connections_created: list[dict[str, str]] = []
        for c_meta in payload.get("connections", []):
            src = c_meta.get("source_agent_name")
            tgt = c_meta.get("target_agent_name")
            if not src or not tgt:
                continue
            src_id = agent_name_to_id.get(src)
            tgt_id = agent_name_to_id.get(tgt)
            if not src_id or not tgt_id:
                continue
            conn = AgentConnection(
                org_id=org_id,
                project_id=new_project_id,
                source_agent_id=src_id,
                target_agent_id=tgt_id,
                connection_type=c_meta.get("connection_type", "handoff"),
                label=c_meta.get("label"),
                enabled=True,
            )
            db.add(conn)
            connections_created.append({
                "source": src, "target": tgt, "type": conn.connection_type,
            })

        # Mark manifest as restored
        manifest.restored_at = datetime.now(timezone.utc)
        manifest.restored_to_project_id = new_project_id
        flag_modified(manifest, "restored_at")

        await db.commit()

        return {
            "success": True,
            "manifest_id": str(manifest.id),
            "new_project_id": str(new_project_id),
            "project_name": new_project.name,
            "agents_created": agents_created,
            "knowledge_bases": kbs_created,
            "connections_created": connections_created,
            "next_step": (
                "Skeleton is live. KB stubs are empty — re-upload "
                "documents with upload_to_kb. Mint fresh gateway keys "
                "with mint_gateway_key (old keys were revoked at delete)."
            ),
        }
