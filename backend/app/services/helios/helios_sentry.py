"""
Helios Core — Issue, Incident, AlertRule, AlertChannel models + in-memory store.

Mirrors Sentry's data model:
  - Issue: grouped event cluster (e.g., "all errors from /api/gateway")
  - Incident: active problem tracked from detection through resolution
  - AlertRule: condition + threshold that triggers an incident
  - AlertChannel: where to send alerts (Slack, PagerDuty, webhook, etc.)

Storage: in-memory dict (production would use the platform_logs table + Redis).
"""

from __future__ import annotations
import uuid
import logging
from enum import Enum
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from collections import defaultdict

logger = logging.getLogger("helios.core")


# ── Enums ──────────────────────────────────────────────────────────────────

class Severity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    @classmethod
    def from_str(cls, s: str) -> Severity:
        return cls(s.lower())

    @property
    def sentry_level(self) -> str:
        """Map to Sentry event.level."""
        return self.value


class IncidentStatus(str, Enum):
    DETECTED = "detected"   # Freshly created from alert trigger
    ACKNOWLEDGED = "acknowledged"  # Someone saw it
    RESOLVED = "resolved"   # Fixed / dismissed


class AlertStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class AlertChannelType(str, Enum):
    SLACK = "slack"
    WEBHOOK = "webhook"
    PAGERDUTY = "pagerduty"
    EMAIL = "email"


# ── Data Models ────────────────────────────────────────────────────────────

@dataclass
class AlertChannel:
    id: uuid.UUID
    name: str
    channel_type: AlertChannelType
    config: Dict[str, Any]  # webhook_url, email, etc.
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AlertRule:
    id: uuid.UUID
    name: str
    org_id: uuid.UUID
    # Condition
    log_type: str  # e.g., "deployment", "gateway"
    event_pattern: str  # e.g., "error", "crash", "BUILD_FAILED"
    severity_min: Severity = Severity.ERROR
    # Threshold
    count_threshold: int = 3       # N events in window
    time_window_seconds: int = 300  # ...within this window
    # Self-healing action (retry_deploy, rollback, notify_oncall)
    heal_action: Optional[str] = None
    # Action
    channel_ids: List[uuid.UUID] = field(default_factory=list)
    status: AlertStatus = AlertStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_triggered_at: Optional[datetime] = None


@dataclass
class Issue:
    """
    A grouped cluster of related events — like a Sentry Issue.

    id, fingerprint, first_seen, last_seen, event_count,
    level (max severity), title, description, metadata
    """
    id: uuid.UUID
    fingerprint: str  # Groups events: "vercel/deploy/error/[deployment_id]"
    log_type: str
    event_type: str
    level: Severity
    title: str        # e.g., "Vercel deployment failed: build step error"
    description: str   # e.g., "Deployment dpl_xxx failed with exit code 1"
    first_seen: datetime
    last_seen: datetime
    event_count: int = 1
    seen_in_orgs: List[uuid.UUID] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "open"  # open, resolved, ignored

    def to_sentry_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "fingerprint": self.fingerprint,
            "level": self.level.sentry_level,
            "title": self.title,
            "description": self.description,
            "firstSeen": self.first_seen.isoformat(),
            "lastSeen": self.last_seen.isoformat(),
            "count": self.event_count,
            "status": self.status,
            "metadata": self.metadata,
            "logType": self.log_type,
            "eventType": self.event_type,
        }


@dataclass
class Incident:
    """
    An active problem being tracked — like a Sentry Incident.

    Created when an AlertRule's threshold is breached.
    Resolved manually or auto-resolved when the root cause clears.
    """
    id: uuid.UUID
    rule_id: uuid.UUID
    issue_id: uuid.UUID
    org_id: uuid.UUID
    status: IncidentStatus
    severity: Severity
    title: str
    description: str
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    event_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_sentry_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "ruleId": str(self.rule_id),
            "issueId": str(self.issue_id),
            "orgId": str(self.org_id),
            "status": self.status.value,
            "severity": self.severity.sentry_level,
            "title": self.title,
            "description": self.description,
            "detectedAt": self.detected_at.isoformat(),
            "acknowledgedAt": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolvedAt": self.resolved_at.isoformat() if self.resolved_at else None,
            "eventCount": self.event_count,
            "metadata": self.metadata,
        }


# ── In-memory store (production: DB + Redis) ───────────────────────────────

