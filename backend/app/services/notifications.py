"""Notification service — in-app notifications with pluggable email/webhook delivery."""

import uuid
import logging
from datetime import datetime
from typing import Optional, Protocol

import httpx

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

    # ─── Mock data for demo ───

    _mock_notifications = [
        {
            "id": str(uuid.uuid4()),
            "org_id": "00000000-0000-0000-0000-000000000001",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "type": "cost_alert",
            "title": "Budget threshold reached",
            "body": "Your organization has used 85% of the monthly budget ($8,500 of $10,000).",
            "read": False,
            "created_at": "2026-02-08T10:00:00Z",
        },
        {
            "id": str(uuid.uuid4()),
            "org_id": "00000000-0000-0000-0000-000000000001",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "type": "model_deprecation",
            "title": "GPT-4 Turbo deprecation notice",
            "body": "OpenAI will deprecate gpt-4-turbo on March 15, 2026. Consider migrating to gpt-4o.",
            "read": False,
            "created_at": "2026-02-07T14:30:00Z",
        },
        {
            "id": str(uuid.uuid4()),
            "org_id": "00000000-0000-0000-0000-000000000001",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "type": "compliance_alert",
            "title": "Data residency policy violation",
            "body": "3 requests were routed to a non-EU region, violating your GDPR data residency policy.",
            "read": True,
            "created_at": "2026-02-06T09:15:00Z",
        },
        {
            "id": str(uuid.uuid4()),
            "org_id": "00000000-0000-0000-0000-000000000001",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "type": "digest",
            "title": "Weekly digest — Feb 1–7",
            "body": "This week: 12,450 requests, $4,230 spend (+8% vs last week). Top model: Claude 3.5 Sonnet (45% of traffic).",
            "read": True,
            "created_at": "2026-02-03T08:00:00Z",
        },
        {
            "id": str(uuid.uuid4()),
            "org_id": "00000000-0000-0000-0000-000000000001",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "type": "cost_alert",
            "title": "Unusual spending spike",
            "body": "Daily spend jumped 340% on Feb 5 ($1,200 vs $350 average). Review recent usage for anomalies.",
            "read": False,
            "created_at": "2026-02-05T16:45:00Z",
        },
    ]

    _mock_alert_rules = [
        {
            "id": str(uuid.uuid4()),
            "org_id": "00000000-0000-0000-0000-000000000001",
            "type": "budget_threshold",
            "threshold": 80.0,
            "channel": "in_app",
            "enabled": True,
            "created_at": "2026-01-15T10:00:00Z",
        },
        {
            "id": str(uuid.uuid4()),
            "org_id": "00000000-0000-0000-0000-000000000001",
            "type": "budget_threshold",
            "threshold": 95.0,
            "channel": "email",
            "enabled": True,
            "created_at": "2026-01-15T10:00:00Z",
        },
        {
            "id": str(uuid.uuid4()),
            "org_id": "00000000-0000-0000-0000-000000000001",
            "type": "compliance_violation",
            "threshold": None,
            "channel": "in_app",
            "enabled": True,
            "created_at": "2026-01-20T12:00:00Z",
        },
        {
            "id": str(uuid.uuid4()),
            "org_id": "00000000-0000-0000-0000-000000000001",
            "type": "model_deprecation",
            "threshold": None,
            "channel": "in_app",
            "enabled": False,
            "created_at": "2026-01-20T12:00:00Z",
        },
    ]

    _mock_preferences = {
        "weekly_digest": True,
        "cost_alerts": True,
        "compliance_alerts": True,
        "model_updates": True,
    }

    def get_notifications(self, notification_type: Optional[str] = None):
        items = list(self._mock_notifications)
        if notification_type:
            items = [n for n in items if n["type"] == notification_type]
        items.sort(key=lambda x: x["created_at"], reverse=True)
        unread = sum(1 for n in self._mock_notifications if not n["read"])
        return {"items": items, "total": len(items), "unread_count": unread}

    def mark_read(self, notification_id: str):
        for n in self._mock_notifications:
            if n["id"] == notification_id:
                n["read"] = True
                return n
        return None

    def get_unread_count(self):
        return sum(1 for n in self._mock_notifications if not n["read"])

    def get_alert_rules(self):
        return list(self._mock_alert_rules)

    def create_alert_rule(self, data: dict):
        rule = {
            "id": str(uuid.uuid4()),
            "org_id": "00000000-0000-0000-0000-000000000001",
            "type": data["type"],
            "threshold": data.get("threshold"),
            "channel": data.get("channel", "in_app"),
            "enabled": data.get("enabled", True),
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        self._mock_alert_rules.append(rule)
        return rule

    def update_alert_rule(self, rule_id: str, data: dict):
        for rule in self._mock_alert_rules:
            if rule["id"] == rule_id:
                for k, v in data.items():
                    if v is not None:
                        rule[k] = v
                return rule
        return None

    def delete_alert_rule(self, rule_id: str):
        self._mock_alert_rules[:] = [r for r in self._mock_alert_rules if r["id"] != rule_id]
        return True

    def get_preferences(self):
        return dict(self._mock_preferences)

    def update_preferences(self, data: dict):
        for k, v in data.items():
            if v is not None and k in self._mock_preferences:
                self._mock_preferences[k] = v
        return dict(self._mock_preferences)

    async def send_email(self, to: str, subject: str, body: str) -> bool:
        return await self.email_backend.send(to, subject, body)

    async def send_webhook(self, url: str, payload: dict) -> bool:
        return await deliver_webhook(url, payload)


# Singleton
notification_service = NotificationService()
