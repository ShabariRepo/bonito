"""
Platform admin API routes.

All endpoints require superadmin access (email in ADMIN_EMAILS env var).
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func, delete, and_, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import require_superadmin
from app.models.user import User
from app.models.organization import Organization
from app.models.cloud_provider import CloudProvider
from app.services.log_emitters import emit_admin_event
from app.models.deployment import Deployment
from app.models.gateway import GatewayRequest, GatewayKey

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------- Schemas ----------

class OrgSummary(BaseModel):
    id: str
    name: str
    user_count: int
    provider_count: int
    deployment_count: int
    total_requests: int
    total_cost: float
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class OrgDetail(BaseModel):
    id: str
    name: str
    created_at: Optional[str] = None
    users: list[dict]
    providers: list[dict]
    deployments: list[dict]


class AdminUserSummary(BaseModel):
    id: str
    email: str
    name: str
    org_id: str
    org_name: str
    role: str
    email_verified: bool
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    role: Optional[str] = None
    suspended: Optional[bool] = None


class PlatformStats(BaseModel):
    total_orgs: int
    total_users: int
    total_requests: int
    total_cost: float
    requests_by_day: list[dict]
    active_orgs: list[dict]


# ---------- Organizations ----------

@router.get("/organizations")
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_superadmin),
):
    """List all organizations with aggregated stats."""
    # Get all orgs
    orgs_result = await db.execute(select(Organization).order_by(Organization.created_at.desc()))
    orgs = orgs_result.scalars().all()

    summaries = []
    for org in orgs:
        # User count
        user_count_result = await db.execute(
            select(func.count(User.id)).where(User.org_id == org.id)
        )
        user_count = user_count_result.scalar() or 0

        # Provider count
        provider_count_result = await db.execute(
            select(func.count(CloudProvider.id)).where(CloudProvider.org_id == org.id)
        )
        provider_count = provider_count_result.scalar() or 0

        # Deployment count
        deployment_count_result = await db.execute(
            select(func.count(Deployment.id)).where(Deployment.org_id == org.id)
        )
        deployment_count = deployment_count_result.scalar() or 0

        # Gateway stats
        gateway_stats_result = await db.execute(
            select(
                func.count(GatewayRequest.id),
                func.coalesce(func.sum(GatewayRequest.cost), 0.0),
            ).where(GatewayRequest.org_id == org.id)
        )
        row = gateway_stats_result.one()
        total_requests = row[0] or 0
        total_cost = float(row[1] or 0.0)

        summaries.append({
            "id": str(org.id),
            "name": org.name,
            "user_count": user_count,
            "provider_count": provider_count,
            "deployment_count": deployment_count,
            "total_requests": total_requests,
            "total_cost": total_cost,
            "created_at": org.created_at.isoformat() if org.created_at else None,
        })

    return summaries


@router.get("/organizations/{org_id}")
async def get_organization(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_superadmin),
):
    """Get detailed information about a specific organization."""
    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Users
    users_result = await db.execute(
        select(User).where(User.org_id == org_id).order_by(User.created_at)
    )
    users = [
        {
            "id": str(u.id),
            "email": u.email,
            "name": u.name,
            "role": u.role,
            "email_verified": u.email_verified,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users_result.scalars().all()
    ]

    # Providers
    providers_result = await db.execute(
        select(CloudProvider).where(CloudProvider.org_id == org_id).order_by(CloudProvider.created_at)
    )
    providers = [
        {
            "id": str(p.id),
            "provider_type": p.provider_type,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in providers_result.scalars().all()
    ]

    # Deployments
    deployments_result = await db.execute(
        select(Deployment).where(Deployment.org_id == org_id).order_by(Deployment.created_at)
    )
    deployments = [
        {
            "id": str(d.id),
            "status": d.status,
            "config": d.config,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in deployments_result.scalars().all()
    ]

    return {
        "id": str(org.id),
        "name": org.name,
        "created_at": org.created_at.isoformat() if org.created_at else None,
        "users": users,
        "providers": providers,
        "deployments": deployments,
    }


@router.delete("/organizations/{org_id}", status_code=204)
async def delete_organization(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_superadmin),
):
    """Delete an organization and all associated data."""
    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Delete in order: gateway requests, gateway keys, deployments, providers, users, org
    await db.execute(delete(GatewayRequest).where(GatewayRequest.org_id == org_id))
    await db.execute(delete(GatewayKey).where(GatewayKey.org_id == org_id))
    await db.execute(delete(Deployment).where(Deployment.org_id == org_id))
    await db.execute(delete(CloudProvider).where(CloudProvider.org_id == org_id))
    await db.execute(delete(User).where(User.org_id == org_id))
    await db.delete(org)
    await db.flush()


# ---------- Users ----------

@router.get("/users")
async def list_all_users(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_superadmin),
):
    """List all users across all organizations."""
    result = await db.execute(
        select(User, Organization.name.label("org_name"))
        .join(Organization, User.org_id == Organization.id)
        .order_by(User.created_at.desc())
    )

    users = []
    for row in result.all():
        user = row[0]
        org_name = row[1]
        users.append({
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "org_id": str(user.org_id),
            "org_name": org_name,
            "role": user.role,
            "email_verified": user.email_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        })

    return users


@router.patch("/users/{user_id}")
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_superadmin),
):
    """Update a user's role or suspension status."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.role is not None:
        if body.role not in ("admin", "editor", "viewer"):
            raise HTTPException(status_code=422, detail="Invalid role. Must be admin, editor, or viewer.")
        user.role = body.role

    # suspended flag — we don't have a dedicated column, so we use email_verified
    # as a proxy for suspension (unverified = can't log in)
    if body.suspended is not None:
        user.email_verified = not body.suspended

    await db.flush()

    # Log admin action
    try:
        changes = {}
        if body.role is not None:
            changes["role"] = body.role
        if body.suspended is not None:
            changes["suspended"] = body.suspended
        await emit_admin_event(
            user.org_id, "user_update", user_id=_admin.id,
            resource_id=user.id, resource_type="user", action="update",
            message=f"Admin updated user {user.email}",
            metadata={"target_email": user.email, "changes": changes},
        )
    except Exception:
        pass

    # Fetch org name for response
    org_result = await db.execute(select(Organization.name).where(Organization.id == user.org_id))
    org_name = org_result.scalar() or "Unknown"

    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "org_id": str(user.org_id),
        "org_name": org_name,
        "role": user.role,
        "email_verified": user.email_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.post("/users/{user_id}/verify", response_model=dict)
