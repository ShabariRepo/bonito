"""Cost intelligence service — real multi-cloud cost aggregation.

Pulls real cost data from connected cloud providers, normalizes it,
and provides unified views, breakdowns, and forecasting.
Falls back to cached/empty data when providers aren't connected.

Caching strategy: 10-minute TTL with background preloading.
- On page load, always serve from Redis cache (instant)
- If cache miss, fetch from clouds and cache it
- Background refresh task keeps cache warm (runs every 8 min)
- Stale data served while refresh happens in background
"""

import asyncio
import json
import logging
import time
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_client
from app.models.cloud_provider import CloudProvider
from app.services.provider_service import (
    get_aws_provider,
    get_azure_provider,
    get_gcp_provider,
)
from app.schemas.cost import (
    CostSummary,
    CostBreakdownResponse,
    CostForecastResponse,
    DailyCost,
    ForecastPoint,
    ProviderCostBreakdown,
    ModelCostBreakdown,
    DepartmentCostBreakdown,
)

logger = logging.getLogger(__name__)

PROVIDER_COLORS = {"aws": "#FF9900", "azure": "#0078D4", "gcp": "#EA4335"}
COST_CACHE_TTL = 600  # 10 minutes
COST_STALE_TTL = 1800  # 30 minutes — serve stale data while refreshing
_refresh_lock = asyncio.Lock()  # Prevent concurrent refreshes


async def get_cost_summary_real(
    period: str, db: AsyncSession, budget: float = 40000.0, org_id=None,
    skip_cache: bool = False,
) -> CostSummary:
    """Get unified cost summary across all connected providers."""

    days = {"daily": 1, "weekly": 7, "monthly": 30}.get(period, 30)
    end = date.today()
    start = end - timedelta(days=days)

    # Check cache
    cache_key = f"costs:summary:{org_id}:{period}:{end.isoformat()}"
    if not skip_cache:
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                return CostSummary(**json.loads(cached))
        except Exception:
            pass

    result = await db.execute(
        select(CloudProvider).where(CloudProvider.status == "active", *([CloudProvider.org_id == org_id] if org_id else []))
    )
    providers = result.scalars().all()

    # Fetch current AND previous period in parallel for all providers
    prev_start = start - timedelta(days=days)

    async def _fetch(p, s, e):
        try:
            return p.provider_type, await _get_provider_costs(p, s, e)
        except Exception as ex:
            logger.warning(f"Cost pull failed for {p.provider_type}: {ex}")
            return p.provider_type, None

    tasks = []
    for p in providers:
        tasks.append(_fetch(p, start, end))       # current
        tasks.append(_fetch(p, prev_start, start)) # previous
    results = await asyncio.gather(*tasks)

    # Split results: even indices = current, odd = previous
    all_daily: dict[str, float] = {}
    prev_total = 0.0
    for i, (ptype, cost_data) in enumerate(results):
        if cost_data is None:
            continue
        if i % 2 == 0:  # current period
            for dc in cost_data.daily_costs:
                all_daily[dc.date] = all_daily.get(dc.date, 0) + dc.amount
        else:  # previous period
            prev_total += cost_data.total

    total = sum(all_daily.values())
    daily_costs = [
        DailyCost(date=d, amount=round(a, 2))
        for d, a in sorted(all_daily.items())
    ]

    change = ((total - prev_total) / prev_total * 100) if prev_total > 0 else 0

    summary = CostSummary(
        total_spend=round(total, 2),
        period=period,
        daily_costs=daily_costs,
        budget=budget,
        budget_used_percentage=round((total / budget * 100) if budget > 0 else 0, 1),
        change_percentage=round(change, 1),
    )

    # Cache
    try:
        await redis_client.setex(cache_key, COST_CACHE_TTL, summary.model_dump_json())
    except Exception:
        pass

    return summary


