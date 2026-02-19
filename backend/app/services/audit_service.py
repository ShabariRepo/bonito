"""Audit logging service with real audit trail + mock seed data."""

import uuid
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog

logger = logging.getLogger(__name__)


async def log_audit_event(
    db: AsyncSession,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
    org_id: Optional[uuid.UUID] = None,
    details: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_name: Optional[str] = None,
) -> uuid.UUID:
    """Write a real audit log entry. Returns the audit log ID."""
    entry = AuditLog(
        org_id=org_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details_json=details or {},
        ip_address=ip_address,
        user_name=user_name,
    )
    db.add(entry)
    await db.flush()
    logger.info("Audit: %s %s %s (org=%s)", action, resource_type, resource_id, org_id)
    return entry.id

MOCK_USERS = [
    {"id": "10000000-0000-0000-0000-000000000001", "name": "Sarah Chen", "email": "sarah@bonito.ai"},
    {"id": "10000000-0000-0000-0000-000000000002", "name": "Marcus Johnson", "email": "marcus@bonito.ai"},
    {"id": "10000000-0000-0000-0000-000000000003", "name": "Aisha Patel", "email": "aisha@bonito.ai"},
    {"id": "10000000-0000-0000-0000-000000000004", "name": "David Kim", "email": "david@bonito.ai"},
]

MOCK_AUDIT_EVENTS = [
    {"action": "create", "resource_type": "provider", "details": {"provider": "AWS Bedrock", "region": "us-east-1"}},
    {"action": "create", "resource_type": "provider", "details": {"provider": "Azure OpenAI", "region": "eastus"}},
    {"action": "create", "resource_type": "deployment", "details": {"model": "GPT-4o", "provider": "azure", "endpoint": "prod-gpt4o"}},
    {"action": "create", "resource_type": "deployment", "details": {"model": "Claude 3.5 Sonnet", "provider": "aws", "endpoint": "prod-claude"}},
    {"action": "update", "resource_type": "policy", "details": {"policy": "Daily Spend Limit", "change": "limit increased to $1000"}},
    {"action": "create", "resource_type": "policy", "details": {"policy": "Model Access Control", "rule": "GPT-4 restricted to Engineering"}},
    {"action": "create", "resource_type": "user", "details": {"email": "new@bonito.ai", "role": "viewer"}},
    {"action": "update", "resource_type": "user", "details": {"email": "marcus@bonito.ai", "role_change": "viewer → editor"}},
    {"action": "delete", "resource_type": "deployment", "details": {"model": "PaLM 2", "reason": "deprecated"}},
    {"action": "access", "resource_type": "api_key", "details": {"key_prefix": "sk-bon-***", "action": "rotated"}},
    {"action": "update", "resource_type": "provider", "details": {"provider": "GCP Vertex AI", "change": "credentials refreshed"}},
    {"action": "access", "resource_type": "audit_log", "details": {"exported_records": 150, "format": "csv"}},
    {"action": "create", "resource_type": "provider", "details": {"provider": "GCP Vertex AI", "project": "bonito-prod"}},
    {"action": "delete", "resource_type": "policy", "details": {"policy": "Legacy Region Lock", "reason": "no longer needed"}},
    {"action": "update", "resource_type": "deployment", "details": {"model": "GPT-4o", "change": "scaled to 3 replicas"}},
    {"action": "access", "resource_type": "model", "details": {"model": "Claude 3.5 Sonnet", "action": "benchmark run"}},
]

IPS = ["10.0.1.42", "10.0.1.87", "10.0.2.15", "192.168.1.100", "10.0.3.201"]


def generate_mock_audit_logs(count: int = 50, org_id: str | None = None) -> list:
    """Generate mock audit log entries.

    Args:
        count: Number of entries to generate.
        org_id: The organization ID to associate with entries.
                If not provided, entries will have a None org_id.
    """
    random.seed(123)
    logs = []
    now = datetime.now(timezone.utc)
    for i in range(count):
        event = random.choice(MOCK_AUDIT_EVENTS)
        user = random.choice(MOCK_USERS)
        logs.append({
            "id": str(uuid.uuid4()),
            "org_id": org_id,
            "user_id": user["id"],
            "user_name": user["name"],
            "action": event["action"],
            "resource_type": event["resource_type"],
            "resource_id": str(uuid.uuid4())[:8],
            "details_json": event["details"],
            "ip_address": random.choice(IPS),
            "created_at": (now - timedelta(hours=i * 2, minutes=random.randint(0, 59))).isoformat(),
        })
    random.seed()
    return logs
