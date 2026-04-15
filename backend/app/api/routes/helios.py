"""
Helios API Routes — Sentry-style observability endpoints.

Base path: /api/helios
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
import uuid as uuid_lib

from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.helios import (
    helios_monitor,
    helios_store,
    Issue, Incident, AlertRule, AlertChannel,
    Severity, IncidentStatus, AlertStatus, AlertChannelType,
    create_issue_from_event,
    get_active_incidents, acknowledge_incident, resolve_incident,
)

router = APIRouter(prefix="/helios", tags=["helios"])


# ── Request/Response Models ────────────────────────────────────────────────

class AlertChannelCreate(BaseModel):
    name: str
    channel_type: str  # webhook, slack, email
    config: Dict[str, Any]  # {"webhook_url": "...", "email": "..."}


class AlertChannelResponse(BaseModel):
    id: str
    name: str
    channel_type: str
    created_at: str


class AlertRuleCreate(BaseModel):
    name: str
    log_type: str
    event_pattern: str
    severity_min: str = "error"
    count_threshold: int = 3
    time_window_seconds: int = 300
    channel_ids: List[str] = []
    heal_action: Optional[str] = None  # retry_deploy, rollback, notify_oncall


class AlertRuleResponse(BaseModel):
    id: str
    name: str
    log_type: str
    event_pattern: str
    severity_min: str
    count_threshold: int
    time_window_seconds: int
    channel_ids: List[str]
    status: str
    last_triggered_at: Optional[str]
    heal_action: Optional[str] = None


class IssueResponse(BaseModel):
    id: str
    fingerprint: str
    level: str
    title: str
    description: str
    first_seen: str
    last_seen: str
    event_count: int
    status: str
    log_type: str
    event_type: str
    metadata: Dict[str, Any]


class IncidentResponse(BaseModel):
    id: str
    rule_id: str
    issue_id: str
    org_id: str
    status: str
    severity: str
    title: str
    description: str
    detected_at: str
    acknowledged_at: Optional[str]
    resolved_at: Optional[str]
    event_count: int


class MonitorStatus(BaseModel):
    running: bool
    last_poll: Optional[str]


# ── Monitor Control ───────────────────────────────────────────────────────

@router.post("/monitor/start", status_code=status.HTTP_200_OK)
async def start_monitor(
    token: str,
    current_user: User = Depends(get_current_user),
):
    """Start the Helios background monitor."""
    await helios_monitor.start(token)
    return {"status": "started", "vercel_token_set": True}


@router.post("/monitor/stop", status_code=status.HTTP_200_OK)
async def stop_monitor(current_user: User = Depends(get_current_user)):
    """Stop the Helios background monitor."""
    await helios_monitor.stop()
    return {"status": "stopped"}


@router.get("/monitor/status", response_model=MonitorStatus)
async def monitor_status(current_user: User = Depends(get_current_user)):
    """Get current monitor running status."""
    last = helios_monitor._last_poll.isoformat() if helios_monitor._last_poll else None
    return {"running": helios_monitor._running, "last_poll": last}


# ── Issues ────────────────────────────────────────────────────────────────

@router.get("/issues", response_model=List[IssueResponse])
async def list_issues(
    status: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
):
    """List all issues (Sentry-style)."""
    issues = helios_store.list_issues(status=status, limit=limit)
    return [
        IssueResponse(
            id=str(i.id),
            fingerprint=i.fingerprint,
            level=i.level.value,
            title=i.title,
            description=i.description,
            first_seen=i.first_seen.isoformat(),
            last_seen=i.last_seen.isoformat(),
            event_count=i.event_count,
            status=i.status,
            log_type=i.log_type,
            event_type=i.event_type,
            metadata=i.metadata,
        )
        for i in issues
    ]


@router.get("/issues/{fingerprint}", response_model=IssueResponse)
async def get_issue(
    fingerprint: str,
    current_user: User = Depends(get_current_user),
):
    """Get a specific issue by fingerprint."""
    from app.services.helios.helios_sentry import get_issue_by_fingerprint
    issue = get_issue_by_fingerprint(fingerprint)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return IssueResponse(
        id=str(issue.id),
        fingerprint=issue.fingerprint,
        level=issue.level.value,
        title=issue.title,
        description=issue.description,
        first_seen=issue.first_seen.isoformat(),
        last_seen=issue.last_seen.isoformat(),
        event_count=issue.event_count,
        status=issue.status,
        log_type=issue.log_type,
        event_type=issue.event_type,
        metadata=issue.metadata,
    )


# ── Incidents ─────────────────────────────────────────────────────────────

@router.get("/incidents", response_model=List[IncidentResponse])
async def list_incidents(
    status: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
):
    """List all incidents (Sentry-style)."""
    status_enum = IncidentStatus(status) if status else None
    incidents = helios_store.list_incidents(status=status_enum, limit=limit)
    return [
        IncidentResponse(
            id=str(i.id),
            rule_id=str(i.rule_id),
            issue_id=str(i.issue_id),
            org_id=str(i.org_id),
            status=i.status.value,
            severity=i.severity.value,
            title=i.title,
            description=i.description,
            detected_at=i.detected_at.isoformat(),
            acknowledged_at=i.acknowledged_at.isoformat() if i.acknowledged_at else None,
            resolved_at=i.resolved_at.isoformat() if i.resolved_at else None,
            event_count=i.event_count,
        )
        for i in incidents
    ]


@router.post("/incidents/{incident_id}/acknowledge")
async def ack_incident(
    incident_id: str,
    current_user: User = Depends(get_current_user),
):
    """Acknowledge an incident."""
    incident = acknowledge_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"status": "acknowledged", "incident_id": incident_id}


@router.post("/incidents/{incident_id}/resolve")
async def res_incident(
    incident_id: str,
    current_user: User = Depends(get_current_user),
):
    """Resolve an incident."""
    incident = resolve_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"status": "resolved", "incident_id": incident_id}


# ── Alert Rules ───────────────────────────────────────────────────────────

@router.post("/alert-rules", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    rule_data: AlertRuleCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a new alert rule."""
    rule = AlertRule(
        id=uuid_lib.uuid4(),
        name=rule_data.name,
        org_id=current_user.org_id,
        log_type=rule_data.log_type,
        event_pattern=rule_data.event_pattern,
        severity_min=Severity(rule_data.severity_min),
        count_threshold=rule_data.count_threshold,
        time_window_seconds=rule_data.time_window_seconds,
        channel_ids=[UUID(cid) for cid in rule_data.channel_ids],
        status=AlertStatus.ACTIVE,
    )
    if rule_data.heal_action:
        rule.config = {"heal_action": rule_data.heal_action}
    helios_store.upsert_alert_rule(rule)
    return AlertRuleResponse(
        id=str(rule.id),
        name=rule.name,
        log_type=rule.log_type,
        event_pattern=rule.event_pattern,
        severity_min=rule.severity_min.value,
        count_threshold=rule.count_threshold,
        time_window_seconds=rule.time_window_seconds,
        channel_ids=[str(c) for c in rule.channel_ids],
        status=rule.status.value,
        last_triggered_at=rule.last_triggered_at.isoformat() if rule.last_triggered_at else None,
        heal_action=rule_data.heal_action,
    )


