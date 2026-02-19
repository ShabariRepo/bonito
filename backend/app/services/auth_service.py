import uuid
from datetime import datetime, timedelta, timezone

import bcrypt as _bcrypt
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.core.config import settings
from app.models.user import User

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:72]
    return _bcrypt.hashpw(pw, _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    pw = plain.encode("utf-8")[:72]
    return _bcrypt.checkpw(pw, hashed.encode("utf-8"))


def create_token(data: dict, expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_access_token(user_id: str, org_id: str, role: str) -> str:
    return create_token(
        {"sub": user_id, "org_id": org_id, "role": role, "type": "access"},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


async def create_enhanced_access_token(db: AsyncSession, user: User) -> str:
    """Create access token with role assignments for RBAC."""
    from app.models.role_assignment import RoleAssignment
    from app.models.role import Role
    
    # Get user's role assignments
    stmt = select(RoleAssignment, Role.name).join(Role).where(
        RoleAssignment.user_id == user.id
    )
    result = await db.execute(stmt)
    assignments = result.all()
    
    role_assignments = []
    for assignment, role_name in assignments:
        role_assignments.append({
            "role_id": str(assignment.role_id),
            "role_name": role_name,
            "scope_type": assignment.scope_type.value,
            "scope_id": str(assignment.scope_id) if assignment.scope_id else None
        })
    
    return create_token(
        {
            "sub": str(user.id),
            "org_id": str(user.org_id),
            "role": user.role,  # Legacy role for backward compatibility
            "role_assignments": role_assignments,
            "type": "access"
        },
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: str) -> str:
    return create_token(
        {"sub": user_id, "type": "refresh"},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token. Raises JWTError on failure."""
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])


async def store_session(r: redis.Redis, user_id: str, refresh_token: str) -> None:
    key = f"session:{user_id}"
    await r.set(key, refresh_token, ex=REFRESH_TOKEN_EXPIRE_DAYS * 86400)


async def invalidate_session(r: redis.Redis, user_id: str) -> None:
    await r.delete(f"session:{user_id}")


async def is_session_valid(r: redis.Redis, user_id: str, refresh_token: str) -> bool:
    stored = await r.get(f"session:{user_id}")
    return stored == refresh_token


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    email: str,
    password: str,
    name: str,
    org_id: uuid.UUID,
    role: str = "viewer",
) -> User:
    user = User(
        email=email,
        hashed_password=hash_password(password),
        name=name,
        org_id=org_id,
        role=role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
