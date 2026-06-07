"""Origami admin routes — platform-admin visibility into customer usage.

Lets Shabari (or another platform admin) see who's using Origami, what
they're doing, from which org / project / user. Reads origami_turn_log
and origami_audit_log directly.

ALL routes here require platform-admin (super-admin) access, NOT just
org-admin. The data is cross-tenant by design.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_superadmin
from app.core.database import get_db
from app.models.user import User
from app.models.organization import Organization
from app.models.origami_logs import OrigamiAuditLog, OrigamiTurnLog


router = APIRouter(prefix="/admin/origami", tags=["origami-admin"])


@router.get("/usage-by-org")
async def usage_by_org(
    period: Optional[str] = Query(
        None,
        description="Billing period in YYYY-MM format. Defaults to current month.",
        regex=r"^\d{4}-\d{2}$",
    ),
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate Origami usage per org for a given billing period.

    Returns one row per (org, project) with turn count, total cost,
    token sums. Used by the platform-admin dashboard to see which
    customers are using Origami most heavily.
    """
    if not period:
        now = datetime.now(timezone.utc)
        period = f"{now.year:04d}-{now.month:02d}"

    result = await db.execute(
        select(
            OrigamiTurnLog.org_id,
            OrigamiTurnLog.project_id,
            func.count(OrigamiTurnLog.id).label("turn_count"),
            func.coalesce(func.sum(OrigamiTurnLog.cost_usd), 0).label("total_cost"),
            func.coalesce(func.sum(OrigamiTurnLog.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(OrigamiTurnLog.output_tokens), 0).label("output_tokens"),
            func.coalesce(func.sum(OrigamiTurnLog.tool_calls_count), 0).label("tool_calls"),
            func.count(OrigamiTurnLog.id).filter(
                OrigamiTurnLog.status == "success"
            ).label("success_count"),
            func.count(OrigamiTurnLog.id).filter(
                OrigamiTurnLog.status == "failed"
            ).label("failed_count"),
            func.count(OrigamiTurnLog.id).filter(
                OrigamiTurnLog.status == "over_quota"
            ).label("over_quota_count"),
        )
        .where(OrigamiTurnLog.billing_period_month == period)
        .group_by(OrigamiTurnLog.org_id, OrigamiTurnLog.project_id)
        .order_by(desc("total_cost"))
    )
    rows = list(result)

    # Attach org names for readability
    org_ids = list({r.org_id for r in rows})
    org_name_map: dict[uuid.UUID, str] = {}
    if org_ids:
        org_result = await db.execute(
            select(Organization.id, Organization.name).where(
                Organization.id.in_(org_ids)
            )
        )
        org_name_map = {row.id: row.name for row in org_result}

    return {
        "period": period,
        "orgs": [
            {
                "org_id": str(r.org_id),
                "org_name": org_name_map.get(r.org_id, "(unknown)"),
                "project_id": str(r.project_id) if r.project_id else None,
                "turn_count": int(r.turn_count or 0),
                "total_cost_usd": float(r.total_cost or 0),
                "input_tokens": int(r.input_tokens or 0),
                "output_tokens": int(r.output_tokens or 0),
                "tool_calls": int(r.tool_calls or 0),
                "success_count": int(r.success_count or 0),
                "failed_count": int(r.failed_count or 0),
                "over_quota_count": int(r.over_quota_count or 0),
            }
            for r in rows
        ],
        "totals": {
            "orgs_active": len(set(r.org_id for r in rows)),
            "total_turns": sum(int(r.turn_count or 0) for r in rows),
            "total_cogs_usd": round(sum(float(r.total_cost or 0) for r in rows), 4),
        },
    }


@router.get("/recent-activity")
async def recent_activity(
    limit: int = Query(50, ge=1, le=500),
    org_id: Optional[str] = Query(None, description="Filter to a single org"),
    project_id: Optional[str] = Query(None, description="Filter to a single project"),
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Live tail of recent Origami tool dispatches across all customers.

    Returns most-recent audit log entries (one per tool call) with full
    context: org, project, user, tool name, redacted params, status.
    """
    stmt = select(OrigamiAuditLog).order_by(desc(OrigamiAuditLog.created_at)).limit(limit)

    if org_id:
        try:
            stmt = stmt.where(OrigamiAuditLog.org_id == uuid.UUID(org_id))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="org_id must be a UUID")
    if project_id:
        try:
            stmt = stmt.where(OrigamiAuditLog.project_id == uuid.UUID(project_id))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="project_id must be a UUID")

    result = await db.execute(stmt)
    rows = list(result.scalars())

    return {
        "count": len(rows),
        "entries": [
            {
                "id": str(r.id),
                "org_id": str(r.org_id),
                "user_id": str(r.user_id),
                "project_id": str(r.project_id) if r.project_id else None,
                "session_id": str(r.session_id),
                "tool_name": r.tool_name,
                "tool_params": r.tool_params,  # already redacted at write time
                "intent_summary": r.intent_summary[:200] if r.intent_summary else None,
                "tier_at_time": r.tier_at_time,
                "confirmation": r.confirmation,
                "status": r.status,
                "error": r.error,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


@router.get("/turns")
async def list_turns(
    limit: int = Query(50, ge=1, le=500),
    org_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    period: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}$"),
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """List individual turn-log rows for fine-grained drill-down."""
    stmt = select(OrigamiTurnLog).order_by(desc(OrigamiTurnLog.created_at)).limit(limit)

    if org_id:
        try:
            stmt = stmt.where(OrigamiTurnLog.org_id == uuid.UUID(org_id))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="org_id must be a UUID")
    if project_id:
        try:
            stmt = stmt.where(OrigamiTurnLog.project_id == uuid.UUID(project_id))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="project_id must be a UUID")
    if period:
        stmt = stmt.where(OrigamiTurnLog.billing_period_month == period)

    result = await db.execute(stmt)
    rows = list(result.scalars())

    return {
        "count": len(rows),
        "entries": [
            {
                "id": str(r.id),
                "org_id": str(r.org_id),
                "user_id": str(r.user_id),
                "project_id": str(r.project_id) if r.project_id else None,
                "session_id": str(r.session_id),
                "conversation_id": r.conversation_id,
                "user_message_preview": r.user_message_preview,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "cost_usd": float(r.cost_usd) if r.cost_usd is not None else 0,
                "tool_calls_count": r.tool_calls_count,
                "model_used": r.model_used,
                "status": r.status,
                "finish_reason": r.finish_reason,
                "billing_period_month": r.billing_period_month,
                "tier_at_time": r.tier_at_time,
                "duration_ms": r.duration_ms,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }
