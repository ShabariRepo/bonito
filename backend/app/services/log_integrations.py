"""
External log integration service.

Manages dispatching logs to external destinations (Datadog, Splunk, CloudWatch, etc.).
Each integration type implements send_logs() and test_connection().
"""

import logging
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import UUID

import httpx

logger = logging.getLogger("bonito.log_integrations")


# ── Base Integration ──

class BaseLogIntegration(ABC):
    """Base class for all log integration providers."""

    def __init__(self, config: Dict[str, Any], credentials: Dict[str, Any]):
        self.config = config
        self.credentials = credentials

    @abstractmethod
    async def send_logs(self, logs: List[Dict[str, Any]]) -> bool:
        """Send a batch of log entries. Returns True on success."""
        ...

    @abstractmethod
    async def test_connection(self) -> tuple[bool, str]:
        """Test the integration. Returns (success, message)."""
        ...

    def _format_log(self, log: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a PlatformLog dict to a standard format for the provider."""
        return {
            "timestamp": log.get("created_at", datetime.now(timezone.utc).isoformat()),
            "org_id": str(log.get("org_id", "")),
            "log_type": log.get("log_type", ""),
            "event_type": log.get("event_type", ""),
            "severity": log.get("severity", "info"),
            "message": log.get("message", ""),
            "user_id": str(log.get("user_id", "")) if log.get("user_id") else None,
            "resource_type": log.get("resource_type"),
            "resource_id": str(log.get("resource_id", "")) if log.get("resource_id") else None,
            "action": log.get("action"),
            "duration_ms": log.get("duration_ms"),
            "cost": log.get("cost"),
            "trace_id": str(log.get("trace_id", "")) if log.get("trace_id") else None,
            "metadata": log.get("metadata", {}),
        }


# ── Datadog Integration ──

class DatadogIntegration(BaseLogIntegration):
    """Datadog Logs API integration (v2/logs)."""

    SEVERITY_MAP = {
        "debug": "debug",
        "info": "info",
        "warn": "warning",
        "error": "error",
        "critical": "critical",
    }

    async def send_logs(self, logs: List[Dict[str, Any]]) -> bool:
        api_key = self.credentials.get("api_key", "")
        site = self.config.get("site", "datadoghq.com")
        source = self.config.get("source", "bonito")
        service = self.config.get("service", "bonito-platform")
        tags = self.config.get("tags", "")

        url = f"https://http-intake.logs.{site}/api/v2/logs"

        entries = []
        for log in logs:
            formatted = self._format_log(log)
            entries.append({
                "ddsource": source,
                "ddtags": f"env:{self.config.get('env', 'production')},log_type:{formatted['log_type']},{tags}".rstrip(","),
                "hostname": "bonito-platform",
                "service": service,
                "status": self.SEVERITY_MAP.get(formatted["severity"], "info"),
                "message": json.dumps({
                    "event_type": formatted["event_type"],
                    "message": formatted["message"],
                    "org_id": formatted["org_id"],
                    "user_id": formatted["user_id"],
                    "resource_type": formatted["resource_type"],
                    "resource_id": formatted["resource_id"],
                    "action": formatted["action"],
                    "duration_ms": formatted["duration_ms"],
                    "cost": formatted["cost"],
                    "trace_id": formatted["trace_id"],
                    **formatted["metadata"],
                }),
            })

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    url,
                    json=entries,
                    headers={
                        "DD-API-KEY": api_key,
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code in (200, 202):
                    return True
                logger.warning(f"Datadog send failed ({resp.status_code}): {resp.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Datadog send error: {e}")
            return False

    async def test_connection(self) -> tuple[bool, str]:
        api_key = self.credentials.get("api_key", "")
        site = self.config.get("site", "datadoghq.com")

        if not api_key:
            return False, "API key is required"

        url = f"https://api.{site}/api/v1/validate"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers={"DD-API-KEY": api_key})
                if resp.status_code == 200:
                    return True, "Connected to Datadog successfully"
                return False, f"Datadog validation failed (HTTP {resp.status_code})"
        except Exception as e:
            return False, f"Connection error: {str(e)}"


# ── Splunk HEC Integration ──

class SplunkIntegration(BaseLogIntegration):
    """Splunk HTTP Event Collector integration."""

    async def send_logs(self, logs: List[Dict[str, Any]]) -> bool:
        hec_url = self.config.get("hec_url", "")
        token = self.credentials.get("hec_token", "")
        index = self.config.get("index", "main")
        source = self.config.get("source", "bonito")
        sourcetype = self.config.get("sourcetype", "bonito:platform_log")

        if not hec_url or not token:
            logger.warning("Splunk HEC URL or token not configured")
            return False

        # Splunk HEC supports batching via newline-delimited JSON
        payload_lines = []
        for log in logs:
            formatted = self._format_log(log)
            event = {
                "time": int(datetime.fromisoformat(formatted["timestamp"]).timestamp()) if formatted.get("timestamp") else int(time.time()),
                "host": "bonito-platform",
                "source": source,
                "sourcetype": sourcetype,
                "index": index,
                "event": {
                    "log_type": formatted["log_type"],
                    "event_type": formatted["event_type"],
                    "severity": formatted["severity"],
                    "message": formatted["message"],
                    "org_id": formatted["org_id"],
                    "user_id": formatted["user_id"],
                    "resource_type": formatted["resource_type"],
                    "resource_id": formatted["resource_id"],
                    "action": formatted["action"],
                    "duration_ms": formatted["duration_ms"],
                    "cost": formatted["cost"],
                    "trace_id": formatted["trace_id"],
                    "metadata": formatted["metadata"],
                },
            }
            payload_lines.append(json.dumps(event))

        try:
            # Use /services/collector endpoint
            url = hec_url.rstrip("/")
            if not url.endswith("/services/collector"):
                url += "/services/collector"

            async with httpx.AsyncClient(timeout=10.0, verify=self.config.get("verify_ssl", True)) as client:
                resp = await client.post(
                    url,
                    content="\n".join(payload_lines),
                    headers={
                        "Authorization": f"Splunk {token}",
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code == 200:
                    return True
                logger.warning(f"Splunk HEC send failed ({resp.status_code}): {resp.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Splunk HEC send error: {e}")
            return False

    async def test_connection(self) -> tuple[bool, str]:
        hec_url = self.config.get("hec_url", "")
        token = self.credentials.get("hec_token", "")

        if not hec_url:
            return False, "HEC URL is required"
        if not token:
            return False, "HEC token is required"

        url = hec_url.rstrip("/")
        if not url.endswith("/services/collector"):
            url += "/services/collector"

        try:
            test_event = {
                "event": {"message": "Bonito connectivity test", "source": "bonito"},
                "sourcetype": "bonito:test",
            }
            async with httpx.AsyncClient(timeout=10.0, verify=self.config.get("verify_ssl", True)) as client:
                resp = await client.post(
                    url,
                    json=test_event,
                    headers={
                        "Authorization": f"Splunk {token}",
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code == 200:
                    return True, "Connected to Splunk HEC successfully"
                return False, f"Splunk HEC validation failed (HTTP {resp.status_code}): {resp.text[:100]}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"


# ── AWS CloudWatch Integration ──

class CloudWatchIntegration(BaseLogIntegration):
    """AWS CloudWatch Logs integration via boto3."""

    async def send_logs(self, logs: List[Dict[str, Any]]) -> bool:
        try:
            import boto3
        except ImportError:
            logger.error("boto3 not installed — cannot send to CloudWatch")
            return False

        region = self.config.get("region", "us-east-1")
        log_group = self.config.get("log_group", "/bonito/platform")
        log_stream = self.config.get("log_stream", "platform-logs")
        access_key = self.credentials.get("aws_access_key_id", "")
        secret_key = self.credentials.get("aws_secret_access_key", "")

        try:
            client = boto3.client(
                "logs",
                region_name=region,
                aws_access_key_id=access_key or None,
                aws_secret_access_key=secret_key or None,
            )

            # Ensure log group and stream exist
            try:
                client.create_log_group(logGroupName=log_group)
            except client.exceptions.ResourceAlreadyExistsException:
                pass

            try:
                client.create_log_stream(logGroupName=log_group, logStreamName=log_stream)
            except client.exceptions.ResourceAlreadyExistsException:
                pass

            # Build log events
            events = []
            for log in logs:
                formatted = self._format_log(log)
                ts = formatted.get("timestamp", "")
                try:
                    epoch_ms = int(datetime.fromisoformat(ts).timestamp() * 1000)
                except (ValueError, TypeError):
                    epoch_ms = int(time.time() * 1000)

                events.append({
                    "timestamp": epoch_ms,
                    "message": json.dumps({
                        "log_type": formatted["log_type"],
                        "event_type": formatted["event_type"],
                        "severity": formatted["severity"],
                        "message": formatted["message"],
                        "org_id": formatted["org_id"],
                        "user_id": formatted["user_id"],
                        "resource_type": formatted["resource_type"],
                        "resource_id": formatted["resource_id"],
                        "duration_ms": formatted["duration_ms"],
                        "cost": formatted["cost"],
                        "metadata": formatted["metadata"],
                    }),
                })

            # Sort by timestamp (CloudWatch requirement)
            events.sort(key=lambda e: e["timestamp"])

            # Get sequence token
            resp = client.describe_log_streams(
                logGroupName=log_group,
                logStreamNamePrefix=log_stream,
                limit=1,
            )
            streams = resp.get("logStreams", [])
            kwargs = {
                "logGroupName": log_group,
                "logStreamName": log_stream,
                "logEvents": events,
            }
            if streams and "uploadSequenceToken" in streams[0]:
                kwargs["sequenceToken"] = streams[0]["uploadSequenceToken"]

            client.put_log_events(**kwargs)
            return True

        except Exception as e:
            logger.error(f"CloudWatch send error: {e}")
            return False

    async def test_connection(self) -> tuple[bool, str]:
        try:
            import boto3
        except ImportError:
            return False, "boto3 is not installed on the server"

        region = self.config.get("region", "us-east-1")
        access_key = self.credentials.get("aws_access_key_id", "")
        secret_key = self.credentials.get("aws_secret_access_key", "")

        try:
            client = boto3.client(
                "logs",
                region_name=region,
                aws_access_key_id=access_key or None,
                aws_secret_access_key=secret_key or None,
            )
            # Test by describing log groups (lightweight API call)
            client.describe_log_groups(limit=1)
            return True, "Connected to AWS CloudWatch successfully"
        except Exception as e:
            return False, f"CloudWatch connection error: {str(e)}"


# ── Webhook Integration ──

class WebhookIntegration(BaseLogIntegration):
    """Generic webhook (HTTP POST) integration."""

    async def send_logs(self, logs: List[Dict[str, Any]]) -> bool:
        url = self.config.get("url", "")
        secret = self.credentials.get("secret", "")
        headers = self.config.get("headers", {})

        if not url:
            logger.warning("Webhook URL not configured")
            return False

        payload = {
            "source": "bonito",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": len(logs),
            "logs": [self._format_log(log) for log in logs],
        }

        request_headers = {
            "Content-Type": "application/json",
            "User-Agent": "Bonito-Platform/1.0",
            **headers,
        }
        if secret:
            import hashlib
            import hmac
            body = json.dumps(payload)
            signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
            request_headers["X-Bonito-Signature"] = f"sha256={signature}"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload, headers=request_headers)
                if resp.status_code < 300:
                    return True
                logger.warning(f"Webhook send failed ({resp.status_code}): {resp.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Webhook send error: {e}")
            return False

    async def test_connection(self) -> tuple[bool, str]:
        url = self.config.get("url", "")
        if not url:
            return False, "Webhook URL is required"

        try:
            payload = {
                "source": "bonito",
                "type": "test",
                "message": "Bonito connectivity test",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json", "User-Agent": "Bonito-Platform/1.0"},
                )
                if resp.status_code < 300:
                    return True, f"Webhook responded with {resp.status_code}"
                return False, f"Webhook returned HTTP {resp.status_code}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"


# ── Stub Integrations ──

class ElasticsearchIntegration(BaseLogIntegration):
    """Elasticsearch/OpenSearch integration (stub)."""

    async def send_logs(self, logs: List[Dict[str, Any]]) -> bool:
        logger.info(f"Elasticsearch integration stub: would send {len(logs)} logs")
        return True

    async def test_connection(self) -> tuple[bool, str]:
        return False, "Elasticsearch integration is not yet fully implemented. Coming soon."


class AzureMonitorIntegration(BaseLogIntegration):
    """Azure Monitor integration (stub)."""

    async def send_logs(self, logs: List[Dict[str, Any]]) -> bool:
        logger.info(f"Azure Monitor integration stub: would send {len(logs)} logs")
        return True

    async def test_connection(self) -> tuple[bool, str]:
        return False, "Azure Monitor integration is not yet fully implemented. Coming soon."


class GCPLoggingIntegration(BaseLogIntegration):
    """Google Cloud Logging integration (stub)."""

    async def send_logs(self, logs: List[Dict[str, Any]]) -> bool:
        logger.info(f"GCP Logging integration stub: would send {len(logs)} logs")
        return True

    async def test_connection(self) -> tuple[bool, str]:
        return False, "Google Cloud Logging integration is not yet fully implemented. Coming soon."


class CloudStorageIntegration(BaseLogIntegration):
    """Cloud storage batch export integration (stub)."""

    async def send_logs(self, logs: List[Dict[str, Any]]) -> bool:
        logger.info(f"Cloud Storage integration stub: would send {len(logs)} logs")
        return True

    async def test_connection(self) -> tuple[bool, str]:
        return False, "Cloud Storage integration is not yet fully implemented. Coming soon."


# ── Factory ──

INTEGRATION_REGISTRY: Dict[str, type[BaseLogIntegration]] = {
    "datadog": DatadogIntegration,
    "splunk": SplunkIntegration,
    "cloudwatch": CloudWatchIntegration,
    "elasticsearch": ElasticsearchIntegration,
    "azure_monitor": AzureMonitorIntegration,
    "gcp_logging": GCPLoggingIntegration,
    "webhook": WebhookIntegration,
    "cloud_storage": CloudStorageIntegration,
}


def get_integration(integration_type: str, config: Dict[str, Any], credentials: Dict[str, Any]) -> Optional[BaseLogIntegration]:
    """Factory to create the correct integration instance."""
    cls = INTEGRATION_REGISTRY.get(integration_type)
    if cls is None:
        logger.warning(f"Unknown integration type: {integration_type}")
        return None
    return cls(config=config, credentials=credentials)
