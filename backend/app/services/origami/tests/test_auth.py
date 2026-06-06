"""Tests for Origami auth — og- token model, lookup, and context binding.

Focus areas:
- Auto-mint / return-existing pattern
- org_id is read from token, not from anywhere else
- Revocation invalidates lookup
- Wrong-prefix rejected
- Token type isolation (bp- doesn't satisfy og- lookup, etc.)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.access_token import AccessToken
from app.services.origami import auth


# Marker so tests can be skipped in environments without a DB.
pytestmark = pytest.mark.asyncio


# ─────────── shape-only sanity (no DB) ───────────


def test_origami_context_is_frozen():
    """OrigamiContext is a frozen dataclass — org_id can't be mutated post-creation."""
    ctx = auth.OrigamiContext(
        user_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        role="admin",
        token_id=uuid.uuid4(),
    )
    with pytest.raises((AttributeError, Exception)):
        ctx.org_id = uuid.uuid4()  # type: ignore[misc]


def test_origami_constants():
    assert auth.ORIGAMI_TOKEN_PREFIX == "og-"
    assert auth.ORIGAMI_TOKEN_TYPE == "origami"
    assert auth.ORIGAMI_TOKEN_TTL_DAYS == 90


# ─────────── DB-dependent tests ───────────
# These require a test DB fixture (app uses pytest-asyncio + a `db` fixture
# elsewhere in the suite). Marked xfail if the fixture isn't available yet.


@pytest.mark.skip(reason="Requires test DB fixture — wire when integration suite ready")
async def test_get_or_create_mints_when_missing(db, sample_user):
    """First call mints a new token; raw_token is returned."""
    token, raw = await auth.get_or_create_origami_token(db, sample_user)
    assert token.token_type == "origami"
    assert token.user_id == sample_user.id
    assert token.org_id == sample_user.org_id
    assert token.project_id is None
    assert raw is not None
    assert raw.startswith("og-")


@pytest.mark.skip(reason="Requires test DB fixture — wire when integration suite ready")
async def test_get_or_create_returns_existing(db, sample_user):
    """Second call within TTL returns the same token; raw_token is None."""
    first_token, first_raw = await auth.get_or_create_origami_token(db, sample_user)
    second_token, second_raw = await auth.get_or_create_origami_token(db, sample_user)
    assert second_token.id == first_token.id
    assert second_raw is None  # we don't have the raw value


@pytest.mark.skip(reason="Requires test DB fixture — wire when integration suite ready")
async def test_revoke_then_mints_fresh(db, sample_user):
    """After revocation, get_or_create mints a brand new token."""
    first_token, _ = await auth.get_or_create_origami_token(db, sample_user)
    await auth.revoke_origami_token(db, sample_user.id, sample_user.org_id)
    second_token, second_raw = await auth.get_or_create_origami_token(db, sample_user)
    assert second_token.id != first_token.id
    assert second_raw is not None


@pytest.mark.skip(reason="Requires test DB fixture — wire when integration suite ready")
async def test_org_id_isolation(db, sample_user, sample_user_other_org):
    """A user's token doesn't appear when querying for a different org."""
    token, _ = await auth.get_or_create_origami_token(db, sample_user)
    found = await auth.get_active_origami_token(
        db, sample_user.id, sample_user_other_org.org_id
    )
    assert found is None


# ─────────── Dependency-level security tests (mocked) ───────────


async def test_get_origami_context_rejects_missing_bearer():
    """No Bearer prefix → 401."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await auth.get_origami_context(authorization="og-abc123", db=None)  # type: ignore[arg-type]
    assert exc.value.status_code == 401


async def test_get_origami_context_rejects_wrong_prefix():
    """Bearer with bp- prefix → 401 (must be og-)."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await auth.get_origami_context(authorization="Bearer bp-fake", db=None)  # type: ignore[arg-type]
    assert exc.value.status_code == 401
    assert "og-" in exc.value.detail


# TODO: Add full integration test once test DB fixture is available:
# - test_get_origami_context_returns_org_from_token (the critical invariant)
# - test_get_origami_context_org_id_never_from_request_params
# - test_concurrent_session_creates_idempotently
