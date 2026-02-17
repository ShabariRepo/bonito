import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.auth_service import decode_token, get_user_by_id
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
