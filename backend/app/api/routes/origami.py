"""Origami chat route — POST /api/origami/turn (SSE stream).

Phase 1 skeleton. Authed via existing get_current_user (JWT). The og- token
path also works because get_current_user was extended to recognize og- prefix.

Request:
    POST /api/origami/turn
    Authorization: Bearer <jwt> | Bearer og-...
    Content-Type: application/json
    Body: { "message": "string", "conversation_id": "optional-uuid" }

Response: text/event-stream

Events emitted:
    turn_started, message_complete, tool_started, tool_completed,
    tool_failed, done, error
"""

from __future__ import annotations

import logging
from typing import AsyncIterator, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.origami_auth import (
    OrigamiSessionStart,
    OrigamiTokenResponse,
)
from app.schemas.origami_plan import (
    CancelPlanRequest,
    ExecutePlanRequest,
)
from app.services.origami import plan_store
from app.services.origami.auth import (
    get_or_create_origami_token,
    revoke_origami_token,
)
from app.services.origami.orchestrator import (
    OrigamiEvent,
    execute_plan as execute_plan_orchestrator,
    run_origami_turn,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/origami", tags=["origami"])


class OrigamiTurnRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)
    conversation_id: Optional[str] = None
    project_id: Optional[str] = Field(
        default=None,
        description="Optional: project the user is currently working in. "
        "Recorded on origami_turn_log + origami_audit_log for per-project analytics.",
    )