class HeliosStore:
    """
    Thread-safe in-memory store for issues and incidents.
    
    Production: replace with DB-backed store using platform_logs + Redis.
    """

    def __init__(self):
        self._issues: Dict[str, Issue] = {}  # fingerprint -> Issue
        self._incidents: Dict[str, Incident] = {}  # id -> Incident
        self._alert_rules: Dict[str, AlertRule] = {}  # id -> AlertRule
        self._alert_channels: Dict[str, AlertChannel] = {}  # id -> AlertChannel

    def upsert_issue(self, issue: Issue) -> Issue:
        self._issues[issue.fingerprint] = issue
        return issue

    def get_issue(self, fingerprint: str) -> Optional[Issue]:
        return self._issues.get(fingerprint)

    def list_issues(self, status: Optional[str] = None, limit: int = 100) -> List[Issue]:
        issues = list(self._issues.values())
        if status:
            issues = [i for i in issues if i.status == status]
        issues.sort(key=lambda i: i.last_seen, reverse=True)
        return issues[:limit]

    def upsert_incident(self, incident: Incident) -> Incident:
        self._incidents[str(incident.id)] = incident
        return incident

    def get_incident(self, id: str) -> Optional[Incident]:
        return self._incidents.get(id)

    def list_incidents(self, status: Optional[IncidentStatus] = None, limit: int = 100) -> List[Incident]:
        incidents = list(self._incidents.values())
        if status:
            incidents = [i for i in incidents if i.status == status]
        incidents.sort(key=lambda i: i.detected_at, reverse=True)
        return incidents[:limit]

    def upsert_alert_rule(self, rule: AlertRule) -> AlertRule:
        self._alert_rules[str(rule.id)] = rule
        return rule

    def get_alert_rule(self, id: str) -> Optional[AlertRule]:
        return self._alert_rules.get(id)

    def list_alert_rules(self, org_id: Optional[uuid.UUID] = None) -> List[AlertRule]:
        rules = list(self._alert_rules.values())
        if org_id:
            rules = [r for r in rules if r.org_id == org_id]
        return rules

    def upsert_alert_channel(self, channel: AlertChannel) -> AlertChannel:
        self._alert_channels[str(channel.id)] = channel
        return channel

    def get_alert_channel(self, id: str) -> Optional[AlertChannel]:
        return self._alert_channels.get(id)

    def list_alert_channels(self) -> List[AlertChannel]:
        return list(self._alert_channels.values())


# Singleton store
_helios_store = HeliosStore()


# ── Public API ─────────────────────────────────────────────────────────────

def get_store() -> HeliosStore:
    return _helios_store


def _make_fingerprint(log_type: str, event_type: str, org_id: uuid.UUID, **extra: Any) -> str:
    """Create a stable event fingerprint for grouping."""
    key = "/".join(filter(None, [log_type, event_type, str(org_id)]))
    if extra:
        # Sort and include extra keys that matter for grouping
        important = [f"{k}={extra[k]}" for k in sorted(extra) if extra[k] and k in ("deployment_id", "region", "error_code")]
        if important:
            key = f"{key}/{'/'.join(important)}"
    return key


def create_issue_from_event(event: Dict[str, Any]) -> Issue:
    """
    Group an incoming event into an Issue (or update existing).

    This is the core "issue fingerprinting" logic — mirrors Sentry's grouping.
    """
    log_type = event.get("log_type", "unknown")
    event_type = event.get("event_type", "unknown")
    org_id = event.get("org_id")
    severity = Severity.from_str(event.get("severity", "info"))

    # Build fingerprint key
    extra = {}
    for key in ("deployment_id", "region", "error_code", "build_step"):
        if key in event.get("metadata", {}):
            extra[key] = event["metadata"][key]

    fingerprint = _make_fingerprint(log_type, event_type, org_id, **extra)

    now = datetime.now(timezone.utc)

    # Check if issue already exists
    existing = _helios_store.get_issue(fingerprint)

    if existing:
        # Update existing issue
        existing.last_seen = now
        existing.event_count += 1
        if severity.value > existing.level.value:
            existing.level = severity
        # Update description with latest
        if event.get("message"):
            existing.description = event["message"][:500]
        if "metadata" in event:
            existing.metadata.update(event["metadata"])
        return existing

    # Create new issue
    title = event.get("message", f"{log_type}/{event_type}")
    if len(title) > 200:
        title = title[:197] + "..."

    new_issue = Issue(
        id=uuid.uuid4(),
        fingerprint=fingerprint,
        log_type=log_type,
        event_type=event_type,
        level=severity,
        title=title,
        description=event.get("message", "")[:500] if event.get("message") else "",
        first_seen=now,
        last_seen=now,
        event_count=1,
        metadata=event.get("metadata", {}),
        status="open",
    )

    if org_id:
        new_issue.seen_in_orgs = [org_id]

    return _helios_store.upsert_issue(new_issue)


def create_incident(rule: AlertRule, issue: Issue, org_id: uuid.UUID) -> Incident:
    """Fire a new incident from a triggered alert rule."""
    incident = Incident(
        id=uuid.uuid4(),
        rule_id=rule.id,
        issue_id=issue.id,
        org_id=org_id,
        status=IncidentStatus.DETECTED,
        severity=issue.level,
        title=f"[Alert] {rule.name}: {issue.title}",
        description=issue.description,
        metadata={"rule_name": rule.name, "issue_fingerprint": issue.fingerprint},
    )
    return _helios_store.upsert_incident(incident)


def get_active_incidents(org_id: Optional[uuid.UUID] = None) -> List[Incident]:
    incidents = _helios_store.list_incidents(status=IncidentStatus.DETECTED)
    incidents += _helios_store.list_incidents(status=IncidentStatus.ACKNOWLEDGED)
    if org_id:
        incidents = [i for i in incidents if i.org_id == org_id]
    return incidents


def acknowledge_incident(incident_id: str) -> Optional[Incident]:
    incident = _helios_store.get_incident(incident_id)
    if not incident:
        return None
    incident.status = IncidentStatus.ACKNOWLEDGED
    incident.acknowledged_at = datetime.now(timezone.utc)
    return _helios_store.upsert_incident(incident)


def resolve_incident(incident_id: str) -> Optional[Incident]:
    incident = _helios_store.get_incident(incident_id)
    if not incident:
        return None
    incident.status = IncidentStatus.RESOLVED
    incident.resolved_at = datetime.now(timezone.utc)
    return _helios_store.upsert_incident(incident)


def get_issue_by_fingerprint(fingerprint: str) -> Optional[Issue]:
    return _helios_store.get_issue(fingerprint)