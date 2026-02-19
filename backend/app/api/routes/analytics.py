from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user, require_feature
from app.models.user import User
from app.services.analytics import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_feature("analytics")),
):
    return await analytics_service.get_overview(db, user.org_id)


@router.get("/usage")
async def get_usage(
    period: str = Query("day", regex="^(day|week|month)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_feature("analytics")),
):
    return await analytics_service.get_usage(db, user.org_id, period)


@router.get("/costs")
async def get_cost_breakdown(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_feature("analytics")),
):
    return await analytics_service.get_cost_breakdown(db, user.org_id)


@router.get("/trends")
async def get_trends(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_feature("analytics")),
):
    return await analytics_service.get_trends(db, user.org_id)


@router.get("/digest")
async def get_digest(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_feature("analytics")),
):
    return await analytics_service.get_weekly_digest(db, user.org_id)