@router.post("/turn")
async def origami_turn(
    body: OrigamiTurnRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run one Origami chat turn and stream events back as SSE."""
    import uuid as _uuid

    parsed_project_id: Optional[_uuid.UUID] = None
    if body.project_id:
        try:
            parsed_project_id = _uuid.UUID(body.project_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="project_id must be a valid UUID",
            )

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for event in run_origami_turn(
                user=user,
                message=body.message,
                conversation_id=body.conversation_id,
                project_id=parsed_project_id,
                db=db,
            ):
                yield event.to_sse()
        except Exception as e:
            logger.exception("Origami turn failed at the route layer")
            err = OrigamiEvent("error", {
                "code": "route_layer_failure",
                "message": str(e),
            })
            yield err.to_sse()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",  # disable nginx buffering
            "Connection": "keep-alive",
        },
    )


@router.post("/execute_plan")
async def origami_execute_plan(
    body: ExecutePlanRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deploy a plan card the user just confirmed.

    Streams the same SSE event vocabulary as /turn: tool_started,
    tool_completed, tool_failed, execution_started, execution_done.
    """

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for event in execute_plan_orchestrator(
                user=user,
                plan_card_id=body.plan_card_id,
                db=db,
            ):
                yield event.to_sse()
        except Exception as e:
            logger.exception("Origami execute_plan failed at the route layer")
            err = OrigamiEvent("error", {
                "code": "route_layer_failure",
                "message": str(e),
            })
            yield err.to_sse()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.delete("/plan", status_code=status.HTTP_204_NO_CONTENT)
async def origami_cancel_plan(
    body: CancelPlanRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel (delete) a pending plan card."""
    await plan_store.delete_plan(body.plan_card_id)


@router.post("/session/start", response_model=OrigamiSessionStart)
async def origami_session_start(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mint (or return existing) og- token for the user's Origami session.

    Frontend calls this on first visit to /origami. If a new token was just
    minted, raw_token is returned ONCE — the frontend stores it in secure
    session storage. On subsequent calls within TTL, raw_token is null and
    the existing client-side value continues to work.
    """
    token_record, raw_token = await get_or_create_origami_token(db, user)
    await db.commit()
    return OrigamiSessionStart(
        token=OrigamiTokenResponse.model_validate(token_record),
        raw_token=raw_token,
        is_new=raw_token is not None,
    )


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
async def origami_session_revoke(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke the user's active og- token. Next session_start mints fresh."""
    await revoke_origami_token(db, user.id, user.org_id)
    await db.commit()


@router.get("/usage")
async def origami_usage_for_user(
    period: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Customer-facing Origami usage view for the user's own org.

    Returns current-period summary (turns used, tier cap, % remaining,
    cost projection) plus a 30-day daily breakdown for the chart.

    Optional ?period=YYYY-MM query param. Defaults to current month.
    """
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select, func, cast, Date
    from app.models.origami_logs import OrigamiTurnLog
    from app.services.origami.metering import (
        TIER_TURN_CAPS, get_turn_cap, check_quota,
    )
    from app.services.feature_gate import feature_gate

    # Resolve period (YYYY-MM)
    now = datetime.now(timezone.utc)
    if period:
        try:
            year, month = period.split("-")
            int(year), int(month)
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="period must be YYYY-MM",
            )
    else:
        period = f"{now.year:04d}-{now.month:02d}"

    # Live tier
    try:
        sub = await feature_gate.get_organization_subscription(db, str(user.org_id))
        tier_enum = sub["tier"]
        tier = tier_enum.value if hasattr(tier_enum, "value") else str(tier_enum)
    except Exception:
        tier = "free"

    # Quota snapshot for THIS period (we use check_quota helper for current period
    # which queries the same table)
    quota_snapshot = await check_quota(db, user.org_id, tier)

    # Aggregate for the requested period (might be historical)
    period_result = await db.execute(
        select(
            func.count(OrigamiTurnLog.id),
            func.coalesce(func.sum(OrigamiTurnLog.cost_usd), 0),
            func.coalesce(func.sum(OrigamiTurnLog.input_tokens), 0),
            func.coalesce(func.sum(OrigamiTurnLog.output_tokens), 0),
            func.coalesce(func.sum(OrigamiTurnLog.tool_calls_count), 0),
        ).where(
            OrigamiTurnLog.org_id == user.org_id,
            OrigamiTurnLog.billing_period_month == period,
        )
    )
    p_count, p_cost, p_in, p_out, p_tools = period_result.one()

    # Daily breakdown for the period (UTC day buckets)
    daily_result = await db.execute(
        select(
            cast(OrigamiTurnLog.created_at, Date).label("day"),
            func.count(OrigamiTurnLog.id),
            func.coalesce(func.sum(OrigamiTurnLog.cost_usd), 0),
        )
        .where(
            OrigamiTurnLog.org_id == user.org_id,
            OrigamiTurnLog.billing_period_month == period,
        )
        .group_by("day")
        .order_by("day")
    )
    daily = [
        {
            "day": row[0].isoformat() if row[0] else None,
            "turns": int(row[1] or 0),
            "cost_usd": float(row[2] or 0),
        }
        for row in daily_result
    ]

    cap = get_turn_cap(tier)
    cap_for_response = None if cap == float("inf") else int(cap)
    used = int(p_count or 0)
    remaining = (
        None if cap_for_response is None else max(0, cap_for_response - used)
    )
    pct_used = (
        None if not cap_for_response else round(100 * used / cap_for_response, 1)
    )

    return {
        "period": period,
        "tier": tier,
        "turns_used": used,
        "turns_cap": cap_for_response,
        "turns_remaining": remaining,
        "percent_used": pct_used,
        "cost_usd_this_period": float(p_cost or 0),
        "overage_rate_usd": quota_snapshot.get("overage_rate_usd", 0.0),
        "input_tokens": int(p_in or 0),
        "output_tokens": int(p_out or 0),
        "tool_calls": int(p_tools or 0),
        "daily": daily,
    }


@router.get("/health")
async def origami_health():
    """Quick health probe — does NOT require auth.

    Returns the list of registered tools so we can sanity-check the import
    chain in deployed environments.
    """
    from app.services.origami.tools.base import TOOL_REGISTRY

    return {
        "status": "ok",
        "registered_tools": list(TOOL_REGISTRY.keys()),
        "tool_count": len(TOOL_REGISTRY),
    }
