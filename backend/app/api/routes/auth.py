import os
import re
import uuid
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis_lib

from app.core.database import get_db
from app.core.redis import get_redis
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.organization import Organization
from app.services import auth_service
from app.services import email_service
from app.services.log_emitters import emit_auth_event

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------- Datetime Helpers ----------

def _ensure_utc_aware(dt: datetime | None) -> datetime | None:
    """Make a datetime timezone-aware (UTC) if it's naive.

    SQLite doesn't store timezone info, so values come back naive.
    PostgreSQL returns timezone-aware datetimes.  This normalises both.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ---------- Password Validation ----------

def _validate_password(password: str) -> None:
    """Enforce password complexity: min 8 chars, 1 upper, 1 lower, 1 digit."""
    errors: list[str] = []
    if len(password) < 8:
        errors.append("at least 8 characters")
    if not re.search(r"[A-Z]", password):
        errors.append("at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("at least one lowercase letter")
    if not re.search(r"[0-9]", password):
        errors.append("at least one number")
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Password must contain {', '.join(errors)}.",
        )


# ---------- Schemas ----------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    org_id: uuid.UUID | None = None


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
    email_verified: bool = False

    class Config:
        from_attributes = True


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class MessageResponse(BaseModel):
    message: str


# ---------- Endpoints ----------

@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Kill switch: block all new registrations when REGISTRATION_DISABLED=true
    if os.environ.get("REGISTRATION_DISABLED", "").lower() in ("true", "1", "yes"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Registration is currently closed")

    _validate_password(body.password)

    existing = await auth_service.get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    # If no org_id provided, create a personal organization
    org_id = body.org_id
    if not org_id:
        org = Organization(name=f"{body.name}'s Organization")
        db.add(org)
        await db.flush()
        org_id = org.id

    user = await auth_service.create_user(db, body.email, body.password, body.name, org_id, role="admin")

    # Generate verification token and store it (expires in 24 hours)
    token = secrets.token_urlsafe(48)
    user.verification_token = token
    user.verification_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    user.email_verified = False
    await db.flush()

    # Send verification email
    try:
        await email_service.send_verification_email(body.email, token)
    except Exception:
        pass  # Don't fail registration if email fails

    return MessageResponse(message="Registration successful. Please check your email to verify your account.")


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(body: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.verification_token == body.token)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token")

    # Check token expiry
    if user.verification_token_expires_at and datetime.now(timezone.utc) > _ensure_utc_aware(user.verification_token_expires_at):
        user.verification_token = None
        user.verification_token_expires_at = None
        await db.flush()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification token has expired. Please request a new one.")

    user.email_verified = True
    user.verification_token = None
    user.verification_token_expires_at = None
    await db.flush()

    # Send welcome email
    try:
        await email_service.send_welcome_email(user.email, user.name)
    except Exception:
        pass

    return MessageResponse(message="Email verified successfully. You can now log in.")


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    r: redis_lib.Redis = Depends(get_redis),
):
    user = await auth_service.get_user_by_email(db, body.email)
    if not user or not auth_service.verify_password(body.password, user.hashed_password or ""):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Check if the org has SSO enforced — block password login unless break-glass admin
    try:
        from app.services.saml_service import get_sso_config
        sso_config = await get_sso_config(db, user.org_id)
        if sso_config and sso_config.enabled and sso_config.enforced:
            # Allow break-glass admin to use password login
            is_breakglass = (
                sso_config.breakglass_user_id
                and str(sso_config.breakglass_user_id) == str(user.id)
            )
            if not is_breakglass:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Your organization requires SSO login.",
                    headers={
                        "X-SSO-Login-URL": f"/api/auth/saml/{user.org_id}/login",
                    },
                )
    except HTTPException:
        raise  # Re-raise SSO enforcement errors
    except Exception:
        # SSO check failed (table missing, connection issue, etc.) — allow login
        pass

    if not user.email_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Please verify your email before logging in")

    access = auth_service.create_access_token(str(user.id), str(user.org_id), user.role)
    refresh = auth_service.create_refresh_token(str(user.id))
    await auth_service.store_session(r, str(user.id), refresh)

    # Log successful login (fire-and-forget)
    try:
        await emit_auth_event(user.org_id, user.id, "login_success", message=f"User {user.email} logged in")
    except Exception:
        pass

    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    user = await auth_service.get_user_by_email(db, body.email)
    if user:
        token = secrets.token_urlsafe(48)
        user.reset_token = token
        user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        await db.flush()
        try:
            await email_service.send_password_reset_email(body.email, token)
        except Exception:
            pass
    # Always return success to prevent email enumeration
    return MessageResponse(message="If an account exists with that email, a password reset link has been sent.")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    _validate_password(body.password)

    result = await db.execute(
        select(User).where(User.reset_token == body.token)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    # Check token expiry
    if user.reset_token_expires_at and datetime.now(timezone.utc) > _ensure_utc_aware(user.reset_token_expires_at):
        user.reset_token = None
        user.reset_token_expires_at = None
        await db.flush()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token has expired. Please request a new one.")

    user.hashed_password = auth_service.hash_password(body.password)
    user.reset_token = None
    user.reset_token_expires_at = None
    await db.flush()

    return MessageResponse(message="Password reset successfully. You can now log in.")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    user = await auth_service.get_user_by_email(db, body.email)
    if user and not user.email_verified:
        token = secrets.token_urlsafe(48)
        user.verification_token = token
        user.verification_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        await db.flush()
        try:
            await email_service.send_verification_email(body.email, token)
        except Exception:
            pass
    return MessageResponse(message="If an unverified account exists with that email, a verification link has been sent.")


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
    refresh_tok = auth_service.create_refresh_token(str(user.id))
    await auth_service.store_session(r, str(user.id), refresh_tok)

    try:
        await emit_auth_event(user.org_id, user.id, "token_refresh", severity="debug", message="Token refreshed")
    except Exception:
        pass

    return TokenResponse(access_token=access, refresh_token=refresh_tok)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    user: User = Depends(get_current_user),
    r: redis_lib.Redis = Depends(get_redis),
):
    await auth_service.invalidate_session(r, str(user.id))

    try:
        await emit_auth_event(user.org_id, user.id, "logout", message=f"User {user.email} logged out")
    except Exception:
        pass


@router.get("/me")
async def me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return current user profile with organization details."""
    org_name = None
    try:
        result = await db.execute(
            select(Organization).where(Organization.id == user.org_id)
        )
        org = result.scalar_one_or_none()
        if org:
            org_name = org.name
    except Exception:
        pass

    # Check if user is a platform superadmin
    from app.core.config import settings
    admin_emails = [e.strip() for e in settings.admin_emails.split(",") if e.strip()]
    is_platform_admin = user.email in admin_emails

    return {
        "id": str(user.id),
        "org_id": str(user.org_id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "avatar_url": user.avatar_url,
        "email_verified": user.email_verified,
        "is_platform_admin": is_platform_admin,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "org": {"name": org_name} if org_name else None,
    }