async def get_cost_breakdown_real(db: AsyncSession, org_id=None) -> CostBreakdownResponse:
    """Get cost breakdown by provider, model, and department."""
    end = date.today()
    start = end - timedelta(days=30)

    cache_key = f"costs:breakdown:{org_id}:{end.isoformat()}"
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            return CostBreakdownResponse(**json.loads(cached))
    except Exception:
        pass

    result = await db.execute(
        select(CloudProvider).where(CloudProvider.status == "active", *([CloudProvider.org_id == org_id] if org_id else []))
    )
    providers = result.scalars().all()

    provider_costs: dict[str, float] = {}
    service_costs: dict[str, list] = {}  # provider -> list of (service, amount)

    for p in providers:
        try:
            cost_data = await _get_provider_costs(p, start, end)
            provider_costs[p.provider_type] = cost_data.total

            # Group by service/usage_type for model breakdown
            svc_map: dict[str, float] = {}
            for dc in cost_data.daily_costs:
                key = dc.usage_type or dc.service or "General"
                svc_map[key] = svc_map.get(key, 0) + dc.amount
            service_costs[p.provider_type] = list(svc_map.items())
        except Exception as e:
            logger.warning(f"Cost breakdown failed for {p.provider_type}: {e}")

    grand = sum(provider_costs.values())

    by_provider = [
        ProviderCostBreakdown(
            provider=prov,
            total=round(total, 2),
            percentage=round((total / grand * 100) if grand > 0 else 0, 1),
            color=PROVIDER_COLORS.get(prov, "#666666"),
        )
        for prov, total in sorted(provider_costs.items(), key=lambda x: -x[1])
    ]

    by_model = []
    for prov, services in service_costs.items():
        for svc_name, amount in sorted(services, key=lambda x: -x[1])[:10]:
            by_model.append(ModelCostBreakdown(
                model=svc_name,
                provider=prov,
                total=round(amount, 2),
                requests=0,  # Not available from cost APIs
            ))
    by_model.sort(key=lambda x: -x.total)

    # Department attribution via team_id on gateway_requests.
    # GatewayKey.team_id propagates to GatewayRequest.team_id at request time.
    by_department: list[DepartmentCostBreakdown] = []
    try:
        from app.models.gateway import GatewayRequest
        from sqlalchemy import func as sa_func, and_

        dept_filters = [GatewayRequest.team_id.isnot(None)]
        if org_id:
            dept_filters.append(GatewayRequest.org_id == org_id)
        dept_filters.append(GatewayRequest.created_at >= start)

        dept_result = await db.execute(
            select(
                GatewayRequest.team_id,
                sa_func.sum(GatewayRequest.cost),
            )
            .where(and_(*dept_filters))
            .group_by(GatewayRequest.team_id)
            .order_by(sa_func.sum(GatewayRequest.cost).desc())
            .limit(20)
        )
        dept_rows = dept_result.all()
        dept_total = sum(r[1] or 0 for r in dept_rows) or 1
        for team_id, cost_sum in dept_rows:
            by_department.append(DepartmentCostBreakdown(
                department=team_id,
                total=round(cost_sum or 0, 2),
                percentage=round(((cost_sum or 0) / dept_total * 100), 1),
            ))
    except Exception:
        logger.exception("Failed to compute department cost attribution")

    breakdown = CostBreakdownResponse(
        by_provider=by_provider,
        by_model=by_model[:20],
        by_department=by_department,
        total=round(grand, 2),
    )

    try:
        await redis_client.setex(cache_key, COST_CACHE_TTL, breakdown.model_dump_json())
    except Exception:
        pass

    return breakdown


