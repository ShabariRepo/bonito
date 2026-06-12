"""Bonito Studio routes — POST /api/studio/init + POST /api/studio/turn.

Studio is the chat-first front door for Bonito (`/` after auth). It reuses
Origami's orchestrator wholesale — the only swap is the system prompt
(BDR-flavored) and an injected org snapshot as extra_context.

Endpoints:

  POST /api/studio/init
    Returns the org snapshot the frontend uses to render the opener
    placeholder + future server-side opener text. Cheap, parallel
    aggregate queries. p95 target <500ms.

  POST /api/studio/turn
    SSE stream — same event vocabulary as /api/origami/turn (turn_started,
    message_token, tool_started, tool_completed, tool_failed, done, error)
    so the Studio frontend can reuse the Origami SSE parser unchanged.
    Differences from Origami's /turn: snapshot is fetched server-side and
    injected as extra_context; system_prompt is STUDIO_SYSTEM_PROMPT.
"""

from __future__ import annotations

import logging
import uuid as _uuid
from typing import AsyncIterator, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services.origami.orchestrator import OrigamiEvent, run_origami_turn
from app.services.studio.prompt import (
    STUDIO_SYSTEM_PROMPT,
    render_snapshot_for_prompt,
)
from app.services.studio.snapshot import get_org_snapshot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/studio", tags=["studio"])


class StudioTurnRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)
    conversation_id: Optional[str] = None
    project_id: Optional[str] = Field(
        default=None,
        description="Optional: project the user is currently working in.",
    )


@router.post("/init")
async def studio_init(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch the org snapshot for Studio's opener.

    Frontend calls this on `/` load to render the empty-state opener and
    seed any tier-aware UI (sidebar badges, billing tooltips). The same
    snapshot is fetched on every /turn server-side — this endpoint exists
    so the frontend can pre-render before the first user message.
    """
    snapshot = await get_org_snapshot(db=db, org_id=user.org_id)
    return snapshot.to_dict()


@router.post("/turn")
async def studio_turn(
    body: StudioTurnRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run one Studio chat turn and stream events back as SSE.

    Internally delegates to run_origami_turn with the BDR system prompt
    and a freshly-fetched org snapshot rendered as extra_context.
    """
    parsed_project_id: Optional[_uuid.UUID] = None
    if body.project_id:
        try:
            parsed_project_id = _uuid.UUID(body.project_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="project_id must be a valid UUID",
            )

    snapshot = await get_org_snapshot(db=db, org_id=user.org_id)
    snapshot_context = render_snapshot_for_prompt(snapshot)

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for event in run_origami_turn(
                user=user,
                message=body.message,
                conversation_id=body.conversation_id,
                project_id=parsed_project_id,
                db=db,
                system_prompt=STUDIO_SYSTEM_PROMPT,
                extra_context=snapshot_context,
            ):
                yield event.to_sse()
        except Exception as e:
            logger.exception("Studio turn failed at the route layer")
            err = OrigamiEvent(
                "error",
                {"code": "route_layer_failure", "message": str(e)},
            )
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
