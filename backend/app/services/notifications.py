"""Notification service — in-app notifications with pluggable email/webhook delivery.

All notification/alert-rule/preference data is now backed by the database.
"""

import uuid
import logging
from typing import Optional, Protocol

import httpx
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notifications import Notification, AlertRule, NotificationPreference

logger = logging.getLogger(__name__)


# ─── Pluggable email backend ───

class EmailBackend(Protocol):
    async def send(self, to: str, subject: str, body: str) -> bool: ...


class SMTPEmailBackend:
    """Placeholder SMTP backend. Configure with real SMTP settings in production."""

    def __init__(self, host: str = "localhost", port: int = 587, username: str = "", password: str = ""):
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    async def send(self, to: str, subject: str, body: str) -> bool:
        logger.info(f"[EMAIL] Would send to={to} subject={subject} (SMTP not configured)")
        return True


class NoopEmailBackend:
    async def send(self, to: str, subject: str, body: str) -> bool:
        logger.info(f"[EMAIL-NOOP] to={to} subject={subject}")
        return True


# ─── Webhook delivery ───

async def deliver_webhook(url: str, payload: dict) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            return resp.status_code < 400
    except Exception as e:
        logger.error(f"[WEBHOOK] Failed to deliver to {url}: {e}")
        return False


# ─── Notification service ───

