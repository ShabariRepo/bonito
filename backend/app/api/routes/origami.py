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
    plan_store.delete_plan(body.plan_card_id)


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
