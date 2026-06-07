"""view_logs — recent gateway requests + agent sessions for debugging.

Read-only. Returns the latest activity so Origami can answer questions
like "why was my last request slow?", "what models am I using?", or
"are any agents misbehaving?".
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.origami.tools.base import OrigamiTool, register_tool


@register_tool
class ViewLogsTool(OrigamiTool):
    name = "view_logs"
    description = (
        "Return the most recent gateway requests and agent sessions for the "
        "user's organization. Use this when the user asks about recent "
        "activity, errors, latency, costs, which models they're using, or "
        "why something failed. Returns up to `limit` of each (default 20)."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 50,
                "default": 20,
                "description": "Max entries to return per category. Defaults to 20.",
            },
        },
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
        limit = int(params.get("limit") or 20)
        if limit < 1:
            limit = 1
        if limit > 50:
            limit = 50

        gateway_recent = []
        agent_sessions_recent = []

        # Gateway requests
        try:
            from app.models.gateway import GatewayRequest

            result = await db.execute(
                select(
                    GatewayRequest.id,
                    GatewayRequest.model_requested,
                    GatewayRequest.model_used,
                    GatewayRequest.provider,
                    GatewayRequest.status,
                    GatewayRequest.latency_ms,
                    GatewayRequest.input_tokens,
                    GatewayRequest.output_tokens,
                    GatewayRequest.cost,
                    GatewayRequest.error_message,
                    GatewayRequest.created_at,
                ).where(
                    GatewayRequest.org_id == org_id,
                ).order_by(GatewayRequest.created_at.desc()).limit(limit)
            )
            for row in result:
                gateway_recent.append({
                    "id": str(row.id),
                    "model_requested": row.model_requested,
                    "model_used": row.model_used,
                    "provider": row.provider,
                    "status": row.status,
                    "latency_ms": row.latency_ms,
                    "input_tokens": row.input_tokens,
                    "output_tokens": row.output_tokens,
                    "cost_usd": float(row.cost) if row.cost is not None else 0.0,
                    "error": row.error_message,
                    "at": row.created_at.isoformat() if row.created_at else None,
                })
        except Exception as e:
            gateway_recent = []
            gateway_error = str(e)
        else:
            gateway_error = None

        # Recent agent sessions
        try:
            from app.models.agent_session import AgentSession

            result = await db.execute(
                select(
                    AgentSession.id,
                    AgentSession.agent_id,
                    AgentSession.title,
                    AgentSession.status,
                    AgentSession.message_count,
                    AgentSession.total_tokens,
                    AgentSession.total_cost,
                ).where(
                    AgentSession.org_id == org_id,
                ).limit(limit)
            )
            for row in result:
                agent_sessions_recent.append({
                    "id": str(row.id),
                    "agent_id": str(row.agent_id),
                    "title": row.title,
                    "status": row.status,
                    "message_count": row.message_count,
                    "total_tokens": row.total_tokens,
                    "total_cost_usd": (
                        float(row.total_cost) if row.total_cost is not None else 0.0
                    ),
                })
        except Exception:
            agent_sessions_recent = []

        # Summary stats for quick context
        success_count = sum(1 for g in gateway_recent if g["status"] == "success")
        error_count = sum(1 for g in gateway_recent if g["status"] != "success")
        total_cost = round(sum(g["cost_usd"] for g in gateway_recent), 4)

        return {
            "gateway_requests": {
                "shown": len(gateway_recent),
                "success": success_count,
                "errors": error_count,
                "total_cost_usd_in_view": total_cost,
                "entries": gateway_recent,
                "error_note": gateway_error,
            },
            "agent_sessions": {
                "shown": len(agent_sessions_recent),
                "entries": agent_sessions_recent,
            },
            "note": "Most recent first. Limit: {0}.".format(limit),
        }