@router.get("/alert-rules", response_model=List[AlertRuleResponse])
async def list_rules(
    current_user: User = Depends(get_current_user),
):
    """List alert rules for this org."""
    rules = helios_store.list_alert_rules(org_id=current_user.org_id)
    return [
        AlertRuleResponse(
            id=str(r.id),
            name=r.name,
            log_type=r.log_type,
            event_pattern=r.event_pattern,
            severity_min=r.severity_min.value,
            count_threshold=r.count_threshold,
            time_window_seconds=r.time_window_seconds,
            channel_ids=[str(c) for c in r.channel_ids],
            status=r.status.value,
            last_triggered_at=r.last_triggered_at.isoformat() if r.last_triggered_at else None,
            heal_action=r.config.get("heal_action") if hasattr(r, "config") else None,
        )
        for r in rules
    ]


@router.delete("/alert-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete an alert rule."""
    rule = helios_store.get_alert_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    del helios_store._alert_rules[rule_id]
    return None


# ── Alert Channels ────────────────────────────────────────────────────────

@router.post("/alert-channels", response_model=AlertChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(
    channel_data: AlertChannelCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a new alert channel (webhook, Slack, email)."""
    channel = AlertChannel(
        id=uuid_lib.uuid4(),
        name=channel_data.name,
        channel_type=AlertChannelType(channel_data.channel_type),
        config=channel_data.config,
    )
    helios_store.upsert_alert_channel(channel)
    return AlertChannelResponse(
        id=str(channel.id),
        name=channel.name,
        channel_type=channel.channel_type.value,
        created_at=channel.created_at.isoformat(),
    )


@router.get("/alert-channels", response_model=List[AlertChannelResponse])
async def list_channels(current_user: User = Depends(get_current_user)):
    """List all alert channels."""
    channels = helios_store.list_alert_channels()
    return [
        AlertChannelResponse(
            id=str(c.id),
            name=c.name,
            channel_type=c.channel_type.value,
            created_at=c.created_at.isoformat(),
        )
        for c in channels
    ]


# ── Manual Event Ingest (for testing / direct agent use) ───────────────────

@router.post("/ingest", status_code=status.HTTP_201_CREATED)
async def ingest_event(
    event: Dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    """
    Manually ingest an event (e.g., from Bonoto agent error logs).
    Fire-and-forget — creates an issue immediately.
    """
    issue = create_issue_from_event(event)
    return {"issue_fingerprint": issue.fingerprint, "event_count": issue.event_count}


# ── Vercel Events (called by Vercel deploy hook or cron) ───────────────────

@router.post("/vercel/webhook", status_code=status.HTTP_200_OK)
async def vercel_webhook(
    payload: Dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    """
    Receive Vercel deployment notifications.
    Vercel webhook → parse → create issue.
    """
    deployment = payload.get("deployment", {})
    state = deployment.get("readyState", "")
    uid = deployment.get("uid", "")
    
    event = {
        "log_type": "deployment",
        "event_type": "deploy_" + state.lower() if state else "deploy_unknown",
        "severity": "error" if state == "ERROR" else "info",
        "message": f"Deployment {uid}: {state}",
        "metadata": {
            "deployment_id": uid,
            "url": deployment.get("url"),
            "error_state": deployment.get("errorState"),
        },
        "org_id": current_user.org_id,
    }
    
    issue = create_issue_from_event(event)
    return {"status": "processed", "fingerprint": issue.fingerprint}