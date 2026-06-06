"""view_usage — current period gateway-request usage + tier headroom.

Lightweight summary so Origami can tell users "you're using 12k of 100k
this month" without overloading the LLM context with full analytics.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.origami.tools.base import OrigamiTool, register_tool


@register_tool
class ViewUsageTool(OrigamiTool):
    name = "view_usage"
    description = (
        "Return current-month gateway request usage and tier limit headroom "
        "for the user's organization. Use this when the user asks about "
        "usage, cost, or whether they're close to a tier limit."
    )
    input_schema = {
        "type": "object",
        "properties": {},
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
        from app.services.feature_gate import feature_gate

        # First of current month, UTC
        now = datetime.now(timezone.utc)
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

        # Gateway request count this period — try GatewayLog if it exists,
        # fall back to 0 if the table isn't available.
        request_count = 0
        try:
            from app.models.gateway_log import GatewayLog

            result = await db.execute(
                select(func.count(GatewayLog.id)).where(
                    GatewayLog.org_id == org_id,
                    GatewayLog.created_at >= month_start,
                )
            )
            request_count = result.scalar_one() or 0
        except Exception:
            # TODO: replace with concrete log model when wired up
            request_count = 0

        # Tier limit
        try:
            subscription = await feature_gate.get_organization_subscription(db, str(org_id))
            tier_name = (
                subscription["tier"].value
                if hasattr(subscription["tier"], "value")
                else str(subscription["tier"])
            )
            limits = subscription.get("limits") or {}
            request_limit = limits.get("requests_per_month") or 25_000  # free default
        except Exception:
            tier_name = "free"
            request_limit = 25_000

        # Headroom calculation
        if request_limit and request_limit > 0:
            pct_used = round(100 * request_count / request_limit, 1)
            headroom = request_limit - request_count
        else:
            pct_used = 0.0
            headroom = None  # unlimited

        return {
            "period_start": month_start.isoformat(),
            "period_end_estimate": (month_start + timedelta(days=31)).isoformat(),
            "tier": tier_name,
            "gateway_requests": {
                "used": request_count,
                "limit": request_limit,
                "percent_used": pct_used,
                "remaining": headroom,
            },
            # TODO Phase 2: include Origami turn usage once metering table exists
            "origami_turns": {"used": None, "limit": None, "note": "metering pending"},
        }