async def get_cost_forecast_real(db: AsyncSession, org_id=None) -> CostForecastResponse:
    """Forecast costs based on real historical data."""
    end = date.today()
    start = end - timedelta(days=30)

    result = await db.execute(
        select(CloudProvider).where(CloudProvider.status == "active", *([CloudProvider.org_id == org_id] if org_id else []))
    )
    providers = result.scalars().all()

    daily_totals: dict[str, float] = {}
    for p in providers:
        try:
            cost_data = await _get_provider_costs(p, start, end)
            for dc in cost_data.daily_costs:
                daily_totals[dc.date] = daily_totals.get(dc.date, 0) + dc.amount
        except Exception:
            pass

    sorted_days = sorted(daily_totals.items())
    amounts = [a for _, a in sorted_days]

    if not amounts:
        return CostForecastResponse(
            current_monthly_spend=0,
            projected_monthly_spend=0,
            forecast=[],
            savings_opportunity=0,
            trend="stable",
        )

    current_monthly = sum(amounts)
    avg_daily = sum(amounts) / len(amounts)

    # Linear regression for trend
    n = len(amounts)
    if n > 1:
        x_mean = (n - 1) / 2
        y_mean = avg_daily
        num = sum((i - x_mean) * (a - y_mean) for i, a in enumerate(amounts))
        den = sum((i - x_mean) ** 2 for i in range(n))
        slope = num / den if den != 0 else 0
    else:
        slope = 0

    projected = (avg_daily + slope * 15) * 30  # Project 15 days ahead

    # Generate forecast points
    forecast = []
    for i in range(1, 15):
        d = end + timedelta(days=i)
        proj = avg_daily + slope * (n + i)
        proj = max(proj, 0)
        forecast.append(ForecastPoint(
            date=d.isoformat(),
            projected=round(proj, 2),
            lower_bound=round(proj * 0.80, 2),
            upper_bound=round(proj * 1.20, 2),
        ))

    trend = "increasing" if slope > 1 else "decreasing" if slope < -1 else "stable"

    # Savings opportunity: estimate 10-15% from routing optimization
    savings = round(projected * 0.12, 2) if projected > 0 else 0

    return CostForecastResponse(
        current_monthly_spend=round(current_monthly, 2),
        projected_monthly_spend=round(projected, 2),
        forecast=forecast,
        savings_opportunity=savings,
        trend=trend,
    )


async def get_optimization_recommendations(db: AsyncSession, org_id=None) -> list[dict]:
    """Generate cost optimization recommendations based on real usage."""
    result = await db.execute(
        select(CloudProvider).where(CloudProvider.status == "active", *([CloudProvider.org_id == org_id] if org_id else []))
    )
    providers = result.scalars().all()

    recommendations = []

    for p in providers:
        try:
            if p.provider_type == "aws":
                prov = await get_aws_provider(str(p.id))
                models = await prov.list_models()
                # Find expensive models that have cheaper alternatives
                for m in models:
                    if m.input_price_per_1m_tokens > 10:
                        cheaper = [
                            alt for alt in models
                            if alt.input_price_per_1m_tokens < m.input_price_per_1m_tokens * 0.5
                            and "text" in alt.capabilities
                        ]
                        if cheaper:
                            best = min(cheaper, key=lambda x: x.input_price_per_1m_tokens)
                            savings_pct = round(
                                (1 - best.input_price_per_1m_tokens / m.input_price_per_1m_tokens) * 100
                            )
                            recommendations.append({
                                "type": "model_switch",
                                "severity": "medium",
                                "title": f"Switch from {m.model_name} to {best.model_name}",
                                "description": f"Save ~{savings_pct}% on input costs by using {best.model_name} for non-critical workloads",
                                "provider": "aws",
                                "estimated_savings_pct": savings_pct,
                            })
        except Exception as e:
            logger.warning(f"Optimization analysis failed for {p.provider_type}: {e}")

    # Cross-provider recommendations
    if len(providers) > 1:
        recommendations.append({
            "type": "cross_provider",
            "severity": "high",
            "title": "Enable cross-provider routing",
            "description": "Route requests to the cheapest provider automatically. Estimated 15-25% savings.",
            "estimated_savings_pct": 20,
        })

    if not recommendations:
        recommendations.append({
            "type": "info",
            "severity": "low",
            "title": "Connect cloud providers for recommendations",
            "description": "Connect your AWS, Azure, or GCP accounts to get personalized cost optimization recommendations.",
            "estimated_savings_pct": 0,
        })

    return recommendations


# ── Internal helpers ────────────────────────────────────────────


