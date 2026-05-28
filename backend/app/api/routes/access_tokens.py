"""Personal Access Tokens (bp-) and Project Tokens (bj-) CRUD."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user, require_pro_or_enterprise, require_admin
from app.models.user import User
from app.schemas.access_token import (
    AccessTokenCreate,
    ProjectTokenCreate,
    AccessTokenResponse,
    AccessTokenCreated,
)
from app.services import access_token_service

router = APIRouter()

# ── PAT tier limits (active, non-revoked) ──
PAT_LIMITS = {"free": 2, "starter": 5, "pro": 10, "enterprise": 999, "scale": 999}


# ─────────────────── Personal Access Tokens ───────────────────


@router.get("/tokens", response_model=list[AccessTokenResponse])
async def list_tokens(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tokens = await access_token_service.list_user_tokens(db, user.id)
    return tokens


@router.post("/tokens", response_model=AccessTokenCreated, status_code=status.HTTP_201_CREATED)
async def create_token(
    body: AccessTokenCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check tier limit
    from app.services.feature_gate import feature_gate

    sub = await feature_gate.get_organization_subscription(db, str(user.org_id))
    tier = sub["tier"].value
    limit = PAT_LIMITS.get(tier, 2)
    count = await access_token_service.count_user_tokens(db, user.id)
    if count >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"PAT limit reached ({count}/{limit}). Upgrade your plan for more.",
        )

    token, raw = await access_token_service.create_personal_token(
        db=db,
        user=user,
        name=body.name,
        scopes=body.scopes,
        expires_in_days=body.expires_in_days,
        rate_limit=body.rate_limit,
    )
    await db.commit()
    return AccessTokenCreated(
        id=token.id,
        token_type=token.token_type,
        name=token.name,
        token_prefix=token.token_prefix,
        scopes=token.scopes,
        rate_limit=token.rate_limit,
        expires_at=token.expires_at,
        last_used_at=token.last_used_at,
        created_at=token.created_at,
        revoked_at=token.revoked_at,
        created_by_id=token.created_by_id,
        project_id=token.project_id,
        token=raw,
    )


@router.delete("/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_token(
    token_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    token = await access_token_service.revoke_token(db, token_id, user.org_id)
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    await db.commit()


# ─────────────────── Project Tokens ───────────────────


@router.get("/projects/{project_id}/tokens", response_model=list[AccessTokenResponse])
async def list_project_tokens(
    project_id: uuid.UUID,
    user: User = Depends(require_pro_or_enterprise),
    db: AsyncSession = Depends(get_db),
):
    tokens = await access_token_service.list_project_tokens(db, project_id, user.org_id)
    return tokens


@router.post(
    "/projects/{project_id}/tokens",
    response_model=AccessTokenCreated,
    status_code=status.HTTP_201_CREATED,
)
async def create_project_token(
    project_id: uuid.UUID,
    body: ProjectTokenCreate,
    user: User = Depends(require_pro_or_enterprise),
    db: AsyncSession = Depends(get_db),
):
    # Only org admins can create project tokens
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can create project tokens",
        )
    # Verify project belongs to org
    from app.models.project import Project
    from sqlalchemy import select

    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.org_id == user.org_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    token, raw = await access_token_service.create_project_token(
        db=db,
        user=user,
        project_id=project_id,
        name=body.name,
        expires_in_days=body.expires_in_days,
        rate_limit=body.rate_limit,
    )
    await db.commit()
    return AccessTokenCreated(
        id=token.id,
        token_type=token.token_type,
        name=token.name,
        token_prefix=token.token_prefix,
        scopes=token.scopes,
        rate_limit=token.rate_limit,
        expires_at=token.expires_at,
        last_used_at=token.last_used_at,
        created_at=token.created_at,
        revoked_at=token.revoked_at,
        created_by_id=token.created_by_id,
        project_id=token.project_id,
        token=raw,
    )


@router.delete("/projects/{project_id}/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_project_token(
    project_id: uuid.UUID,
    token_id: uuid.UUID,
    user: User = Depends(require_pro_or_enterprise),
    db: AsyncSession = Depends(get_db),
):
    # Only org admins can revoke project tokens
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can revoke project tokens",
        )
    token = await access_token_service.revoke_token(db, token_id, user.org_id)
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    await db.commit()
