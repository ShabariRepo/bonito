from datetime import datetime
from uuid import UUID
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, field_validator


class ModelConfiguration(BaseModel):
    model_id: UUID
    weight: Optional[int] = 50  # For A/B testing
    role: str = "primary"  # primary, fallback


class RoutingRules(BaseModel):
    max_cost_per_request: Optional[float] = None
    max_tokens: Optional[int] = None
    allowed_capabilities: Optional[List[str]] = None
    region_preference: Optional[str] = None


class RoutingPolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    strategy: str = Field(..., pattern="^(cost_optimized|latency_optimized|balanced|failover|ab_test)$")
    models: List[ModelConfiguration] = Field(..., min_length=1)
    rules: RoutingRules = Field(default_factory=RoutingRules)
    is_active: bool = True

    @field_validator('models')
    @classmethod
    def validate_models(cls, v, info):
        if not v:
            raise ValueError("At least one model configuration is required")
        
        strategy = info.data.get('strategy')
        if strategy == 'failover' and len(v) < 2:
            raise ValueError("Failover strategy requires at least 2 models")
        
        if strategy == 'ab_test':
            total_weight = sum(model.weight or 0 for model in v)
            if total_weight != 100:
                raise ValueError("A/B test weights must sum to 100")
        
        return v


class RoutingPolicyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    strategy: Optional[str] = Field(None, pattern="^(cost_optimized|latency_optimized|balanced|failover|ab_test)$")
    models: Optional[List[ModelConfiguration]] = None
    rules: Optional[RoutingRules] = None
    is_active: Optional[bool] = None

    @field_validator('models')
    @classmethod
    def validate_models(cls, v, info):
        if v is not None:
            if not v:
                raise ValueError("At least one model configuration is required")
            
            strategy = info.data.get('strategy')
            if strategy == 'failover' and len(v) < 2:
                raise ValueError("Failover strategy requires at least 2 models")
            
            if strategy == 'ab_test':
                total_weight = sum(model.weight or 0 for model in v)
                if total_weight != 100:
                    raise ValueError("A/B test weights must sum to 100")
        
        return v


class RoutingPolicyResponse(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    description: Optional[str]
    strategy: str
    models: List[Dict[str, Any]]  # Will be converted from JSON
    rules: Dict[str, Any]  # Will be converted from JSON
    is_active: bool
    api_key_prefix: str
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class RoutingPolicyDetailResponse(RoutingPolicyResponse):
    model_names: Dict[str, str]  # model_id -> display_name mapping


class PolicyTestRequest(BaseModel):
    prompt: str
    context: Optional[str] = None
    max_tokens: Optional[int] = None


class PolicyTestResult(BaseModel):
    selected_model_id: UUID
    selected_model_name: str
    strategy_used: str
    selection_reason: str
    estimated_cost: Optional[float] = None
    estimated_latency_ms: Optional[int] = None


class PolicyStats(BaseModel):
    policy_id: UUID
    request_count: int
    total_cost: float
    avg_latency_ms: float
    success_rate: float
    last_24h_requests: int
    model_distribution: Dict[str, int]  # model_id -> request_count