async def verify_user_email(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_superadmin),
):
    """Admin: force-verify a user's email."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.email_verified = True
    await db.flush()

    return {"id": str(user.id), "email": user.email, "email_verified": True}


@router.post("/users/verify-by-email", response_model=dict)
async def verify_user_by_email(
    body: dict,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_superadmin),
):
    """Admin: force-verify a user by email address."""
    email = body.get("email")
    if not email:
        raise HTTPException(status_code=422, detail="email required")
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.email_verified = True
    await db.flush()

    return {"id": str(user.id), "email": user.email, "email_verified": True}


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_superadmin),
):
    """Delete a user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.flush()


# ---------- Platform Stats ----------

@router.get("/stats")
async def get_platform_stats(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_superadmin),
):
    """Get platform-wide statistics."""
    # Total orgs
    org_count = (await db.execute(select(func.count(Organization.id)))).scalar() or 0

    # Total users
    user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0

    # Total gateway requests and cost
    gateway_totals = await db.execute(
        select(
            func.count(GatewayRequest.id),
            func.coalesce(func.sum(GatewayRequest.cost), 0.0),
        )
    )
    totals_row = gateway_totals.one()
    total_requests = totals_row[0] or 0
    total_cost = float(totals_row[1] or 0.0)

    # Requests by day (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    daily_result = await db.execute(
        select(
            cast(GatewayRequest.created_at, Date).label("date"),
            func.count(GatewayRequest.id).label("requests"),
            func.coalesce(func.sum(GatewayRequest.cost), 0.0).label("cost"),
        )
        .where(GatewayRequest.created_at >= thirty_days_ago)
        .group_by(cast(GatewayRequest.created_at, Date))
        .order_by(cast(GatewayRequest.created_at, Date))
    )
    requests_by_day = [
        {"date": str(row.date), "requests": row.requests, "cost": float(row.cost)}
        for row in daily_result.all()
    ]

    # Active orgs (had requests in last 7 days)
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    active_orgs_result = await db.execute(
        select(
            Organization.id,
            Organization.name,
            func.count(GatewayRequest.id).label("recent_requests"),
        )
        .join(GatewayRequest, GatewayRequest.org_id == Organization.id)
        .where(GatewayRequest.created_at >= seven_days_ago)
        .group_by(Organization.id, Organization.name)
        .order_by(func.count(GatewayRequest.id).desc())
    )
    active_orgs = [
        {"id": str(row.id), "name": row.name, "recent_requests": row.recent_requests}
        for row in active_orgs_result.all()
    ]

    return {
        "total_orgs": org_count,
        "total_users": user_count,
        "total_requests": total_requests,
        "total_cost": total_cost,
        "requests_by_day": requests_by_day,
        "active_orgs": active_orgs,
    }


# ---------- Knowledge Base ----------

@router.get("/kb")
async def list_kb_articles(
    _admin: User = Depends(require_superadmin),
):
    """List all knowledge base articles."""
    from app.services.kb_content import get_all_articles
    return get_all_articles()


@router.get("/kb/{slug}")
async def get_kb_article(
    slug: str,
    _admin: User = Depends(require_superadmin),
):
    """Get a single knowledge base article by slug."""
    from app.services.kb_content import get_article_by_slug
    article = get_article_by_slug(slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article
