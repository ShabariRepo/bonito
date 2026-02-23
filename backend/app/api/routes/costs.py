"""Cost intelligence routes — real multi-cloud cost data."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.cost_service import (
    get_cost_summary_real,
    get_cost_breakdown_real,
    get_cost_forecast_real,
    get_optimization_recommendations,
)
from app.api.dependencies import get_current_user
from app.models.user import User
from app.schemas.cost import CostSummary, CostBreakdownResponse, CostForecastResponse
from app.services.feature_gate import feature_gate

router = APIRouter(prefix="/costs", tags=["costs"])


async def _require_budget_alerts(db: AsyncSession, user: User):
    """Check that the organization has access to the budget_alerts feature."""
    await feature_gate.require_feature(db, str(user.org_id), "budget_alerts")


@router.get("", response_model=CostSummary)
async def get_costs(
    period: str = Query("monthly", enum=["daily", "weekly", "monthly"]),
    budget: float = Query(40000.0, description="Budget amount for percentage calculation"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get unified cost summary across all connected providers."""
    await _require_budget_alerts(db, user)
    return await get_cost_summary_real(period, db, budget)


@router.get("/breakdown", response_model=CostBreakdownResponse)
async def costs_breakdown(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Get cost breakdown by provider, model/service, and department."""
    await _require_budget_alerts(db, user)
    return await get_cost_breakdown_real(db)


@router.get("/forecast", response_model=CostForecastResponse)
async def costs_forecast(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Get cost forecast based on real historical trends."""
    await _require_budget_alerts(db, user)
    return await get_cost_forecast_real(db)


@router.get("/recommendations")
async def cost_recommendations(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Get cost optimization recommendations."""
    await _require_budget_alerts(db, user)
    return await get_optimization_recommendations(db)