class NotificationService:
    def __init__(self, email_backend: Optional[EmailBackend] = None):
        self.email_backend = email_backend or NoopEmailBackend()

    # ─── Notifications ───

    async def get_notifications(
        self, db: AsyncSession, org_id, user_id, notification_type: Optional[str] = None
    ) -> dict:
        query = (
            select(Notification)
            .where(Notification.org_id == org_id, Notification.user_id == user_id)
        )
        if notification_type:
            query = query.where(Notification.type == notification_type)
        query = query.order_by(Notification.created_at.desc())

        result = await db.execute(query)
        items = result.scalars().all()

        unread_q = await db.execute(
            select(func.count(Notification.id)).where(
                Notification.org_id == org_id,
                Notification.user_id == user_id,
                Notification.read == False,  # noqa: E712
            )
        )
        unread_count = unread_q.scalar_one() or 0

        return {"items": items, "total": len(items), "unread_count": unread_count}

    async def mark_read(self, db: AsyncSession, org_id, user_id, notification_id: str):
        result = await db.execute(
            select(Notification).where(
                Notification.id == uuid.UUID(notification_id),
                Notification.org_id == org_id,
                Notification.user_id == user_id,
            )
        )
        notification = result.scalar_one_or_none()
        if not notification:
            return None
        notification.read = True
        await db.flush()
        await db.refresh(notification)
        return notification

    async def create_notification(
        self,
        db: AsyncSession,
        org_id,
        user_id,
        type: str,
        title: str,
        body: str,
    ) -> Notification:
        """Create an in-app notification for a user."""
        notification = Notification(
            id=uuid.uuid4(),
            org_id=org_id,
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            read=False,
        )
        db.add(notification)
        await db.flush()
        await db.refresh(notification)
        return notification

    async def notify_org_admins(
        self,
        db: AsyncSession,
        org_id,
        type: str,
        title: str,
        body: str,
    ):
        """Send a notification to all users in the org."""
        from app.models.user import User as UserModel
        result = await db.execute(
            select(UserModel.id).where(UserModel.org_id == org_id)
        )
        user_ids = result.scalars().all()
        for uid in user_ids:
            await self.create_notification(db, org_id, uid, type, title, body)

        # Check alert rules for webhook/email delivery
        rules = await self.get_alert_rules(db, org_id)
        for rule in rules:
            if not rule.enabled:
                continue
            # Match rule type to notification type
            type_map = {
                "budget_threshold": "cost_alert",
                "compliance_violation": "compliance_alert",
                "model_deprecation": "model_deprecation",
                "deployment_status": "deployment_alert",
                "gateway_error": "gateway_alert",
            }
            if type_map.get(rule.type) == type or rule.type == type:
                if rule.channel == "webhook" and hasattr(rule, 'webhook_url'):
                    await self.send_webhook(
                        getattr(rule, 'webhook_url', ''),
                        {"type": type, "title": title, "body": body, "org_id": str(org_id)},
                    )
                elif rule.channel == "email":
                    # Email would go to org admin emails
                    logger.info(f"[ALERT-EMAIL] Would email org {org_id}: {title}")

    async def get_unread_count(self, db: AsyncSession, org_id, user_id) -> int:
        result = await db.execute(
            select(func.count(Notification.id)).where(
                Notification.org_id == org_id,
                Notification.user_id == user_id,
                Notification.read == False,  # noqa: E712
            )
        )
        return result.scalar_one() or 0

    # ─── Alert Rules ───

    async def get_alert_rules(self, db: AsyncSession, org_id) -> list:
        result = await db.execute(
            select(AlertRule)
            .where(AlertRule.org_id == org_id)
            .order_by(AlertRule.created_at)
        )
        return result.scalars().all()

    async def create_alert_rule(self, db: AsyncSession, org_id, data: dict):
        rule = AlertRule(
            id=uuid.uuid4(),
            org_id=org_id,
            type=data["type"],
            threshold=data.get("threshold"),
            channel=data.get("channel", "in_app"),
            enabled=data.get("enabled", True),
        )
        db.add(rule)
        await db.flush()
        await db.refresh(rule)
        return rule

    async def update_alert_rule(self, db: AsyncSession, org_id, rule_id: str, data: dict):
        result = await db.execute(
            select(AlertRule).where(
                AlertRule.id == uuid.UUID(rule_id),
                AlertRule.org_id == org_id,
            )
        )
        rule = result.scalar_one_or_none()
        if not rule:
            return None
        for k, v in data.items():
            if v is not None and hasattr(rule, k):
                setattr(rule, k, v)
        await db.flush()
        await db.refresh(rule)
        return rule

    async def delete_alert_rule(self, db: AsyncSession, org_id, rule_id: str) -> bool:
        result = await db.execute(
            select(AlertRule).where(
                AlertRule.id == uuid.UUID(rule_id),
                AlertRule.org_id == org_id,
            )
        )
        rule = result.scalar_one_or_none()
        if not rule:
            return False
        await db.delete(rule)
        await db.flush()
        return True

    # ─── Preferences ───

    async def get_preferences(self, db: AsyncSession, user_id) -> dict:
        result = await db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        pref = result.scalar_one_or_none()
        if not pref:
            # Return defaults
            return {
                "weekly_digest": True,
                "cost_alerts": True,
                "compliance_alerts": True,
                "model_updates": True,
            }
        return {
            "weekly_digest": pref.weekly_digest,
            "cost_alerts": pref.cost_alerts,
            "compliance_alerts": pref.compliance_alerts,
            "model_updates": pref.model_updates,
        }

    async def update_preferences(self, db: AsyncSession, user_id, data: dict) -> dict:
        result = await db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        pref = result.scalar_one_or_none()
        if not pref:
            pref = NotificationPreference(user_id=user_id)
            db.add(pref)
        for k, v in data.items():
            if v is not None and hasattr(pref, k):
                setattr(pref, k, v)
        await db.flush()
        await db.refresh(pref)
        return {
            "weekly_digest": pref.weekly_digest,
            "cost_alerts": pref.cost_alerts,
            "compliance_alerts": pref.compliance_alerts,
            "model_updates": pref.model_updates,
        }

    # ─── Delivery helpers ───

    async def send_email(self, to: str, subject: str, body: str) -> bool:
        return await self.email_backend.send(to, subject, body)

    async def send_webhook(self, url: str, payload: dict) -> bool:
        return await deliver_webhook(url, payload)


# Singleton
notification_service = NotificationService()
