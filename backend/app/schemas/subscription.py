from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel


class SubscriptionResponse(BaseModel):
    tier: str
    status: str
    bonobot_plan: str
    bonobot_agent_limit: int
    tier_limits: Dict[str, Any]
    usage: Dict[str, Any]


class SubscriptionUpdateRequest(BaseModel):
    org_id: str
    tier: Optional[str] = None
    status: Optional[str] = None
    bonobot_plan: Optional[str] = None
    bonobot_agent_limit: Optional[int] = None
    reason: Optional[str] = None
    notes: Optional[str] = None


class UsageResponse(BaseModel):
    usage: Dict[str, Any]


class TierComparisonResponse(BaseModel):
    current_tier: str
    tiers: Dict[str, Any]


class FeatureAccessResponse(BaseModel):
    feature: str
    has_access: bool
    current_tier: str
    required_tier: Optional[str]
    upgrade_url: Optional[str]


class SubscriptionHistoryResponse(BaseModel):
    id: str
    previous_tier: Optional[str]
    new_tier: str
    previous_status: Optional[str]
    new_status: str
    previous_bonobot_plan: Optional[str]
    new_bonobot_plan: str
    previous_bonobot_agent_limit: Optional[int]
    new_bonobot_agent_limit: int
    changed_by_user_id: Optional[str]
    reason: Optional[str]
    notes: Optional[str]
    created_at: datetime