from typing import Optional

from fastapi import APIRouter, Query, HTTPException

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

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=NotificationListResponse)
async def list_notifications(type: Optional[str] = Query(None)):
    return notification_service.get_notifications(notification_type=type)


@router.put("/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    result = notification_service.mark_read(notification_id)
    if not result:
        raise HTTPException(status_code=404, detail="Notification not found")
    return result


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count():
    return {"count": notification_service.get_unread_count()}


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_preferences():
    return notification_service.get_preferences()


@router.put("/preferences", response_model=NotificationPreferencesResponse)
async def update_preferences(data: NotificationPreferencesUpdate):
    return notification_service.update_preferences(data.model_dump(exclude_none=True))


# ─── Alert Rules ───

alert_router = APIRouter(prefix="/alert-rules", tags=["alert-rules"])


@alert_router.get("/", response_model=list[AlertRuleResponse])
async def list_alert_rules():
    return notification_service.get_alert_rules()


@alert_router.post("/", response_model=AlertRuleResponse, status_code=201)
async def create_alert_rule(data: AlertRuleCreate):
    return notification_service.create_alert_rule(data.model_dump())


@alert_router.put("/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(rule_id: str, data: AlertRuleUpdate):
    result = notification_service.update_alert_rule(rule_id, data.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return result


@alert_router.delete("/{rule_id}", status_code=204)
async def delete_alert_rule(rule_id: str):
    notification_service.delete_alert_rule(rule_id)
