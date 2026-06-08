"""Service for Personal Access Tokens (bp-) and Project Tokens (bj-)."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.access_token import AccessToken
from app.models.user import User


def generate_token(prefix: str) -> tuple[str, str, str]:
    """Generate a token. Returns (raw_token, token_hash, display_prefix)."""
    raw = prefix + secrets.token_hex(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    display_prefix = raw[:12] + "..."
    return raw, token_hash, display_prefix


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def validate_access_token(db: AsyncSession, raw_token: str) -> Optional[AccessToken]:
    """Look up token by hash, check not revoked/expired."""
    token_hash = hash_token(raw_token)
    result = await db.execute(
        select(AccessToken).where(
            AccessToken.token_hash == token_hash,
            AccessToken.revoked_at.is_(None),
            AccessToken.expires_at > func.now(),
        )
    )
    return result.scalar_one_or_none()


async def create_personal_token(
    db: AsyncSession,
    user: User,
    name: str,
    scopes: Optional[list[str]],
    expires_in_days: int,
    rate_limit: int,
) -> tuple[AccessToken, str]:
    """Create a PAT. Returns (token_record, raw_token)."""
    raw, token_hash, display_prefix = generate_token("bp-")

    token = AccessToken(
        org_id=user.org_id,
        user_id=user.id,
        project_id=None,
        token_type="personal",
        name=name,
        token_hash=token_hash,
        token_prefix=display_prefix,
        scopes=scopes,
        rate_limit=rate_limit,
        expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days),
        created_by_id=user.id,
    )
    db.add(token)
    await db.flush()
    return token, raw


async def create_project_token(
    db: AsyncSession,
    user: User,
    project_id: uuid.UUID,
    name: str,
    expires_in_days: int,
    rate_limit: int,
) -> tuple[AccessToken, str]:
    """Create a project token. Returns (token_record, raw_token)."""
    raw, token_hash, display_prefix = generate_token("bj-")

    token = AccessToken(
        org_id=user.org_id,
        user_id=None,
        project_id=project_id,
        token_type="project",
        name=name,
        token_hash=token_hash,
        token_prefix=display_prefix,
        scopes=None,
        rate_limit=rate_limit,
        expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days),
        created_by_id=user.id,
    )
    db.add(token)
    await db.flush()
    return token, raw


async def revoke_token(db: AsyncSession, token_id: uuid.UUID, org_id: uuid.UUID) -> Optional[AccessToken]:
    """Soft-revoke a token. Returns the token if found."""
    result = await db.execute(
        select(AccessToken).where(
            AccessToken.id == token_id,
            AccessToken.org_id == org_id,
            AccessToken.revoked_at.is_(None),
        )
    )
    token = result.scalar_one_or_none()
    if token:
        token.revoked_at = datetime.now(timezone.utc)
        await db.flush()
    return token


async def list_user_tokens(db: AsyncSession, user_id: uuid.UUID) -> list[AccessToken]:
    """List all PATs for a user (including revoked, for audit)."""
    result = await db.execute(
        select(AccessToken)
        .where(AccessToken.user_id == user_id, AccessToken.token_type == "personal")
        .order_by(AccessToken.created_at.desc())
    )
    return list(result.scalars().all())


async def list_project_tokens(db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID) -> list[AccessToken]:
    """List all tokens for a project."""
    result = await db.execute(
        select(AccessToken)
        .where(
            AccessToken.project_id == project_id,
            AccessToken.org_id == org_id,
            AccessToken.token_type == "project",
        )
        .order_by(AccessToken.created_at.desc())
    )
    return list(result.scalars().all())


async def count_user_tokens(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Count active (non-revoked) PATs for a user."""
    result = await db.execute(
        select(func.count(AccessToken.id)).where(
            AccessToken.user_id == user_id,
            AccessToken.token_type == "personal",
            AccessToken.revoked_at.is_(None),
        )
    )
    return result.scalar_one()


async def count_org_project_tokens(db: AsyncSession, org_id: uuid.UUID) -> int:
    """Count active (non-revoked) project tokens (bj-) across the whole org."""
    result = await db.execute(
        select(func.count(AccessToken.id)).where(
            AccessToken.org_id == org_id,
            AccessToken.token_type == "project",
            AccessToken.revoked_at.is_(None),
        )
    )
    return result.scalar_one()


async def update_last_used(db: AsyncSession, token: AccessToken, ip: Optional[str] = None):
    """Update last_used_at and last_used_ip."""
    token.last_used_at = datetime.now(timezone.utc)
    if ip:
        token.last_used_ip = ip
    await db.flush()
