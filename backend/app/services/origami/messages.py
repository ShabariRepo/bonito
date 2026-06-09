"""Persistence helpers for origami_messages.

Three write functions — one per role we care about — plus a couple of
read helpers used by the conversations API. All writes are best-effort
(swallow exceptions) so a failed persist never breaks a chat turn.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.origami_message import OrigamiMessage

logger = logging.getLogger(__name__)


async def record_user_message(
    *,
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    project_id: Optional[uuid.UUID],
    conversation_id: str,
    session_id: Optional[uuid.UUID],
    content: str,
) -> Optional[uuid.UUID]:
    try:
        row = OrigamiMessage(
            org_id=org_id, user_id=user_id, project_id=project_id,
            conversation_id=conversation_id, session_id=session_id,
            role="user", content=content, synthesized=False,
        )
        db.add(row)
        await db.flush()
        try:
            await db.commit()
        except Exception:
            await db.rollback()
        return row.id
    except Exception:
        logger.exception("record_user_message failed (non-fatal)")
        return None


async def record_assistant_message(
    *,
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    project_id: Optional[uuid.UUID],
    conversation_id: str,
    session_id: Optional[uuid.UUID],
    content: str,
    model_used: Optional[str],
    synthesized: bool,
    extra_metadata: Optional[dict[str, Any]] = None,
) -> Optional[uuid.UUID]:
    if not content:
        return None
    try:
        row = OrigamiMessage(
            org_id=org_id, user_id=user_id, project_id=project_id,
            conversation_id=conversation_id, session_id=session_id,
            role="assistant", content=content,
            model_used=model_used, synthesized=synthesized,
            extra_metadata=extra_metadata,
        )
        db.add(row)
        await db.flush()
        try:
            await db.commit()
        except Exception:
            await db.rollback()
        return row.id
    except Exception:
        logger.exception("record_assistant_message failed (non-fatal)")
        return None


async def record_plan_message(
    *,
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    project_id: Optional[uuid.UUID],
    conversation_id: str,
    session_id: Optional[uuid.UUID],
    plan_card: dict[str, Any],
) -> Optional[uuid.UUID]:
    try:
        row = OrigamiMessage(
            org_id=org_id, user_id=user_id, project_id=project_id,
            conversation_id=conversation_id, session_id=session_id,
            role="plan",
            content=plan_card.get("intent", "(plan)"),
            extra_metadata={"plan_card": plan_card},
        )
        db.add(row)
        await db.flush()
        try:
            await db.commit()
        except Exception:
            await db.rollback()
        return row.id
    except Exception:
        logger.exception("record_plan_message failed (non-fatal)")
        return None


# ────────────────────────── Read helpers ──────────────────────────


async def list_conversations_for_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Group messages by conversation_id, return one row per conversation
    with first/last message timestamps, message count, preview, role distribution.

    Ordered newest first by last_message_at."""

    stmt = (
        select(
            OrigamiMessage.conversation_id.label("conversation_id"),
            func.count(OrigamiMessage.id).label("message_count"),
            func.min(OrigamiMessage.created_at).label("first_at"),
            func.max(OrigamiMessage.created_at).label("last_at"),
        )
        .where(OrigamiMessage.user_id == user_id)
        .group_by(OrigamiMessage.conversation_id)
        .order_by(desc("last_at"))
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = list(result)

    conversations: list[dict[str, Any]] = []
    for row in rows:
        # Pull first user message as a preview / title
        first_user = await db.execute(
            select(OrigamiMessage.content)
            .where(
                OrigamiMessage.conversation_id == row.conversation_id,
                OrigamiMessage.user_id == user_id,
                OrigamiMessage.role == "user",
            )
            .order_by(OrigamiMessage.created_at)
            .limit(1)
        )
        preview = first_user.scalar_one_or_none() or "(empty conversation)"
        if len(preview) > 200:
            preview = preview[:200] + "…"
        # Plan card count (a rough "did they build something?" signal)
        plan_count_result = await db.execute(
            select(func.count(OrigamiMessage.id)).where(
                OrigamiMessage.conversation_id == row.conversation_id,
                OrigamiMessage.role == "plan",
            )
        )
        plan_count = int(plan_count_result.scalar_one() or 0)

        conversations.append({
            "conversation_id": row.conversation_id,
            "title": preview.split("\n")[0][:80],
            "preview": preview,
            "message_count": int(row.message_count),
            "plan_count": plan_count,
            "first_at": row.first_at.isoformat() if row.first_at else None,
            "last_at": row.last_at.isoformat() if row.last_at else None,
        })
    return conversations


async def get_conversation_messages(
    db: AsyncSession,
    conversation_id: str,
    user_id: uuid.UUID,
) -> Optional[list[dict[str, Any]]]:
    """Fetch full message history for a conversation, scoped to the user.

    Returns None if no messages exist (treat as 404). Returns the list
    of message dicts otherwise. Cross-tenant safe via user_id filter."""

    result = await db.execute(
        select(OrigamiMessage)
        .where(
            OrigamiMessage.conversation_id == conversation_id,
            OrigamiMessage.user_id == user_id,
        )
        .order_by(OrigamiMessage.created_at)
    )
    rows = list(result.scalars())
    if not rows:
        return None
    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "model_used": m.model_used,
            "synthesized": m.synthesized,
            "extra_metadata": m.extra_metadata,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in rows
    ]
