from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.analytics import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
async def get_overview(user: User = Depends(get_current_user)):
    return analytics_service.get_overview()


@router.get("/usage")
async def get_usage(period: str = Query("day", regex="^(day|week|month)$"), user: User = Depends(get_current_user)):
    return analytics_service.get_usage(period)


@router.get("/costs")
async def get_cost_breakdown(user: User = Depends(get_current_user)):
    return analytics_service.get_cost_breakdown()


@router.get("/trends")
async def get_trends(user: User = Depends(get_current_user)):
    return analytics_service.get_trends()


@router.get("/digest")
async def get_digest(user: User = Depends(get_current_user)):
    return analytics_service.get_weekly_digest()
