"""
Bonobot Projects API Routes

Project CRUD operations and project graph visualization
"""

from typing import List, Optional
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, aliased

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.organization import Organization
from app.models.project import Project
from app.models.agent import Agent
from app.models.agent_connection import AgentConnection
from app.models.agent_trigger import AgentTrigger
from app.schemas.bonobot import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectGraphResponse,
    GraphNode,
    GraphEdge
)

import logging
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List projects for the current organization."""
    # Get projects with agent count
    stmt = (
        select(
            Project,
            func.count(Agent.id).label("agent_count")
        )
        .outerjoin(Agent)
        .where(Project.org_id == current_user.org_id)
        .group_by(Project.id)
        .order_by(Project.created_at.desc())
    )
    
    result = await db.execute(stmt)
    projects_with_counts = result.all()
    
    response = []
    for project, agent_count in projects_with_counts:
        project_data = ProjectResponse.model_validate(project)
        project_data.agent_count = agent_count
        response.append(project_data)
    
    return response


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new project."""
    # Feature gate: check bonobot_plan
    stmt = select(Organization).where(Organization.id == current_user.org_id)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    
    if not org or org.bonobot_plan == "none":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Bonobot agents require a Pro or Enterprise plan. Upgrade at getbonito.com/pricing",
                "required_tier": "pro",
                "upgrade_url": "https://getbonito.com/pricing"
            }
        )
    
    project = Project(
        org_id=current_user.org_id,
        name=project_data.name,
        description=project_data.description,
        budget_monthly=project_data.budget_monthly,
        settings=project_data.settings or {}
    )
    
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    return ProjectResponse.model_validate(project)


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get project details."""
    stmt = select(Project).where(
        and_(
            Project.id == project_id,
            Project.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Get agent count
    stmt = select(func.count(Agent.id)).where(Agent.project_id == project_id)
    result = await db.execute(stmt)
    agent_count = result.scalar()
    
    project_data = ProjectResponse.model_validate(project)
    project_data.agent_count = agent_count
    
    return project_data


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update project."""
    stmt = select(Project).where(
        and_(
            Project.id == project_id,
            Project.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Update fields
    update_data = project_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    await db.commit()
    await db.refresh(project)
    
    return ProjectResponse.model_validate(project)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    hard: bool = False,
    delete_kb_ids: str | None = None,
    delete_gateway_key_ids: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a project.

    Default mode (hard=False): SOFT delete — sets status to 'archived'.
    Hard mode (hard=True): admin-only. Drops the project row, which
    cascades agents, connections, schedules, project tokens via FK rules.
    Also drops any KBs / gateway keys explicitly listed in
    `delete_kb_ids` and `delete_gateway_key_ids` (comma-separated UUIDs).
    """
    stmt = select(Project).where(
        and_(
            Project.id == project_id,
            Project.org_id == current_user.org_id,
        )
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if hard:
        if getattr(current_user, "role", None) != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Hard delete requires org admin.",
            )

        from app.models.knowledge_base import KnowledgeBase
        from app.models.gateway import GatewayKey
        from sqlalchemy import delete as sa_delete

        # Opt-in KB deletion
        if delete_kb_ids:
            ids: list[uuid.UUID] = []
            for raw in delete_kb_ids.split(","):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    ids.append(uuid.UUID(raw))
                except ValueError:
                    continue
            if ids:
                # Use raw delete to skip pgvector ARRAY coercion errors
                # (matches the KB delete fix from commit 43040-43042)
                from app.models.knowledge_base import KBChunk, KBDocument
                await db.execute(
                    sa_delete(KBChunk).where(
                        KBChunk.knowledge_base_id.in_(ids),
                        KBChunk.org_id == current_user.org_id,
                    )
                )
                await db.execute(
                    sa_delete(KBDocument).where(
                        KBDocument.knowledge_base_id.in_(ids),
                        KBDocument.org_id == current_user.org_id,
                    )
                )
                await db.execute(
                    sa_delete(KnowledgeBase).where(
                        KnowledgeBase.id.in_(ids),
                        KnowledgeBase.org_id == current_user.org_id,
                    )
                )

        # Opt-in gateway-key revocation
        if delete_gateway_key_ids:
            ids = []
            for raw in delete_gateway_key_ids.split(","):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    ids.append(uuid.UUID(raw))
                except ValueError:
                    continue
            if ids:
                await db.execute(
                    sa_delete(GatewayKey).where(
                        GatewayKey.id.in_(ids),
                        GatewayKey.org_id == current_user.org_id,
                    )
                )

        await db.delete(project)
        await db.commit()
        return

    # Soft delete (default — unchanged)
    project.status = "archived"
    await db.commit()


@router.get("/projects/{project_id}/delete-preview")
async def delete_preview(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Show what would be deleted on a hard-delete of this project.

    Splits resources into TWO buckets:
    - cascade: rows that auto-delete via FK rules (agents, connections,
      project tokens, etc.) — admin only needs to confirm.
    - opt_in: org-level rows that survive the project delete (KBs,
      gateway keys) — admin can explicitly pick which to remove.
    """
    from app.models.knowledge_base import KnowledgeBase
    from app.models.gateway import GatewayKey
    from app.models.agent_group import AgentGroup
    from app.models.agent_schedule import AgentSchedule
    from app.models.access_token import AccessToken
    from sqlalchemy import func

    stmt = select(Project).where(
        Project.id == project_id, Project.org_id == current_user.org_id
    )
    project = (await db.execute(stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    async def _count(model, *filters) -> int:
        r = await db.execute(select(func.count(model.id)).where(*filters))
        return int(r.scalar_one() or 0)

    agents_count = await _count(
        Agent, Agent.project_id == project_id, Agent.org_id == current_user.org_id
    )
    connections_count = await _count(
        AgentConnection,
        AgentConnection.project_id == project_id,
        AgentConnection.org_id == current_user.org_id,
    )
    groups_count = await _count(
        AgentGroup,
        AgentGroup.project_id == project_id,
        AgentGroup.org_id == current_user.org_id,
    )
    schedules_count = await _count(
        AgentSchedule,
        AgentSchedule.project_id == project_id,
        AgentSchedule.org_id == current_user.org_id,
    )
    project_tokens_count = await _count(
        AccessToken,
        AccessToken.project_id == project_id,
        AccessToken.org_id == current_user.org_id,
        AccessToken.token_type == "project",
        AccessToken.revoked_at.is_(None),
    )

    # KBs tagged with this project_id in source_config
    kb_rows = (await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.org_id == current_user.org_id)
    )).scalars().all()
    associated_kbs = [
        {"id": str(kb.id), "name": kb.name, "status": kb.status}
        for kb in kb_rows
        if isinstance(kb.source_config, dict)
        and kb.source_config.get("project_id") == str(project_id)
    ]

    # Gateway keys with the project name in their display name (best-effort)
    gk_rows = (await db.execute(
        select(GatewayKey).where(
            GatewayKey.org_id == current_user.org_id,
            GatewayKey.revoked_at.is_(None),
        )
    )).scalars().all()
    associated_gateway_keys = [
        {"id": str(gk.id), "name": gk.name, "key_prefix": gk.key_prefix}
        for gk in gk_rows
        if project.name.lower() in (gk.name or "").lower()
    ]

    return {
        "project": {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
        },
        "cascade": {
            "agents": agents_count,
            "agent_connections": connections_count,
            "agent_groups": groups_count,
            "agent_schedules": schedules_count,
            "project_tokens": project_tokens_count,
        },
        "opt_in": {
            "knowledge_bases": associated_kbs,
            "gateway_keys": associated_gateway_keys,
        },
        "requires_admin": True,
    }


@router.get("/projects/{project_id}/graph", response_model=ProjectGraphResponse)
async def get_project_graph(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get project graph data for React Flow visualization."""
    # Verify project exists and user has access
    stmt = select(Project).where(
        and_(
            Project.id == project_id,
            Project.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Get agents
    stmt = select(Agent).where(Agent.project_id == project_id)
    result = await db.execute(stmt)
    agents = result.scalars().all()
    
    # Get triggers
    stmt = (
        select(AgentTrigger, Agent.name.label("agent_name"))
        .join(Agent)
        .where(Agent.project_id == project_id)
    )
    result = await db.execute(stmt)
    triggers_with_agents = result.all()
    
    # Get connections (alias Agent to avoid duplicate join error)
    SourceAgent = aliased(Agent, name="source_agent")
    TargetAgent = aliased(Agent, name="target_agent")
    stmt = (
        select(
            AgentConnection,
            SourceAgent.name.label("source_agent_name"),
            TargetAgent.name.label("target_agent_name")
        )
        .join(SourceAgent, AgentConnection.source_agent_id == SourceAgent.id)
        .join(TargetAgent, AgentConnection.target_agent_id == TargetAgent.id, isouter=True)
        .where(AgentConnection.project_id == project_id)
    )
    result = await db.execute(stmt)
    connections = result.all()
    
    # Build nodes
    nodes = []
    
    # Agent nodes
    for idx, agent in enumerate(agents):
        node_data = {
            "id": str(agent.id),
            "name": agent.name,
            "description": agent.description,
            "status": agent.status,
            "model_id": agent.model_id,
            "knowledge_base_count": len(agent.knowledge_base_ids) if agent.knowledge_base_ids else 0,
            "total_runs": agent.total_runs,
            "total_cost": float(agent.total_cost),
            "last_active_at": agent.last_active_at.isoformat() if agent.last_active_at else None,
        }
        
        nodes.append(GraphNode(
            id=agent.id,
            type="agent",
            data=node_data,
            position=agent.canvas_position or {"x": 100 + (idx % 4) * 300, "y": 100 + (idx // 4) * 200}
        ))
    
    # Trigger nodes - spread in a column to the left of agent nodes
    for t_idx, (trigger, agent_name) in enumerate(triggers_with_agents):
        node_data = {
            "id": str(trigger.id),
            "trigger_type": trigger.trigger_type,
            "config": trigger.config,
            "enabled": trigger.enabled,
            "agent_name": agent_name,
            "last_fired_at": trigger.last_fired_at.isoformat() if trigger.last_fired_at else None,
        }
        
        trigger_position = getattr(trigger, "canvas_position", None) or {
            "x": 50,
            "y": 100 + t_idx * 150,
        }
        
        nodes.append(GraphNode(
            id=trigger.id,
            type="trigger",
            data=node_data,
            position=trigger_position,
        ))
    
    # Build edges
    edges = []
    
    # Connection edges
    for connection, source_name, target_name in connections:
        edge_data = {
            "connection_type": connection.connection_type,
            "label": connection.label or connection.connection_type,
            "enabled": connection.enabled,
            "source_name": source_name,
            "target_name": target_name,
        }
        
        edges.append(GraphEdge(
            id=connection.id,
            source=connection.source_agent_id,
            target=connection.target_agent_id,
            type="connection",
            data=edge_data
        ))
    
    # Trigger edges (trigger → agent)
    for trigger, agent_name in triggers_with_agents:
        edge_data = {
            "trigger_type": trigger.trigger_type,
            "label": trigger.trigger_type,
            "enabled": trigger.enabled,
        }
        
        edges.append(GraphEdge(
            id=uuid.uuid5(uuid.NAMESPACE_DNS, f"trigger-edge-{trigger.id}"),
            source=trigger.id,
            target=trigger.agent_id,
            type="trigger",
            data=edge_data
        ))
    
    return ProjectGraphResponse(
        project_id=project_id,
        nodes=nodes,
        edges=edges
    )


# ───────────────────────── Deleted projects / restore ─────────────────────
#
# Backs the /agents page "Deleted" tab. Lets org admins browse their
# deleted-project manifests and restore the skeleton with one click —
# same code path as the restore_project Origami tool.


@router.get("/projects/deleted")
async def list_deleted_projects_api(
    include_restored: bool = False,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List ProjectManifest rows for the user's org.

    Used by the Projects page "Deleted" tab. Org-scoped, admin-only.
    """
    from app.models.project_manifest import ProjectManifest

    if getattr(current_user, "role", None) != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only org admins can view deleted-project manifests.",
        )

    limit = max(1, min(limit, 200))
    stmt = select(ProjectManifest).where(
        ProjectManifest.org_id == current_user.org_id
    )
    if not include_restored:
        stmt = stmt.where(ProjectManifest.restored_at.is_(None))
    stmt = stmt.order_by(ProjectManifest.deleted_at.desc()).limit(limit)

    rows = (await db.execute(stmt)).scalars().all()
    return {
        "count": len(rows),
        "manifests": [
            {
                "manifest_id": str(m.id),
                "project_name": m.project_name,
                "description": m.description,
                "deleted_at": m.deleted_at.isoformat() if m.deleted_at else None,
                "deleted_by_user_id": str(m.deleted_by_user_id) if m.deleted_by_user_id else None,
                "restored": m.restored_at is not None,
                "restored_at": m.restored_at.isoformat() if m.restored_at else None,
                "restored_to_project_id": (
                    str(m.restored_to_project_id) if m.restored_to_project_id else None
                ),
                "agent_count": len((m.manifest or {}).get("agents", [])),
                "connection_count": len((m.manifest or {}).get("connections", [])),
                "kb_count": len((m.manifest or {}).get("knowledge_bases", [])),
            }
            for m in rows
        ],
    }


@router.post("/projects/deleted/{manifest_id}/restore")
async def restore_from_manifest_api(
    manifest_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Restore a project from its manifest (UI-facing wrapper).

    Calls the same logic as the Origami restore_project tool — admin
    only, returns the new project_id + counts of what got rebuilt.
    """
    if getattr(current_user, "role", None) != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only org admins can restore projects.",
        )

    from app.services.origami.tools.restore_project import RestoreProjectTool

    result = await RestoreProjectTool().execute(
        org_id=current_user.org_id,
        user=current_user,
        params={"manifest_id": str(manifest_id)},
        db=db,
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message") or "Restore failed.",
        )
    return result