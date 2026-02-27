"""
Billing Service - Per-org billing ledger and summary calculations.

Calculates platform subscription costs, managed inference spend,
agent counts, and total gateway usage for billing periods.
"""

import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.cloud_provider import CloudProvider
from app.models.gateway import GatewayRequest
from app.models.agent import Agent
from app.services.managed_inference import MARKUP_RATE

logger = logging.getLogger(__name__)

# Platform subscription pricing by tier (monthly)
TIER_PRICING = {
    "free": Decimal("0"),
    "pro": Decimal("499"),
    "enterprise": Decimal("2000"),
    "scale": Decimal("0"),  # custom pricing, tracked separately
}

# BonBon pricing per agent per month by tier
BONBON_PRICING = {
    "free": Decimal("0"),
    "pro": Decimal("199"),
    "enterprise": Decimal("399"),
    "scale": Decimal("399"),
}


def get_billing_period(ref_date: Optional[datetime] = None) -> tuple[datetime, datetime]:
    """Return (start, end) of the current calendar month billing period."""
    now = ref_date or datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # End is start of next month
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


async def get_org_billing(
    db: AsyncSession,
    org_id: uuid.UUID,
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
) -> dict:
    """Calculate full billing summary for a single org."""
    if not period_start or not period_end:
        period_start, period_end = get_billing_period()

    # Fetch org
    org_result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = org_result.scalar_one_or_none()
    if not org:
        return {"error": "Organization not found"}

    tier = org.subscription_tier or "free"

    # Platform subscription cost
    platform_cost = float(TIER_PRICING.get(tier, Decimal("0")))

    # Managed inference costs (sum of marked_up_cost from GatewayRequest where is_managed=True)
    managed_by_provider_result = await db.execute(
        select(
            GatewayRequest.provider,
            func.count(GatewayRequest.id).label("request_count"),
            func.coalesce(func.sum(GatewayRequest.cost), 0.0).label("base_cost"),
            func.coalesce(func.sum(GatewayRequest.marked_up_cost), 0.0).label("marked_up_cost"),
            func.coalesce(func.sum(GatewayRequest.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(GatewayRequest.output_tokens), 0).label("output_tokens"),
        ).where(
            and_(
                GatewayRequest.org_id == org_id,
                GatewayRequest.is_managed.is_(True),
                GatewayRequest.status == "success",
                GatewayRequest.created_at >= period_start,
                GatewayRequest.created_at < period_end,
            )
        ).group_by(GatewayRequest.provider)
    )
    managed_by_provider = []
    total_managed_cost = 0.0
    total_managed_markup = 0.0
    for row in managed_by_provider_result.all():
        base = float(row.base_cost)
        marked = float(row.marked_up_cost)
        markup = marked - base
        total_managed_cost += marked
        total_managed_markup += markup
        managed_by_provider.append({
            "provider": row.provider or "unknown",
            "request_count": row.request_count,
            "base_cost": round(base, 4),
            "marked_up_cost": round(marked, 4),
            "markup_amount": round(markup, 4),
            "input_tokens": int(row.input_tokens),
            "output_tokens": int(row.output_tokens),
        })

    # Total gateway requests (all, including BYOK)
    gateway_totals_result = await db.execute(
        select(
            func.count(GatewayRequest.id).label("total_requests"),
            func.coalesce(func.sum(GatewayRequest.cost), 0.0).label("total_cost"),
            func.coalesce(func.sum(GatewayRequest.input_tokens), 0).label("total_input_tokens"),
            func.coalesce(func.sum(GatewayRequest.output_tokens), 0).label("total_output_tokens"),
        ).where(
            and_(
                GatewayRequest.org_id == org_id,
                GatewayRequest.status == "success",
                GatewayRequest.created_at >= period_start,
                GatewayRequest.created_at < period_end,
            )
        )
    )
    gw_row = gateway_totals_result.one()
    total_requests = gw_row.total_requests
    total_gateway_cost = float(gw_row.total_cost)

    # Active agents count
    agent_count_result = await db.execute(
        select(func.count(Agent.id)).where(
            and_(
                Agent.org_id == org_id,
                Agent.status == "active",
            )
        )
    )
    active_agent_count = agent_count_result.scalar() or 0

    # Agent billing (BonBon + Bonobot)
    bonbon_count = org.active_bonbon_count or 0
    bonobot_count = org.active_bonobot_count or 0
    bonbon_unit_price = float(BONBON_PRICING.get(tier, Decimal("0")))
    bonbon_cost = bonbon_count * bonbon_unit_price
    bonbon_monthly = float(org.bonbon_monthly_cost or 0)

    # Total monthly bill
    total_bill = platform_cost + total_managed_cost + bonbon_cost

    return {
        "org_id": str(org_id),
        "org_name": org.name,
        "tier": tier,
        "billing_period": {
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
        },
        "platform_subscription": {
            "tier": tier,
            "monthly_cost": platform_cost,
        },
        "managed_inference": {
            "total_cost": round(total_managed_cost, 4),
            "total_markup": round(total_managed_markup, 4),
            "markup_rate": MARKUP_RATE,
            "by_provider": managed_by_provider,
        },
        "agents": {
            "active_bonobot_count": active_agent_count,
            "active_bonbon_count": bonbon_count,
            "bonbon_unit_price": bonbon_unit_price,
            "bonbon_cost": round(bonbon_cost, 2),
        },
        "gateway_usage": {
            "total_requests": total_requests,
            "total_cost": round(total_gateway_cost, 4),
            "total_input_tokens": int(gw_row.total_input_tokens),
            "total_output_tokens": int(gw_row.total_output_tokens),
        },
        "total_bill": round(total_bill, 2),
    }


async def get_all_orgs_billing_summary(
    db: AsyncSession,
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
) -> dict:
    """Calculate billing summary across ALL orgs (admin god-mode view)."""
    if not period_start or not period_end:
        period_start, period_end = get_billing_period()

    # Fetch all orgs
    orgs_result = await db.execute(
        select(Organization).order_by(Organization.created_at.desc())
    )
    orgs = orgs_result.scalars().all()

    org_summaries = []
    total_platform_mrr = 0.0
    total_managed_revenue = 0.0
    total_bill_all = 0.0

    for org in orgs:
        billing = await get_org_billing(db, org.id, period_start, period_end)
        org_summaries.append(billing)
        total_platform_mrr += billing["platform_subscription"]["monthly_cost"]
        total_managed_revenue += billing["managed_inference"]["total_markup"]
        total_bill_all += billing["total_bill"]

    return {
        "billing_period": {
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
        },
        "total_orgs": len(orgs),
        "total_platform_mrr": round(total_platform_mrr, 2),
        "total_managed_inference_revenue": round(total_managed_revenue, 4),
        "total_bill": round(total_bill_all, 2),
        "organizations": org_summaries,
    }


async def get_enhanced_admin_stats(db: AsyncSession) -> dict:
    """Enhanced stats for admin dashboard, including managed inference
    revenue, tier breakdown, MRR, and top spenders."""
    period_start, period_end = get_billing_period()

    # Total managed inference revenue (sum of markups)
    managed_revenue_result = await db.execute(
        select(
            func.coalesce(
                func.sum(GatewayRequest.marked_up_cost) - func.sum(GatewayRequest.cost),
                0.0,
            ).label("total_markup")
        ).where(
            and_(
                GatewayRequest.is_managed.is_(True),
                GatewayRequest.status == "success",
                GatewayRequest.created_at >= period_start,
                GatewayRequest.created_at < period_end,
            )
        )
    )
    total_managed_markup = float(managed_revenue_result.scalar() or 0)

    # Active managed inference orgs (orgs with at least 1 managed request this month)
    active_managed_result = await db.execute(
        select(func.count(func.distinct(GatewayRequest.org_id))).where(
            and_(
                GatewayRequest.is_managed.is_(True),
                GatewayRequest.status == "success",
                GatewayRequest.created_at >= period_start,
                GatewayRequest.created_at < period_end,
            )
        )
    )
    active_managed_orgs = active_managed_result.scalar() or 0

    # Per-tier org counts
    tier_counts_result = await db.execute(
        select(
            Organization.subscription_tier,
            func.count(Organization.id),
        ).group_by(Organization.subscription_tier)
    )
    tier_counts = {row[0]: row[1] for row in tier_counts_result.all()}

    # Platform MRR (sum of tier pricing across all orgs)
    total_mrr = 0.0
    for tier_name, count in tier_counts.items():
        price = float(TIER_PRICING.get(tier_name, Decimal("0")))
        total_mrr += price * count

    # Top 5 orgs by spend this billing period
    top_spenders_result = await db.execute(
        select(
            Organization.id,
            Organization.name,
            Organization.subscription_tier,
            func.coalesce(func.sum(GatewayRequest.cost), 0.0).label("total_cost"),
            func.count(GatewayRequest.id).label("request_count"),
        )
        .join(GatewayRequest, GatewayRequest.org_id == Organization.id)
        .where(
            and_(
                GatewayRequest.created_at >= period_start,
                GatewayRequest.created_at < period_end,
                GatewayRequest.status == "success",
            )
        )
        .group_by(Organization.id, Organization.name, Organization.subscription_tier)
        .order_by(func.sum(GatewayRequest.cost).desc())
        .limit(5)
    )
    top_spenders = [
        {
            "org_id": str(row.id),
            "org_name": row.name,
            "tier": row.subscription_tier,
            "total_cost": round(float(row.total_cost), 4),
            "request_count": row.request_count,
        }
        for row in top_spenders_result.all()
    ]

    return {
        "managed_inference_revenue": round(total_managed_markup, 4),
        "active_managed_inference_orgs": active_managed_orgs,
        "tier_counts": tier_counts,
        "platform_mrr": round(total_mrr, 2),
        "top_spenders": top_spenders,
        "billing_period": {
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
        },
    }
