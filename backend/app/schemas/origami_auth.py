"""Pydantic schemas for Origami auth endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class OrigamiTokenResponse(BaseModel):
    """Represents an existing og- token. Never includes the raw token value."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    user_id: uuid.UUID
    token_prefix: str  # display prefix only, e.g. "og-a1b2c3d4..."
    name: str
    expires_at: datetime
    last_used_at: Optional[datetime] = None
    last_used_ip: Optional[str] = None
    created_at: datetime
    revoked_at: Optional[datetime] = None


class OrigamiTokenMinted(BaseModel):
    """Returned ONCE on first mint. Includes the raw token (frontend stores it)."""

    token: OrigamiTokenResponse
    raw_token: str  # full og-... string, shown to user / stored client-side ONCE
    is_new: bool  # true if just minted; false if returning existing active token (raw absent)


class OrigamiSessionStart(BaseModel):
    """Response shape for POST /api/origami/session/start.

    Always returns the token record. raw_token is only present when we just
    minted it (frontend stores in secure session storage). On subsequent calls
    within TTL, raw_token is None and frontend continues using the previously
    stored value.
    """

    token: OrigamiTokenResponse
    raw_token: Optional[str] = None
    is_new: bool
