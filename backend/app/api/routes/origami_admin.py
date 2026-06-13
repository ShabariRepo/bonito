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


@router.get("/billing")
async def studio_billing(
    period: Optional[str] = Query(
        None, description="Billing period YYYY-MM. Defaults to current month.",
        regex=r"^\d{4}-\d{2}$",
    ),
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Per-org Studio/Origami billing rollup for a period.

    For each org using Studio/Origami: turns used vs tier cap, over/under,
    overage turns + revenue, Bonito's REAL (cache-discounted) cost to serve,
    and the resulting margin. This is the "are we making money" view.

    cost_real_usd applies the prompt-cache discount (cached reads ~0.1x) using
    the per-turn cache token split — so it reflects the actual Bedrock/Anthropic
    bill, NOT the conservative full-price `cost_tracked_usd` that feeds the cap.
    """
    from app.services.origami.metering import (
        cache_aware_cost, get_turn_cap, get_overage_rate,
    )

    if not period:
        now = datetime.now(timezone.utc)
        period = f"{now.year:04d}-{now.month:02d}"

    # group by (org, model, tier) so cache-aware cost uses the right price
    result = await db.execute(
        select(
            OrigamiTurnLog.org_id,
            OrigamiTurnLog.model_used,
            OrigamiTurnLog.tier_at_time,
            func.count(OrigamiTurnLog.id).label("turns"),
            func.coalesce(func.sum(OrigamiTurnLog.input_tokens), 0).label("inp"),
            func.coalesce(func.sum(OrigamiTurnLog.output_tokens), 0).label("out"),
            func.coalesce(func.sum(OrigamiTurnLog.cache_read_tokens), 0).label("cr"),
            func.coalesce(func.sum(OrigamiTurnLog.cache_write_tokens), 0).label("cw"),
            func.coalesce(func.sum(OrigamiTurnLog.cost_usd), 0).label("tracked"),
        )
        .where(OrigamiTurnLog.billing_period_month == period)
        .group_by(OrigamiTurnLog.org_id, OrigamiTurnLog.model_used, OrigamiTurnLog.tier_at_time)
    )
    # roll up per org
    per_org: dict = {}
    for r in result:
        o = per_org.setdefault(str(r.org_id), {
            "turns": 0, "tracked": 0.0, "real": 0.0, "tier": r.tier_at_time or "free",
        })
        o["turns"] += int(r.turns or 0)
        o["tracked"] += float(r.tracked or 0)
        o["real"] += cache_aware_cost(
            r.model_used, int(r.inp or 0), int(r.out or 0),
            int(r.cr or 0), int(r.cw or 0),
        )
        # keep the highest tier seen (most generous cap)
        o["tier"] = r.tier_at_time or o["tier"]

    org_ids = [uuid.UUID(k) for k in per_org]
    names = {}
    if org_ids:
        nr = await db.execute(select(Organization.id, Organization.name).where(
            Organization.id.in_(org_ids)))
        names = {str(row.id): row.name for row in nr}

    orgs = []
    for oid, d in per_org.items():
        tier = d["tier"]
        cap = get_turn_cap(tier)
        cap_num = None if cap == float("inf") else int(cap)
        over = max(0, d["turns"] - cap_num) if cap_num is not None else 0
        rate = get_overage_rate(tier)
        overage_rev = round(over * rate, 2)
        real = round(d["real"], 4)
        orgs.append({
            "org_id": oid,
            "org_name": names.get(oid, "(unknown)"),
            "tier": tier,
            "turns_used": d["turns"],
            "turn_cap": cap_num,
            "over_cap": cap_num is not None and d["turns"] > cap_num,
            "overage_turns": over,
            "overage_rate_usd": rate,
            "overage_revenue_usd": overage_rev,
            "cost_tracked_usd": round(d["tracked"], 4),   # full-price (cap basis)
            "cost_real_usd": real,                          # cache-discounted (true)
            "margin_usd": round(overage_rev - real, 4),
        })
    orgs.sort(key=lambda x: x["overage_revenue_usd"], reverse=True)

    return {
        "period": period,
        "orgs": orgs,
        "totals": {
            "orgs_using": len(orgs),
            "orgs_over_cap": sum(1 for o in orgs if o["over_cap"]),
            "total_turns": sum(o["turns_used"] for o in orgs),
            "total_overage_revenue_usd": round(sum(o["overage_revenue_usd"] for o in orgs), 2),
            "total_real_cost_usd": round(sum(o["cost_real_usd"] for o in orgs), 4),
            "total_tracked_cost_usd": round(sum(o["cost_tracked_usd"] for o in orgs), 4),
            "total_margin_usd": round(
                sum(o["overage_revenue_usd"] for o in orgs)
                - sum(o["cost_real_usd"] for o in orgs), 2),
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


@router.get("/launch-metrics")
async def launch_metrics(
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """One-call launch readiness snapshot for Phase 4 monitoring.

    Returns this-period vs. prior-period totals (turns, success rate,
    avg tool calls, unique orgs / users) plus a daily breakdown for
    sparklines and the top 10 tool names by call count.

    Designed for a single dashboard fetch — no parameters.
    """
    now = datetime.now(timezone.utc)
    this_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if this_start.month == 1:
        prior_start = this_start.replace(year=this_start.year - 1, month=12)
    else:
        prior_start = this_start.replace(month=this_start.month - 1)

    async def period_summary(start: datetime, end: datetime) -> dict:
        r = await db.execute(
            select(
                func.count(OrigamiTurnLog.id).label("total"),
                func.count(OrigamiTurnLog.id).filter(
                    OrigamiTurnLog.status == "success"
                ).label("success"),
                func.coalesce(func.sum(OrigamiTurnLog.tool_calls_count), 0).label("tools"),
                func.coalesce(func.sum(OrigamiTurnLog.cost_usd), 0).label("cost"),
                func.count(func.distinct(OrigamiTurnLog.org_id)).label("orgs"),
                func.count(func.distinct(OrigamiTurnLog.user_id)).label("users"),
            )
            .where(
                OrigamiTurnLog.created_at >= start,
                OrigamiTurnLog.created_at < end,
            )
        )
        row = r.one()
        total = int(row.total or 0)
        success = int(row.success or 0)
        return {
            "total_turns": total,
            "success_count": success,
            "success_rate": round(success / total, 4) if total else 0.0,
            "tool_calls_total": int(row.tools or 0),
            "avg_tool_calls_per_turn": round(int(row.tools or 0) / total, 2) if total else 0.0,
            "total_cost_usd": round(float(row.cost or 0), 4),
            "unique_orgs": int(row.orgs or 0),
            "unique_users": int(row.users or 0),
        }

    this_period = await period_summary(this_start, now)
    prior_period = await period_summary(prior_start, this_start)

    # Daily breakdown of this period (for sparkline)
    daily = await db.execute(
        select(
            func.date_trunc("day", OrigamiTurnLog.created_at).label("day"),
            func.count(OrigamiTurnLog.id).label("turns"),
        )
        .where(OrigamiTurnLog.created_at >= this_start)
        .group_by("day")
        .order_by("day")
    )
    daily_series = [
        {"day": row.day.date().isoformat(), "turns": int(row.turns)}
        for row in daily.all()
    ]

    # Top tools by call count this period
    top_tools = await db.execute(
        select(
            OrigamiAuditLog.tool_name,
            func.count(OrigamiAuditLog.id).label("calls"),
            func.count(OrigamiAuditLog.id).filter(
                OrigamiAuditLog.status == "success"
            ).label("success"),
        )
        .where(OrigamiAuditLog.created_at >= this_start)
        .group_by(OrigamiAuditLog.tool_name)
        .order_by(desc("calls"))
        .limit(10)
    )
    top_tools_list = [
        {
            "tool_name": row.tool_name,
            "calls": int(row.calls),
            "success_count": int(row.success),
            "success_rate": round(int(row.success) / int(row.calls), 4) if row.calls else 0.0,
        }
        for row in top_tools.all()
    ]

    def growth(now: float, prev: float) -> Optional[float]:
        if prev == 0:
            return None
        return round((now - prev) / prev, 4)

    return {
        "this_period_start": this_start.isoformat(),
        "now": now.isoformat(),
        "this_period": this_period,
        "prior_period": prior_period,
        "growth": {
            "turns_pct": growth(this_period["total_turns"], prior_period["total_turns"]),
            "cost_pct": growth(this_period["total_cost_usd"], prior_period["total_cost_usd"]),
            "users_pct": growth(this_period["unique_users"], prior_period["unique_users"]),
            "orgs_pct": growth(this_period["unique_orgs"], prior_period["unique_orgs"]),
        },
        "daily_turns": daily_series,
        "top_tools": top_tools_list,
    }
