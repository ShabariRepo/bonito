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
from app.services.origami.orchestrator import (
    OrigamiEvent,
    run_origami_turn,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/origami", tags=["origami"])


class OrigamiTurnRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)
    conversation_id: Optional[str] = None


@router.post("/turn")
async def origami_turn(
    body: OrigamiTurnRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run one Origami chat turn and stream events back as SSE."""

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for event in run_origami_turn(
                user=user,
                message=body.message,
                conversation_id=body.conversation_id,
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
