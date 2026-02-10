"""Cost intelligence service — real multi-cloud cost aggregation.

Pulls real cost data from connected cloud providers, normalizes it,
and provides unified views, breakdowns, and forecasting.
Falls back to cached/empty data when providers aren't connected.
"""

import json
import logging
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
COST_CACHE_TTL = 3600  # 1 hour


async def get_cost_summary_real(
    period: str, db: AsyncSession, budget: float = 40000.0
) -> CostSummary:
    """Get unified cost summary across all connected providers."""
    days = {"daily": 1, "weekly": 7, "monthly": 30}.get(period, 30)
    end = date.today()
    start = end - timedelta(days=days)

    # Check cache
    cache_key = f"costs:summary:{period}:{end.isoformat()}"
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            return CostSummary(**json.loads(cached))
    except Exception:
        pass

    # Pull real costs from all providers
    all_daily: dict[str, float] = {}  # date -> amount
    provider_totals: dict[str, float] = {}

    result = await db.execute(
        select(CloudProvider).where(CloudProvider.status == "active")
    )
    providers = result.scalars().all()

    for p in providers:
        try:
            cost_data = await _get_provider_costs(p, start, end)
            provider_totals[p.provider_type] = cost_data.total
            for dc in cost_data.daily_costs:
                all_daily[dc.date] = all_daily.get(dc.date, 0) + dc.amount
        except Exception as e:
            logger.warning(f"Cost pull failed for {p.provider_type}: {e}")

    total = sum(all_daily.values())
    daily_costs = [
        DailyCost(date=d, amount=round(a, 2))
        for d, a in sorted(all_daily.items())
    ]

    # Calculate change vs previous period
    prev_start = start - timedelta(days=days)
    prev_total = 0.0
    for p in providers:
        try:
            prev_data = await _get_provider_costs(p, prev_start, start)
            prev_total += prev_data.total
        except Exception:
            pass

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


async def get_cost_breakdown_real(db: AsyncSession) -> CostBreakdownResponse:
    """Get cost breakdown by provider, model, and department."""
    end = date.today()
    start = end - timedelta(days=30)

    cache_key = f"costs:breakdown:{end.isoformat()}"
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            return CostBreakdownResponse(**json.loads(cached))
    except Exception:
        pass

    result = await db.execute(
        select(CloudProvider).where(CloudProvider.status == "active")
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

    # TODO: Real department attribution requires team/project tagging on API keys.
    # Once API keys carry team_id or project_id, query gateway_requests grouped by
    # that tag to get actual per-department cost attribution.
    # For now, we skip the fake department breakdown — just show provider + model costs.
    by_department = []

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


async def get_cost_forecast_real(db: AsyncSession) -> CostForecastResponse:
    """Forecast costs based on real historical data."""
    end = date.today()
    start = end - timedelta(days=30)

    result = await db.execute(
        select(CloudProvider).where(CloudProvider.status == "active")
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


async def get_optimization_recommendations(db: AsyncSession) -> list[dict]:
    """Generate cost optimization recommendations based on real usage."""
    result = await db.execute(
        select(CloudProvider).where(CloudProvider.status == "active")
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
