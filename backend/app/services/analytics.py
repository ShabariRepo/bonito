"""Usage analytics service — aggregates real cost/gateway data for analytics endpoints."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func, cast, Date, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gateway import GatewayRequest


class UsageAnalytics:
    """Aggregates usage data from gateway_requests table."""

    async def get_overview(self, db: AsyncSession, org_id) -> dict:
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        # Total requests + cost + avg latency + success rate in the last 30 days
        stats = await db.execute(
            select(
                func.count(GatewayRequest.id).label("total_requests"),
                func.coalesce(func.sum(GatewayRequest.cost), 0).label("total_cost"),
                func.coalesce(func.avg(GatewayRequest.latency_ms), 0).label("avg_latency_ms"),
            ).where(
                GatewayRequest.org_id == org_id,
                GatewayRequest.created_at >= thirty_days_ago,
            )
        )
        row = stats.one()
        total_requests = row.total_requests or 0
        total_cost = float(row.total_cost or 0)
        avg_latency = round(float(row.avg_latency_ms or 0), 1)

        # Success rate
        if total_requests > 0:
            success_count = await db.execute(
                select(func.count(GatewayRequest.id)).where(
                    GatewayRequest.org_id == org_id,
                    GatewayRequest.created_at >= thirty_days_ago,
                    GatewayRequest.status == "success",
                )
            )
            success_rate = round(success_count.scalar_one() / total_requests * 100, 1)
        else:
            success_rate = 0.0

        # Active (distinct) models
        active_models_q = await db.execute(
            select(func.count(func.distinct(GatewayRequest.model_used))).where(
                GatewayRequest.org_id == org_id,
                GatewayRequest.created_at >= thirty_days_ago,
                GatewayRequest.model_used.isnot(None),
            )
        )
        active_models = active_models_q.scalar_one() or 0

        # Active users
        active_users_q = await db.execute(
            select(func.count(func.distinct(GatewayRequest.user_id))).where(
                GatewayRequest.org_id == org_id,
                GatewayRequest.created_at >= thirty_days_ago,
                GatewayRequest.user_id.isnot(None),
            )
        )
        active_users = active_users_q.scalar_one() or 0

        # Active teams
        active_teams_q = await db.execute(
            select(func.count(func.distinct(GatewayRequest.team_id))).where(
                GatewayRequest.org_id == org_id,
                GatewayRequest.created_at >= thirty_days_ago,
                GatewayRequest.team_id.isnot(None),
            )
        )
        active_teams = active_teams_q.scalar_one() or 0

        # Top model by request count
        top_model_q = await db.execute(
            select(
                GatewayRequest.model_used,
                func.count(GatewayRequest.id).label("cnt"),
            ).where(
                GatewayRequest.org_id == org_id,
                GatewayRequest.created_at >= thirty_days_ago,
                GatewayRequest.model_used.isnot(None),
            ).group_by(GatewayRequest.model_used)
            .order_by(func.count(GatewayRequest.id).desc())
            .limit(1)
        )
        top_row = top_model_q.first()
        top_model = top_row[0] if top_row else None

        return {
            "total_requests": total_requests,
            "total_cost": round(total_cost, 2),
            "active_models": active_models,
            "active_teams": active_teams,
            "top_model": top_model,
            "avg_latency_ms": avg_latency,
            "success_rate": success_rate,
            "active_users": active_users,
        }

    async def get_usage(self, db: AsyncSession, org_id, period: str = "day") -> dict:
        now = datetime.now(timezone.utc)
        if period == "day":
            start = now - timedelta(hours=24)
        elif period == "week":
            start = now - timedelta(days=7)
        else:  # month
            start = now - timedelta(days=30)

        # Group by date (day-level granularity for week/month, hour-level for day)
        if period == "day":
            # Group by hour
            # Use date_trunc-style grouping via extract
            rows = await db.execute(
                select(
                    func.date_trunc("hour", GatewayRequest.created_at).label("bucket"),
                    func.count(GatewayRequest.id).label("requests"),
                    func.coalesce(func.sum(GatewayRequest.input_tokens + GatewayRequest.output_tokens), 0).label("tokens"),
                    func.coalesce(func.sum(GatewayRequest.cost), 0).label("cost"),
                ).where(
                    GatewayRequest.org_id == org_id,
                    GatewayRequest.created_at >= start,
                ).group_by("bucket")
                .order_by("bucket")
            )
            data = []
            for row in rows:
                data.append({
                    "label": row.bucket.strftime("%H:00") if row.bucket else "",
                    "requests": row.requests,
                    "tokens": int(row.tokens),
                    "cost": round(float(row.cost), 2),
                })
        else:
            # Group by day
            rows = await db.execute(
                select(
                    func.date_trunc("day", GatewayRequest.created_at).label("bucket"),
                    func.count(GatewayRequest.id).label("requests"),
                    func.coalesce(func.sum(GatewayRequest.input_tokens + GatewayRequest.output_tokens), 0).label("tokens"),
                    func.coalesce(func.sum(GatewayRequest.cost), 0).label("cost"),
                ).where(
                    GatewayRequest.org_id == org_id,
                    GatewayRequest.created_at >= start,
                ).group_by("bucket")
                .order_by("bucket")
            )
            fmt = "%a" if period == "week" else "%b %d"
            data = []
            for row in rows:
                data.append({
                    "label": row.bucket.strftime(fmt) if row.bucket else "",
                    "requests": row.requests,
                    "tokens": int(row.tokens),
                    "cost": round(float(row.cost), 2),
                })

        return {"period": period, "data": data}

    async def get_cost_breakdown(self, db: AsyncSession, org_id) -> dict:
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

        # By provider
        prov_rows = await db.execute(
            select(
                GatewayRequest.provider,
                func.coalesce(func.sum(GatewayRequest.cost), 0).label("cost"),
                func.count(GatewayRequest.id).label("requests"),
            ).where(
                GatewayRequest.org_id == org_id,
                GatewayRequest.created_at >= thirty_days_ago,
                GatewayRequest.provider.isnot(None),
            ).group_by(GatewayRequest.provider)
            .order_by(func.sum(GatewayRequest.cost).desc())
        )
        by_provider = []
        total = 0.0
        for row in prov_rows:
            cost_val = float(row.cost)
            total += cost_val
            by_provider.append({
                "provider": row.provider,
                "cost": round(cost_val, 2),
                "requests": row.requests,
            })
        # Add percentages
        for item in by_provider:
            item["percentage"] = round(item["cost"] / total * 100, 1) if total > 0 else 0

        # By model
        model_rows = await db.execute(
            select(
                GatewayRequest.model_used,
                GatewayRequest.provider,
                func.coalesce(func.sum(GatewayRequest.cost), 0).label("cost"),
                func.count(GatewayRequest.id).label("requests"),
            ).where(
                GatewayRequest.org_id == org_id,
                GatewayRequest.created_at >= thirty_days_ago,
                GatewayRequest.model_used.isnot(None),
            ).group_by(GatewayRequest.model_used, GatewayRequest.provider)
            .order_by(func.sum(GatewayRequest.cost).desc())
        )
        by_model = []
        for row in model_rows:
            by_model.append({
                "model": row.model_used,
                "provider": row.provider or "unknown",
                "cost": round(float(row.cost), 2),
                "requests": row.requests,
            })

        # By team (from team_id on gateway requests)
        team_rows = await db.execute(
            select(
                GatewayRequest.team_id,
                func.coalesce(func.sum(GatewayRequest.cost), 0).label("cost"),
                func.count(GatewayRequest.id).label("requests"),
            ).where(
                GatewayRequest.org_id == org_id,
                GatewayRequest.created_at >= thirty_days_ago,
                GatewayRequest.team_id.isnot(None),
            ).group_by(GatewayRequest.team_id)
            .order_by(func.sum(GatewayRequest.cost).desc())
        )
        by_team = []
        for row in team_rows:
            cost_val = float(row.cost)
            by_team.append({
                "team": row.team_id,
                "cost": round(cost_val, 2),
                "requests": row.requests,
                "percentage": round(cost_val / total * 100, 1) if total > 0 else 0,
            })

        return {
            "by_provider": by_provider,
            "by_model": by_model,
            "by_team": by_team,
            "total": round(total, 2),
        }

    async def get_trends(self, db: AsyncSession, org_id) -> dict:
        now = datetime.now(timezone.utc)
        current_start = now - timedelta(days=7)
        previous_start = now - timedelta(days=14)

        # Current week stats
        cur = await db.execute(
            select(
                func.count(GatewayRequest.id).label("requests"),
                func.coalesce(func.sum(GatewayRequest.cost), 0).label("cost"),
            ).where(
                GatewayRequest.org_id == org_id,
                GatewayRequest.created_at >= current_start,
            )
        )
        cur_row = cur.one()
        cur_requests = cur_row.requests or 0
        cur_cost = float(cur_row.cost or 0)

        # Previous week stats
        prev = await db.execute(
            select(
                func.count(GatewayRequest.id).label("requests"),
                func.coalesce(func.sum(GatewayRequest.cost), 0).label("cost"),
            ).where(
                GatewayRequest.org_id == org_id,
                GatewayRequest.created_at >= previous_start,
                GatewayRequest.created_at < current_start,
            )
        )
        prev_row = prev.one()
        prev_requests = prev_row.requests or 0
        prev_cost = float(prev_row.cost or 0)

        # Cost trend
        cost_pct = round(((cur_cost - prev_cost) / prev_cost * 100) if prev_cost > 0 else 0, 1)
        cost_direction = "increasing" if cost_pct > 0 else "decreasing" if cost_pct < 0 else "stable"

        # Request trend
        req_pct = round(((cur_requests - prev_requests) / prev_requests * 100) if prev_requests > 0 else 0, 1)
        req_direction = "increasing" if req_pct > 0 else "decreasing" if req_pct < 0 else "stable"

        # Efficiency: cost per request
        cur_cpr = cur_cost / cur_requests if cur_requests > 0 else 0
        prev_cpr = prev_cost / prev_requests if prev_requests > 0 else 0
        eff_pct = round(((cur_cpr - prev_cpr) / prev_cpr * 100) if prev_cpr > 0 else 0, 1)
        eff_dir = "increasing" if eff_pct > 0 else "decreasing" if eff_pct < 0 else "stable"
        eff_desc = "Cost per request decreased — spending more efficiently" if eff_pct < 0 else \
                   "Cost per request increased" if eff_pct > 0 else "Cost per request unchanged"

        # Model shifts: compare top models current vs previous week
        cur_models = await db.execute(
            select(
                GatewayRequest.model_used,
                func.count(GatewayRequest.id).label("cnt"),
            ).where(
                GatewayRequest.org_id == org_id,
                GatewayRequest.created_at >= current_start,
                GatewayRequest.model_used.isnot(None),
            ).group_by(GatewayRequest.model_used)
            .order_by(func.count(GatewayRequest.id).desc())
            .limit(10)
        )
        prev_models = await db.execute(
            select(
                GatewayRequest.model_used,
                func.count(GatewayRequest.id).label("cnt"),
            ).where(
                GatewayRequest.org_id == org_id,
                GatewayRequest.created_at >= previous_start,
                GatewayRequest.created_at < current_start,
                GatewayRequest.model_used.isnot(None),
            ).group_by(GatewayRequest.model_used)
        )
        cur_map = {r.model_used: r.cnt for r in cur_models}
        prev_map = {r.model_used: r.cnt for r in prev_models}

        model_shifts = []
        for model, cur_cnt in cur_map.items():
            prev_cnt = prev_map.get(model, 0)
            if prev_cnt > 0:
                change = round((cur_cnt - prev_cnt) / prev_cnt * 100, 1)
            elif cur_cnt > 0:
                change = 100.0
            else:
                change = 0.0
            model_shifts.append({
                "model": model,
                "change": change,
                "direction": "increasing" if change > 0 else "decreasing" if change < 0 else "stable",
            })
        model_shifts.sort(key=lambda x: abs(x["change"]), reverse=True)

        return {
            "cost_trend": {
                "direction": cost_direction,
                "percentage": cost_pct,
                "current_period": round(cur_cost, 2),
                "previous_period": round(prev_cost, 2),
            },
            "request_trend": {
                "direction": req_direction,
                "percentage": req_pct,
                "current_period": cur_requests,
                "previous_period": prev_requests,
            },
            "efficiency_trend": {
                "direction": eff_dir,
                "percentage": eff_pct,
                "description": eff_desc,
            },
            "model_shifts": model_shifts[:5],
        }

    async def get_weekly_digest(self, db: AsyncSession, org_id) -> dict:
        now = datetime.now(timezone.utc)
        week_start = now - timedelta(days=7)
        prev_week_start = now - timedelta(days=14)

        # Current week
        cur = await db.execute(
            select(
                func.count(GatewayRequest.id).label("requests"),
                func.coalesce(func.sum(GatewayRequest.cost), 0).label("cost"),
            ).where(
                GatewayRequest.org_id == org_id,
                GatewayRequest.created_at >= week_start,
            )
        )
        cur_row = cur.one()
        total_requests = cur_row.requests or 0
        total_cost = float(cur_row.cost or 0)

        # Previous week cost for change %
        prev = await db.execute(
            select(
                func.coalesce(func.sum(GatewayRequest.cost), 0).label("cost"),
            ).where(
                GatewayRequest.org_id == org_id,
                GatewayRequest.created_at >= prev_week_start,
                GatewayRequest.created_at < week_start,
            )
        )
        prev_cost = float(prev.scalar_one() or 0)
        cost_change = round(((total_cost - prev_cost) / prev_cost * 100) if prev_cost > 0 else 0, 1)

        # Top model
        top_q = await db.execute(
            select(
                GatewayRequest.model_used,
                func.count(GatewayRequest.id).label("cnt"),
            ).where(
                GatewayRequest.org_id == org_id,
                GatewayRequest.created_at >= week_start,
                GatewayRequest.model_used.isnot(None),
            ).group_by(GatewayRequest.model_used)
            .order_by(func.count(GatewayRequest.id).desc())
            .limit(1)
        )
        top_row = top_q.first()
        top_model = top_row[0] if top_row else None
        top_model_pct = round(top_row[1] / total_requests * 100, 1) if top_row and total_requests > 0 else 0

        # Active users/teams
        users_q = await db.execute(
            select(func.count(func.distinct(GatewayRequest.user_id))).where(
                GatewayRequest.org_id == org_id,
                GatewayRequest.created_at >= week_start,
                GatewayRequest.user_id.isnot(None),
            )
        )
        active_users = users_q.scalar_one() or 0

        teams_q = await db.execute(
            select(func.count(func.distinct(GatewayRequest.team_id))).where(
                GatewayRequest.org_id == org_id,
                GatewayRequest.created_at >= week_start,
                GatewayRequest.team_id.isnot(None),
            )
        )
        active_teams = teams_q.scalar_one() or 0

        period_str = f"{week_start.strftime('%b %d')} – {now.strftime('%b %d, %Y')}"

        return {
            "period": period_str,
            "summary": {
                "total_requests": total_requests,
                "total_cost": round(total_cost, 2),
                "cost_change_pct": cost_change,
                "top_model": top_model,
                "top_model_pct": top_model_pct,
                "active_users": active_users,
                "active_teams": active_teams,
            },
            "highlights": [],
            "recommendations": [],
        }


# Singleton
analytics_service = UsageAnalytics()