async def _get_provider_costs(provider: CloudProvider, start: date, end: date):
    """Get costs from a specific provider."""
    from app.services.providers.base import CostData

    cache_key = f"costs:{provider.provider_type}:{provider.id}:{start}:{end}"
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            data = json.loads(cached)
            return CostData(**data)
    except Exception:
        pass

    if provider.provider_type == "aws":
        prov = await get_aws_provider(str(provider.id))
    elif provider.provider_type == "azure":
        prov = await get_azure_provider(str(provider.id))
    elif provider.provider_type == "gcp":
        prov = await get_gcp_provider(str(provider.id))
    else:
        raise RuntimeError(f"Unknown provider: {provider.provider_type}")

    cost_data = await prov.get_costs(start, end)

    # Cache
    try:
        cache_val = json.dumps({
            "total": cost_data.total,
            "currency": cost_data.currency,
            "start_date": cost_data.start_date,
            "end_date": cost_data.end_date,
            "daily_costs": [
                {"date": dc.date, "amount": dc.amount, "currency": dc.currency,
                 "service": dc.service, "usage_type": dc.usage_type}
                for dc in cost_data.daily_costs
            ],
        })
        await redis_client.setex(cache_key, COST_CACHE_TTL, cache_val)
    except Exception:
        pass

    return cost_data


# ── Background cost preloader ──────────────────────────────────


async def preload_costs_for_org(db: AsyncSession, org_id) -> dict:
    """Preload all cost data into Redis for an org.
    
    Called on login, dashboard load, or by a periodic background task.
    Returns a summary of what was cached.
    """
    if _refresh_lock.locked():
        return {"status": "already_refreshing"}

    async with _refresh_lock:
        start_time = time.monotonic()
        results = {}

        try:
            # Preload summary for all periods
            for period in ("daily", "weekly", "monthly"):
                try:
                    await get_cost_summary_real(period, db, org_id=org_id, skip_cache=False)
                    results[f"summary_{period}"] = "ok"
                except Exception as e:
                    results[f"summary_{period}"] = f"error: {e}"

            # Preload breakdown
            try:
                await get_cost_breakdown_real(db, org_id=org_id)
                results["breakdown"] = "ok"
            except Exception as e:
                results["breakdown"] = f"error: {e}"

            # Preload forecast
            try:
                await get_cost_forecast_real(db, org_id=org_id)
                results["forecast"] = "ok"
            except Exception as e:
                results["forecast"] = f"error: {e}"

        except Exception as e:
            logger.exception(f"Cost preload failed for org {org_id}: {e}")
            results["error"] = str(e)

        elapsed = round(time.monotonic() - start_time, 2)
        results["elapsed_seconds"] = elapsed
        logger.info(f"Cost preload for org {org_id} completed in {elapsed}s: {results}")
        return results


async def trigger_background_refresh(db: AsyncSession, org_id) -> None:
    """Fire-and-forget cost refresh. Used after login or on dashboard load."""
    cache_key = f"costs:last_refresh:{org_id}"
    try:
        last = await redis_client.get(cache_key)
        if last and (time.time() - float(last)) < COST_CACHE_TTL * 0.8:
            return  # Recently refreshed, skip
    except Exception:
        pass

    async def _refresh():
        try:
            await preload_costs_for_org(db, org_id)
            try:
                await redis_client.setex(cache_key, COST_CACHE_TTL, str(time.time()))
            except Exception:
                pass
        except Exception:
            logger.exception(f"Background cost refresh failed for org {org_id}")

    asyncio.create_task(_refresh())


# ── Legacy sync API (fallback) ──────────────────────────────────


def get_cost_summary(period: str = "monthly") -> CostSummary:
    """Sync fallback — returns empty when no DB session."""
    return CostSummary(
        total_spend=0, period=period, daily_costs=[],
        budget=40000, budget_used_percentage=0, change_percentage=0,
    )


def get_cost_breakdown() -> CostBreakdownResponse:
    return CostBreakdownResponse(
        by_provider=[], by_model=[], by_department=[], total=0,
    )


def get_cost_forecast() -> CostForecastResponse:
    return CostForecastResponse(
        current_monthly_spend=0, projected_monthly_spend=0,
        forecast=[], savings_opportunity=0, trend="stable",
    )
