from datetime import datetime
from uuid import UUID
from typing import Optional, List

from pydantic import BaseModel


# ─── Notifications ───

class NotificationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    org_id: UUID
    user_id: UUID
    type: str
    title: str
    body: str
    read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    count: int


# ─── Alert Rules ───

class AlertRuleCreate(BaseModel):
    type: str  # budget_threshold, compliance_violation, model_deprecation
    threshold: Optional[float] = None
    channel: str = "in_app"  # email, webhook, in_app
    enabled: bool = True


class AlertRuleUpdate(BaseModel):
    type: Optional[str] = None
    threshold: Optional[float] = None
    channel: Optional[str] = None
    enabled: Optional[bool] = None


class AlertRuleResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    org_id: UUID
    type: str
    threshold: Optional[float]
    channel: str
    enabled: bool
    created_at: datetime


# ─── Preferences ───

class NotificationPreferencesUpdate(BaseModel):
    weekly_digest: Optional[bool] = None
    cost_alerts: Optional[bool] = None
    compliance_alerts: Optional[bool] = None
    model_updates: Optional[bool] = None


class NotificationPreferencesResponse(BaseModel):
    weekly_digest: bool
    cost_alerts: bool
    compliance_alerts: bool
    model_updates: bool
