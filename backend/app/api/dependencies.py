import uuid
from functools import wraps
from typing import Callable

import sentry_sdk
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.auth_service import decode_token, get_user_by_id
from app.services.feature_gate import feature_gate
from app.models.user import User

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    raw = credentials.credentials

    # ── Personal Access Token (bp-) ──
    if raw.startswith("bp-"):
        from app.services.access_token_service import validate_access_token, update_last_used
        token = await validate_access_token(db, raw)
        if not token or token.token_type != "personal":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired personal access token")
        await update_last_used(db, token)
        user = await get_user_by_id(db, token.user_id)
        if not user or not user.email_verified:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or suspended")
        user._access_token = token  # type: ignore[attr-defined]
        sentry_sdk.set_user({"id": str(user.id), "email": user.email, "username": user.name, "org_id": str(user.org_id)})
        return user

    # ── Project Token (bj-) ──
    if raw.startswith("bj-"):
        from app.services.access_token_service import validate_access_token, update_last_used
        token = await validate_access_token(db, raw)
        if not token or token.token_type != "project":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired project token")
        await update_last_used(db, token)
        user = await get_user_by_id(db, token.created_by_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token creator not found")
        user._access_token = token  # type: ignore[attr-defined]
        user._project_scope = token.project_id  # type: ignore[attr-defined]
        sentry_sdk.set_user({"id": str(user.id), "email": user.email, "username": user.name, "org_id": str(user.org_id)})
        return user

    # ── Origami Token (og-) ──
    if raw.startswith("og-"):
        from app.services.access_token_service import validate_access_token, update_last_used
        token = await validate_access_token(db, raw)
        if not token or token.token_type != "origami":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired origami token")
        await update_last_used(db, token)
        user = await get_user_by_id(db, token.user_id)
        if not user or not user.email_verified:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or suspended")
        # org_id check: og- tokens are immutably bound to one org at creation.
        # If token.org_id != user.org_id (e.g. user was moved between orgs after token mint),
        # reject — the token no longer represents valid access.
        if token.org_id != user.org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origami token org no longer matches user org")
        user._access_token = token  # type: ignore[attr-defined]
        sentry_sdk.set_user({"id": str(user.id), "email": user.email, "username": user.name, "org_id": str(user.org_id)})
        return user

    # ── JWT session token (existing path) ──
    try:
        payload = decode_token(raw)
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.email_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account suspended")

    sentry_sdk.set_user({
        "id": str(user.id),
        "email": user.email,
        "username": user.name,
        "org_id": str(user.org_id),
    })

    return user


async def require_superadmin(user: User = Depends(get_current_user)) -> User:
    from app.core.config import settings
    admin_emails = [e.strip() for e in settings.admin_emails.split(",") if e.strip()]
    if user.email not in admin_emails:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform admin access required")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


async def require_org_member(
    org_id: uuid.UUID,
    user: User = Depends(get_current_user),
) -> User:
    if str(user.org_id) != str(org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this organization")
    return user


async def require_superadmin(user: User = Depends(get_current_user)) -> User:
    from app.core.config import settings
    admin_emails = [e.strip() for e in settings.admin_emails.split(",") if e.strip()]
    if user.email not in admin_emails:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform admin access required")
    return user


def require_feature(feature: str):
    """Dependency factory for requiring specific features"""
    async def _require_feature(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        await feature_gate.require_feature(db, str(user.org_id), feature)
        return user
    return _require_feature


def require_tier(min_tier: str):
    """Dependency factory for requiring minimum subscription tier"""
    async def _require_tier(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        subscription = await feature_gate.get_organization_subscription(db, str(user.org_id))
        
        tier_hierarchy = {"free": 0, "starter": 1, "pro": 2, "enterprise": 3, "scale": 4}
        current_tier_level = tier_hierarchy.get(subscription["tier"].value, 0)
        required_tier_level = tier_hierarchy.get(min_tier, 3)

        if current_tier_level < required_tier_level:
            tier_names = {"free": "Free", "starter": "Starter", "pro": "Pro", "enterprise": "Enterprise", "scale": "Scale"}
            required_name = tier_names.get(min_tier, "Enterprise")
            message = f"This feature requires a {required_name} plan. Upgrade at getbonito.com/pricing"
            
            detail = {
                "message": message,
                "required_tier": min_tier,
                "upgrade_url": "https://getbonito.com/pricing"
            }
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
        
        return user
    return _require_tier


def require_usage_limit(limit_type: str):
    """Dependency factory for checking usage limits"""
    async def _require_usage_limit(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        await feature_gate.require_usage_limit(db, str(user.org_id), limit_type)
        return user
    return _require_usage_limit


async def require_pro_or_enterprise(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Shortcut dependency for Pro+ features"""
    subscription = await feature_gate.get_organization_subscription(db, str(user.org_id))
    
    if subscription["tier"].value in ("free", "starter"):
        detail = {
            "message": "This feature requires a Pro or Enterprise plan. Upgrade at getbonito.com/pricing",
            "required_tier": "pro",
            "upgrade_url": "https://getbonito.com/pricing"
        }
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
    
    return user


async def require_enterprise(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Shortcut dependency for Enterprise-only features"""
    subscription = await feature_gate.get_organization_subscription(db, str(user.org_id))

    if subscription["tier"].value not in ("enterprise", "scale"):
        detail = {
            "message": "This feature requires an Enterprise plan. Upgrade at getbonito.com/pricing",
            "required_tier": "enterprise",
            "upgrade_url": "https://getbonito.com/pricing"
        }
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

    return user


def check_project_scope(user: User, project_id: uuid.UUID) -> None:
    """Enforce project token scope.

    Call this in any route that takes a project_id path param.
    If the user authenticated with a project token (bj-), this ensures
    the requested project_id matches the token's project_id.
    PATs and JWTs pass through unrestricted.
    Raises 403 if the token's project doesn't match.
    """
    scoped_project = getattr(user, "_project_scope", None)
    if scoped_project is None:
        return  # JWT or PAT — no restriction
    if str(scoped_project) != str(project_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project token does not have access to this project",
        )
