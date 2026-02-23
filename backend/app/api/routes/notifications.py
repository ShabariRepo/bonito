from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.schemas.notifications import (
    NotificationListResponse,
    UnreadCountResponse,
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertRuleResponse,
    NotificationPreferencesUpdate,
    NotificationPreferencesResponse,
)
from app.services.notifications import notification_service
from app.services.feature_gate import feature_gate

router = APIRouter(prefix="/notifications", tags=["notifications"])


async def _require_notifications(db: AsyncSession, user: User):
    """Check that the organization has access to the notifications feature."""
    await feature_gate.require_feature(db, str(user.org_id), "notifications")


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_notifications(db, user)
    return await notification_service.get_notifications(db, user.org_id, user.id, notification_type=type)


@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_notifications(db, user)
    result = await notification_service.mark_read(db, user.org_id, user.id, notification_id)
    if not result:
        raise HTTPException(status_code=404, detail="Notification not found")
    return result


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_notifications(db, user)
    count = await notification_service.get_unread_count(db, user.org_id, user.id)
    return {"count": count}


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_preferences(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_notifications(db, user)
    return await notification_service.get_preferences(db, user.id)


@router.put("/preferences", response_model=NotificationPreferencesResponse)
async def update_preferences(
    data: NotificationPreferencesUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_notifications(db, user)
    return await notification_service.update_preferences(db, user.id, data.model_dump(exclude_none=True))


# ─── Alert Rules ───

alert_router = APIRouter(prefix="/alert-rules", tags=["alert-rules"])


async def _require_budget_alerts(db: AsyncSession, user: User):
    """Check that the organization has access to the budget_alerts feature."""
    await feature_gate.require_feature(db, str(user.org_id), "budget_alerts")


@alert_router.get("", response_model=list[AlertRuleResponse])
async def list_alert_rules(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_budget_alerts(db, user)
    return await notification_service.get_alert_rules(db, user.org_id)


@alert_router.post("", response_model=AlertRuleResponse, status_code=201)
async def create_alert_rule(
    data: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_budget_alerts(db, user)
    return await notification_service.create_alert_rule(db, user.org_id, data.model_dump())


@alert_router.put("/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: str,
    data: AlertRuleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_budget_alerts(db, user)
    result = await notification_service.update_alert_rule(db, user.org_id, rule_id, data.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return result


@alert_router.delete("/{rule_id}", status_code=204)
async def delete_alert_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_budget_alerts(db, user)
    await notification_service.delete_alert_rule(db, user.org_id, rule_id)
