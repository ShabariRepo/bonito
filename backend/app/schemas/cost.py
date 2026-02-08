from datetime import date, datetime
from uuid import UUID
from typing import Optional, List

from pydantic import BaseModel


class DailyCost(BaseModel):
    date: str
    amount: float
    provider: Optional[str] = None


class ProviderCostBreakdown(BaseModel):
    provider: str
    total: float
    percentage: float
    color: str


class ModelCostBreakdown(BaseModel):
    model: str
    provider: str
    total: float
    requests: int


class DepartmentCostBreakdown(BaseModel):
    department: str
    total: float
    percentage: float


class CostSummary(BaseModel):
    total_spend: float
    period: str
    daily_costs: List[DailyCost]
    budget: float
    budget_used_percentage: float
    change_percentage: float


class CostBreakdownResponse(BaseModel):
    by_provider: List[ProviderCostBreakdown]
    by_model: List[ModelCostBreakdown]
    by_department: List[DepartmentCostBreakdown]
    total: float


class ForecastPoint(BaseModel):
    date: str
    projected: float
    lower_bound: float
    upper_bound: float


class CostForecastResponse(BaseModel):
    current_monthly_spend: float
    projected_monthly_spend: float
    forecast: List[ForecastPoint]
    savings_opportunity: float
    trend: str  # "increasing", "decreasing", "stable"
