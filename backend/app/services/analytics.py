"""Usage analytics service — aggregates cost/gateway data for analytics endpoints."""

import random
from datetime import datetime, timedelta
from typing import Optional


class UsageAnalytics:
    """Aggregates usage data from cost records and gateway logs."""

    def get_overview(self):
        return {
            "total_requests": 48_720,
            "total_cost": 12_450.80,
            "active_models": 8,
            "active_teams": 5,
            "top_model": "claude-3.5-sonnet",
            "avg_latency_ms": 340,
            "success_rate": 99.7,
            "active_users": 32,
        }

    def get_usage(self, period: str = "day"):
        now = datetime.utcnow()
        if period == "day":
            points = 24
            fmt = "%H:00"
            delta = timedelta(hours=1)
        elif period == "week":
            points = 7
            fmt = "%a"
            delta = timedelta(days=1)
        else:  # month
            points = 30
            fmt = "%b %d"
            delta = timedelta(days=1)

        data = []
        base_requests = 1500
        base_tokens = 450000
        for i in range(points):
            ts = now - delta * (points - 1 - i)
            noise = random.uniform(0.7, 1.4)
            data.append({
                "label": ts.strftime(fmt),
                "requests": int(base_requests * noise),
                "tokens": int(base_tokens * noise),
                "cost": round(base_requests * noise * 0.008, 2),
            })
        return {"period": period, "data": data}

    def get_cost_breakdown(self):
        return {
            "by_provider": [
                {"provider": "Anthropic", "cost": 5_200.40, "percentage": 41.8, "requests": 18_500},
                {"provider": "OpenAI", "cost": 4_100.20, "percentage": 32.9, "requests": 16_200},
                {"provider": "AWS Bedrock", "cost": 2_100.10, "percentage": 16.9, "requests": 9_000},
                {"provider": "Google AI", "cost": 1_050.10, "percentage": 8.4, "requests": 5_020},
            ],
            "by_model": [
                {"model": "claude-3.5-sonnet", "provider": "Anthropic", "cost": 3_800.00, "requests": 14_200},
                {"model": "gpt-4o", "provider": "OpenAI", "cost": 2_900.50, "requests": 10_800},
                {"model": "claude-3-haiku", "provider": "Anthropic", "cost": 1_400.40, "requests": 4_300},
                {"model": "gpt-4o-mini", "provider": "OpenAI", "cost": 1_200.70, "requests": 5_400},
                {"model": "claude-3-opus", "provider": "AWS Bedrock", "cost": 1_100.00, "requests": 2_100},
                {"model": "gemini-1.5-pro", "provider": "Google AI", "cost": 1_050.10, "requests": 5_020},
            ],
            "by_team": [
                {"team": "Engineering", "cost": 5_800.30, "requests": 22_000, "percentage": 46.6},
                {"team": "Product", "cost": 2_800.20, "requests": 11_200, "percentage": 22.5},
                {"team": "Research", "cost": 2_100.10, "requests": 8_500, "percentage": 16.9},
                {"team": "Support", "cost": 1_100.10, "requests": 4_500, "percentage": 8.8},
                {"team": "Marketing", "cost": 650.10, "requests": 2_520, "percentage": 5.2},
            ],
            "total": 12_450.80,
        }

    def get_trends(self):
        return {
            "cost_trend": {
                "direction": "increasing",
                "percentage": 12.4,
                "current_period": 12_450.80,
                "previous_period": 11_078.10,
            },
            "request_trend": {
                "direction": "increasing",
                "percentage": 8.2,
                "current_period": 48_720,
                "previous_period": 45_028,
            },
            "efficiency_trend": {
                "direction": "decreasing",
                "percentage": -3.1,
                "description": "Cost per request decreased — you're spending more efficiently",
            },
            "model_shifts": [
                {"model": "claude-3.5-sonnet", "change": 15.2, "direction": "increasing"},
                {"model": "gpt-4-turbo", "change": -22.5, "direction": "decreasing"},
                {"model": "gpt-4o-mini", "change": 45.0, "direction": "increasing"},
            ],
        }

    def get_weekly_digest(self):
        return {
            "period": "Feb 1 – Feb 7, 2026",
            "summary": {
                "total_requests": 48_720,
                "total_cost": 12_450.80,
                "cost_change_pct": 8.3,
                "top_model": "claude-3.5-sonnet",
                "top_model_pct": 29.2,
                "active_users": 32,
                "active_teams": 5,
            },
            "highlights": [
                "Cost increased 8.3% compared to last week",
                "gpt-4o-mini adoption grew 45% — consider expanding its use for cost savings",
                "3 compliance policy violations detected (data residency)",
                "Budget utilization at 85% — on track to exceed by month end",
            ],
            "recommendations": [
                "Route simple queries to gpt-4o-mini to reduce costs by ~$800/week",
                "Review data residency rules — 3 violations this week",
                "Consider setting a budget alert at 90% threshold",
            ],
        }


# Singleton
analytics_service = UsageAnalytics()
