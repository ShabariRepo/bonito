from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.analytics import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


async def _require_analytics(db: AsyncSession, user: User):
    """Check that the organization has access to the analytics feature."""
    from app.services.feature_gate import feature_gate
    await feature_gate.require_feature(db, str(user.org_id), "analytics")


@router.get("/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_analytics(db, user)
    return await analytics_service.get_overview(db, user.org_id)


@router.get("/usage")
async def get_usage(
    period: str = Query("day", regex="^(day|week|month)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_analytics(db, user)
    return await analytics_service.get_usage(db, user.org_id, period)


@router.get("/costs")
async def get_cost_breakdown(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_analytics(db, user)
    return await analytics_service.get_cost_breakdown(db, user.org_id)


@router.get("/trends")
async def get_trends(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_analytics(db, user)
    return await analytics_service.get_trends(db, user.org_id)


@router.get("/digest")
async def get_digest(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_analytics(db, user)
    return await analytics_service.get_weekly_digest(db, user.org_id)
