import uuid
from functools import wraps
from typing import Callable

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
    try:
        payload = decode_token(credentials.credentials)
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
        
        tier_hierarchy = {"free": 0, "pro": 1, "enterprise": 2}
        current_tier_level = tier_hierarchy.get(subscription["tier"].value, 0)
        required_tier_level = tier_hierarchy.get(min_tier, 2)
        
        if current_tier_level < required_tier_level:
            tier_names = {"free": "Free", "pro": "Pro", "enterprise": "Enterprise"}
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
    
    if subscription["tier"].value == "free":
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
    
    if subscription["tier"].value != "enterprise":
        detail = {
            "message": "This feature requires an Enterprise plan. Upgrade at getbonito.com/pricing",
            "required_tier": "enterprise",
            "upgrade_url": "https://getbonito.com/pricing"
        }
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
    
    return user
