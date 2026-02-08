import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis_lib

from app.core.database import get_db
from app.core.redis import get_redis
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------- Schemas ----------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    org_id: uuid.UUID


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    org_id: uuid.UUID
    role: str

    class Config:
        from_attributes = True


# ---------- Endpoints ----------

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await auth_service.get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = await auth_service.create_user(db, body.email, body.password, body.name, body.org_id)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    r: redis_lib.Redis = Depends(get_redis),
):
    user = await auth_service.get_user_by_email(db, body.email)
    if not user or not auth_service.verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access = auth_service.create_access_token(str(user.id), str(user.org_id), user.role)
    refresh = auth_service.create_refresh_token(str(user.id))
    await auth_service.store_session(r, str(user.id), refresh)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    r: redis_lib.Redis = Depends(get_redis),
):
    try:
        payload = auth_service.decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = payload["sub"]
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if not await auth_service.is_session_valid(r, user_id, body.refresh_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    user = await auth_service.get_user_by_id(db, uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access = auth_service.create_access_token(str(user.id), str(user.org_id), user.role)
    refresh = auth_service.create_refresh_token(str(user.id))
    await auth_service.store_session(r, str(user.id), refresh)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    user: User = Depends(get_current_user),
    r: redis_lib.Redis = Depends(get_redis),
):
    await auth_service.invalidate_session(r, str(user.id))


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return user
