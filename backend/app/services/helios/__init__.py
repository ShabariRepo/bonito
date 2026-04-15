"""
Helios — Sentry-style Observability & Self-Healing Layer for Bonito.

Architecture:
  - Monitor: periodically fetches Vercel deploy logs, detects errors
  - Issues: grouped event clusters (like Sentry issues)
  - Incidents: active problems requiring attention
  - AlertRules + AlertChannels: configurable alerting
  - AgentExecutor: runs corrective actions via Bonoto agents

Usage:
    from app.services.helios.helios_monitor import helios_monitor
    await helios_monitor.start()
"""

from .helios_monitor import helios_monitor
from .helios_sentry import (
    Issue, Incident, AlertRule, AlertChannel,
    AlertStatus, IncidentStatus, Severity,
    create_issue_from_event,
    get_active_incidents,
    acknowledge_incident,
    resolve_incident,
)

__all__ = [
    "helios_monitor",
    "Issue", "Incident", "AlertRule", "AlertChannel",
    "AlertStatus", "IncidentStatus", "Severity",
    "create_issue_from_event",
    "get_active_incidents",
    "acknowledge_incident",
    "resolve_incident",
]