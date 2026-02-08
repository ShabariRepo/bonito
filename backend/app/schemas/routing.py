from datetime import datetime
from uuid import UUID
from typing import Optional, List

from pydantic import BaseModel


class RoutingRuleCreate(BaseModel):
    name: str
    strategy: str
    conditions_json: dict = {}
    priority: int = 0
    enabled: bool = True


class RoutingRuleUpdate(BaseModel):
    name: Optional[str] = None
    strategy: Optional[str] = None
    conditions_json: Optional[dict] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None


class RoutingRuleResponse(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    strategy: str
    conditions_json: dict
    priority: int
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SimulationRequest(BaseModel):
    prompt_description: str
    model_type: str = "chat"
    max_cost_per_token: Optional[float] = None
    preferred_region: Optional[str] = None


class ProviderOption(BaseModel):
    provider: str
    model: str
    estimated_latency_ms: int
    cost_per_1k_tokens: float
    region: str
    selected: bool
    reason: str


class SimulationResult(BaseModel):
    selected_provider: str
    selected_model: str
    strategy_used: str
    decision_path: List[str]
    options: List[ProviderOption]
    estimated_cost_savings_pct: float
    estimated_latency_ms: int


class RoutingAnalytics(BaseModel):
    total_requests: int
    requests_by_provider: dict
    cost_savings_pct: float
    avg_latency_ms: float
    latency_by_provider: dict
    routing_distribution: dict
