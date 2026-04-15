"""
Helios Monitor — async periodic log fetcher + alert evaluator.

Polls Vercel API for deployment events, detects errors, creates Issues,
evaluates AlertRules, fires Incidents, and optionally triggers self-healing.

Usage:
    from app.services.helios import helios_monitor

    # On app startup:
    await helios_monitor.start()

    # On app shutdown:
    await helios_monitor.stop()
"""

import asyncio
import logging
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from app.services.helios.helios_sentry import (
    helios_store, Severity, AlertStatus,
    create_issue_from_event, create_incident,
    Issue, Incident, AlertRule,
)
from app.services.helios.vercel_client import VercelClient

logger = logging.getLogger("helios.monitor")

POLL_INTERVAL_SECONDS = 60  # Check every minute
INCIDENT_COOLDOWN_SECONDS = 300  # Don't fire same rule twice within 5 min


class HeliosMonitor:
    """
    Periodic monitor that:
      1. Fetches deployment logs from Vercel
      2. Detects errors and creates Issues
      3. Evaluates AlertRules → fires Incidents
      4. Triggers self-healing actions if configured
    """

    def __init__(self):
        self._vercel_client: Optional[VercelClient] = None
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._last_poll: Optional[datetime] = None
        self._incident_cooldowns: Dict[str, datetime] = {}  # rule_id -> last_fired

    async def start(self, vercel_token: str):
        if self._running:
            return
        self._vercel_client = VercelClient(vercel_token)
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Helios monitor started (poll every %ds)", POLL_INTERVAL_SECONDS)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Helios monitor stopped")

    async def _run_loop(self):
        while self._running:
            try:
                await self._poll()
            except Exception as e:
                logger.error("Helios poll error: %s", e)
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    async def _poll(self):
        """Fetch events from all configured sources and process."""
        if not self._vercel_client:
            logger.warning("No Vercel client configured, skipping poll")
            return

        logger.debug("Polling Vercel for deployment events...")
        
        # Fetch recent deployments
        deployments = await self._vercel_client.list_deployments(limit=10)
        
        for deployment in deployments:
            events = await self._process_deployment(deployment)
            
            for event in events:
                await self._process_event(event)

        self._last_poll = datetime.now(timezone.utc)

    async def _process_deployment(self, deployment: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract events from a Vercel deployment."""
        uid = deployment.get("uid", "")
        state = deployment.get("readyState", "")
        error_state = deployment.get("errorState", "")
        created = deployment.get("created", 0)
        created_dt = datetime.fromtimestamp(created / 1000, tz=timezone.utc) if created else datetime.now(timezone.utc)
        
        events = []
        
        # Normal state transitions
        if state == "READY":
            events.append({
                "log_type": "deployment",
                "event_type": "deploy_succeeded",
                "severity": "info",
                "message": f"Deployment {uid} succeeded",
                "metadata": {
                    "deployment_id": uid,
                    "deployment_url": deployment.get("url"),
                    "commit_sha": deployment.get("meta", {}).get("githubCommitSha"),
                    "branch": deployment.get("meta", {}).get("githubCommitRef"),
                    "creator": deployment.get("creator", {}).get("email"),
                },
                "created_at": created_dt,
                "org_id": None,  # Will be filled from context
            })
        elif state == "ERROR":
            events.append({
                "log_type": "deployment",
                "event_type": "deploy_failed",
                "severity": "error",
                "message": f"Deployment {uid} failed: {error_state}",
                "metadata": {
                    "deployment_id": uid,
                    "deployment_url": deployment.get("url"),
                    "error_state": error_state,
                    "commit_sha": deployment.get("meta", {}).get("githubCommitSha"),
                    "branch": deployment.get("meta", {}).get("githubCommitRef"),
                },
                "created_at": created_dt,
                "org_id": None,
            })
        elif state == "BUILDING":
            events.append({
                "log_type": "deployment",
                "event_type": "deploy_started",
                "severity": "info",
                "message": f"Deployment {uid} started",
                "metadata": {
                    "deployment_id": uid,
                    "branch": deployment.get("meta", {}).get("githubCommitRef"),
                },
                "created_at": created_dt,
                "org_id": None,
            })

        return events

    async def _process_event(self, event: Dict[str, Any]):
        """Process a single event: create issue, evaluate alert rules."""
        try:
            # Create or update issue
            issue = create_issue_from_event(event)
            logger.debug(
                "Issue %s: %s (count=%d, level=%s)",
                issue.fingerprint[:40], issue.title[:60], issue.event_count, issue.level.value
            )

            # Only alert on warning+ events
            if issue.level.value not in ("error", "critical", "warning"):
                return

            # Evaluate alert rules
            await self._evaluate_alert_rules(issue, event)

        except Exception as e:
            logger.error("Error processing event: %s", e)

    async def _evaluate_alert_rules(self, issue: Issue, event: Dict[str, Any]):
        """Check if any AlertRule matches this issue, fire incidents if thresholds met."""
        org_id = event.get("org_id") or uuid4()
        rules = helios_store.list_alert_rules(org_id=org_id)

        for rule in rules:
            if rule.status != AlertStatus.ACTIVE:
                continue

            # Does this rule match this event?
            if rule.log_type and rule.log_type != issue.log_type:
                continue

            if rule.event_pattern and rule.event_pattern not in issue.event_type and rule.event_pattern not in issue.title:
                continue

            if issue.level.value not in ("error", "critical", "warning"):
                continue

            # Threshold check (simplified — production would track counts per window)
            # For now: fire if severity is error/critical and event_count >= threshold
            if issue.event_count < rule.count_threshold:
                continue

            # Cooldown check
            cooldown_key = str(rule.id)
            last_fired = self._incident_cooldowns.get(cooldown_key)
            if last_fired:
                elapsed = (datetime.now(timezone.utc) - last_fired).total_seconds()
                if elapsed < INCIDENT_COOLDOWN_SECONDS:
                    logger.debug("Rule %s still in cooldown (%.0fs remaining)", rule.name, INCIDENT_COOLDOWN_SECONDS - elapsed)
                    continue

            # Fire incident
            incident = create_incident(rule, issue, org_id)
            self._incident_cooldowns[cooldown_key] = datetime.now(timezone.utc)

            logger.warning(
                "INCIDENT FIRED: %s — %s (severity=%s, events=%d)",
                incident.title, issue.description[:80], issue.level.value, issue.event_count
            )

            # Dispatch to alert channels
            await self._dispatch_alert(rule, incident, issue)

            # Trigger self-healing if configured
            await self._maybe_heal(rule, event, incident)

    async def _dispatch_alert(self, rule: AlertRule, incident: Incident, issue: Issue):
        """Send incident to configured alert channels."""
        channels = [helios_store.get_alert_channel(str(cid)) for cid in rule.channel_ids]
        channels = [c for c in channels if c is not None]

        if not channels:
            logger.debug("No alert channels configured for rule %s", rule.name)
            return

        payload = {
            "incident": incident.to_sentry_dict(),
            "issue": issue.to_sentry_dict(),
            "rule": {"id": str(rule.id), "name": rule.name},
        }

        for channel in channels:
            try:
                if channel.channel_type.value == "webhook":
                    await self._send_webhook_alert(channel, payload)
                elif channel.channel_type.value == "slack":
                    await self._send_slack_alert(channel, payload)
                elif channel.channel_type.value == "email":
                    await self._send_email_alert(channel, payload)
            except Exception as e:
                logger.error("Failed to dispatch alert to %s: %s", channel.name, e)

    async def _send_webhook_alert(self, channel: AlertChannel, payload: Dict[str, Any]):
        url = channel.config.get("webhook_url")
        if not url:
            return
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(url, json=payload)

    async def _send_slack_alert(self, channel: AlertChannel, payload: Dict[str, Any]):
        webhook_url = channel.config.get("webhook_url")
        if not webhook_url:
            return
        incident = payload["incident"]
        issue = payload["issue"]
        text = (
            f":rotating_light: *Incident: {incident['title']}*\n"
            f"*Severity:* `{incident['severity']}` | *Status:* `{incident['status']}`\n"
            f"*Issue:* {issue['title']}\n"
            f"*Count:* {issue['count']} events | *Detected:* {incident['detectedAt']}\n"
            f"<https://app.getbonito.com/helios/incidents/{incident['id']}|View in Helios>"
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(webhook_url, json={"text": text})

    async def _send_email_alert(self, channel: AlertChannel, payload: Dict[str, Any]):
        # Placeholder — integrate with Bonito's email_service
        logger.info("Email alert would be sent to %s", channel.config.get("email", ""))

    async def _maybe_heal(self, rule: AlertRule, event: Dict[str, Any], incident: Incident):
        """Run a corrective action if the rule has one configured."""
        heal_action = rule.heal_action
        if not heal_action:
            return

        deployment_id = event.get("metadata", {}).get("deployment_id")
        logger.info("Running self-heal action '%s' for incident %s", heal_action, incident.id)

        if heal_action == "retry_deploy" and deployment_id:
            # Retry the failed deployment via Vercel API
            if self._vercel_client:
                try:
                    await self._vercel_client.retry_deployment(deployment_id)
                    logger.info("Triggered deployment retry for %s", deployment_id)
                except Exception as e:
                    logger.error("Failed to retry deployment %s: %s", deployment_id, e)

        elif heal_action == "rollback":
            if self._vercel_client:
                try:
                    await self._vercel_client.rollback(deployment_id)
                    logger.info("Triggered rollback for %s", deployment_id)
                except Exception as e:
                    logger.error("Failed to rollback %s: %s", deployment_id, e)

        elif heal_action == "notify_oncall":
            logger.info("Would notify on-call for %s", incident.id)


# ── Singleton ─────────────────────────────────────────────────────────────

helios_monitor = HeliosMonitor()