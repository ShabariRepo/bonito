from fastapi import APIRouter, Query

from app.services.analytics import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
async def get_overview():
    return analytics_service.get_overview()


@router.get("/usage")
async def get_usage(period: str = Query("day", regex="^(day|week|month)$")):
    return analytics_service.get_usage(period)


@router.get("/costs")
async def get_cost_breakdown():
    return analytics_service.get_cost_breakdown()


@router.get("/trends")
async def get_trends():
    return analytics_service.get_trends()


@router.get("/digest")
async def get_digest():
    return analytics_service.get_weekly_digest()
