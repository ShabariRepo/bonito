"""Origami auth: `og-` token model + get_origami_context dependency.

Security invariant: `org_id` is read FROM THE TOKEN, never from the request or
the model output. An og- token is permanently bound to one (user_id, org_id)
pair at creation. Even if the orchestrator hallucinates an org_id in a tool
call, the wrapper layer reads it from OrigamiContext, not the model's params.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.access_token import AccessToken
from app.models.user import User
from app.services.access_token_service import generate_token, hash_token, update_last_used


ORIGAMI_TOKEN_PREFIX = "og-"
ORIGAMI_TOKEN_TYPE = "origami"
ORIGAMI_TOKEN_TTL_DAYS = 90


@dataclass(frozen=True)
class OrigamiContext:
    """Read from the og- token. Frozen — never reassign org_id from request data."""

    user_id: uuid.UUID
    org_id: uuid.UUID
    role: str
    token_id: uuid.UUID


async def get_active_origami_token(
    db: AsyncSession,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
) -> Optional[AccessToken]:
    """Return the active og- token for this (user, org) pair, if any."""
    result = await db.execute(
        select(AccessToken).where(
            AccessToken.user_id == user_id,
            AccessToken.org_id == org_id,
            AccessToken.token_type == ORIGAMI_TOKEN_TYPE,
            AccessToken.revoked_at.is_(None),
            AccessToken.expires_at > func.now(),
        )
    )
    return result.scalar_one_or_none()


async def create_origami_token(
    db: AsyncSession,
    user: User,
    rate_limit: int = 120,
) -> tuple[AccessToken, str]:
    """Mint a new og- token bound to (user.id, user.org_id). Returns (record, raw)."""
    raw, token_hash, display_prefix = generate_token(ORIGAMI_TOKEN_PREFIX)

    token = AccessToken(
        org_id=user.org_id,
        user_id=user.id,
        project_id=None,
        token_type=ORIGAMI_TOKEN_TYPE,
        name=f"origami-{user.email}",
        token_hash=token_hash,
        token_prefix=display_prefix,
        scopes=None,
        rate_limit=rate_limit,
        expires_at=datetime.now(timezone.utc) + timedelta(days=ORIGAMI_TOKEN_TTL_DAYS),
        created_by_id=user.id,
    )
    db.add(token)
    await db.flush()
    return token, raw


async def get_or_create_origami_token(
    db: AsyncSession,
    user: User,
) -> tuple[AccessToken, Optional[str]]:
    """Return active og- token, or mint one if none exists.

    Returns (token_record, raw_token_or_None). raw_token is None when the
    token already existed (we don't have the raw value, only the hash).
    Frontend pattern: call once on session-open; if raw is None, the token
    is already active and the frontend stores nothing new.
    """
    existing = await get_active_origami_token(db, user.id, user.org_id)
    if existing:
        return existing, None
    return await create_origami_token(db, user)


async def revoke_origami_token(
    db: AsyncSession,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
) -> Optional[AccessToken]:
    """Revoke the active og- token for this (user, org). Force re-mint on next session."""
    token = await get_active_origami_token(db, user_id, org_id)
    if token:
        token.revoked_at = datetime.now(timezone.utc)
        await db.flush()
    return token


# ───────────────────────── FastAPI dependency ─────────────────────────


async def get_origami_context(
    authorization: str = Header(..., alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> OrigamiContext:
    """Auth dependency for /api/origami/* routes.

    SECURITY INVARIANT: returns (user_id, org_id) from the TOKEN record, never
    from the request. Tool wrappers downstream must read org_id from this
    context, never trust an org_id field in a model-generated tool param.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
        )

    raw = authorization.removeprefix("Bearer ").strip()

    if not raw.startswith(ORIGAMI_TOKEN_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Origami endpoints require an og- token",
        )

    token_hash = hash_token(raw)
    result = await db.execute(
        select(AccessToken).where(
            AccessToken.token_hash == token_hash,
            AccessToken.token_type == ORIGAMI_TOKEN_TYPE,
            AccessToken.revoked_at.is_(None),
            AccessToken.expires_at > func.now(),
        )
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, revoked, or expired og- token",
        )

    # Touch-update last_used (don't block on this; failure is non-fatal)
    try:
        await update_last_used(db, record)
    except Exception:
        pass

    user = await db.scalar(select(User).where(User.id == record.user_id))
    if not user:
        # Stale FK — should not happen with cascade, but defensive
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token user no longer exists",
        )

    return OrigamiContext(
        user_id=record.user_id,
        org_id=record.org_id,  # ← FROM TOKEN, immutable since creation
        role=user.role,
        token_id=record.id,
    )
