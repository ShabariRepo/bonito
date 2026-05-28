"""
GCS Log Sink — streams structured Bonito events to Google Cloud Storage.

Format: newline-delimited JSON (NDJSON), one event per line.
Path: gs://{bucket}/{org_id}/{log_type}/{YYYY}/{MM}/{DD}/{HH}.ndjson

Organized by org and feature so that:
  - Per-org retention policies can use GCS lifecycle rules on prefix
  - Helios can subscribe to specific org/feature paths
  - Each log type (gateway, agent, auth, kb, admin, deployment) gets its own file

Sentry-compatible event schema — Bonito events map directly to Sentry's event
format so existing Sentry-style tooling can ingest them.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

# Service account JWT auth (for Railway / non-GCP environments)
_SA_KEY_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
_SA_KEY_JSON = os.getenv("GCS_SERVICE_ACCOUNT_JSON", "")  # inline JSON alternative

logger = logging.getLogger(__name__)

BUCKET_NAME = os.getenv("BONITO_LOGS_BUCKET", "bonito-logs-prod")
_SERVER_NAME = os.getenv("BONITO_SERVER_NAME", socket.gethostname())

VALID_LOG_TYPES = {
    "gateway", "auth", "agent", "kb", "admin",
    "deployment", "billing", "compliance", "approval", "system",
}


class GCSLogSink:
    """
    Async GCS log sink that writes NDJSON events to GCS.

    Events are buffered per (org_id, log_type) and flushed every
    `flush_interval` seconds or when any single buffer exceeds
    `flush_size` bytes — whichever comes first.

    Path format:
      {org_id}/{log_type}/{YYYY}/{MM}/{DD}/{HH}.ndjson

    Each org/feature combination gets its own hourly file, enabling:
      - GCS lifecycle rules per org prefix for tier-based retention
      - Feature-level log isolation for Helios processing
      - Clean separation for compliance and audit requirements
    """

    def __init__(
        self,
        bucket: str = BUCKET_NAME,
        server_name: str = _SERVER_NAME,
        flush_interval_seconds: float = 5.0,
        flush_size_bytes: int = 100_000,  # ~100KB per buffer
        max_buffer_events: int = 1000,
    ):
        self.bucket = bucket
        self.server_name = server_name
        self.flush_interval = flush_interval_seconds
        self.flush_size = flush_size_bytes
        self.max_buffer_events = max_buffer_events

        # Buffers keyed by (org_id, log_type)
        self._buffers: Dict[Tuple[str, str], List[str]] = defaultdict(list)
        self._buffer_bytes: Dict[Tuple[str, str], int] = defaultdict(int)
        self._client: Optional[httpx.AsyncClient] = None
        self._flush_task: Optional[asyncio.Task] = None

        # Service account auth state
        self._sa_credentials: Optional[Dict[str, Any]] = None
        self._sa_token: Optional[str] = None
        self._sa_token_expiry: float = 0

    # ── Public API ───────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the sink with periodic flush timer."""
        self._client = httpx.AsyncClient(timeout=30.0)
        self._sa_credentials = self._load_service_account()
        self._flush_task = asyncio.create_task(self._periodic_flush())
        auth_method = "service_account" if self._sa_credentials else "metadata_server"
        logger.info(
            "GCSLogSink started (org-partitioned)",
            extra={
                "bucket": self.bucket,
                "server_name": self.server_name,
                "flush_interval_s": self.flush_interval,
                "auth_method": auth_method,
            },
        )

    async def stop(self) -> None:
        """Flush remaining buffers and close."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self.flush()
        if self._client:
            await self._client.aclose()
        logger.info("GCSLogSink stopped")

    def emit(
        self,
        level: str,
        message: str,
        *,
        logger_name: str = "bonito",
        log_type: str = "gateway",
        feature: Optional[str] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        duration_ms: Optional[float] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        exception: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit a structured log event, routed to the correct org/log_type buffer.

        org_id and log_type determine the GCS path. Events without an org_id
        are written to a shared "_system" prefix. The `feature` field tags the
        sub-feature within the log_type (e.g. "failover" within "gateway").
        """
        event = self._build_event(
            level=level,
            message=message,
            logger_name=logger_name,
            feature=feature,
            request_id=request_id,
            user_id=user_id,
            org_id=org_id,
            api_key_id=api_key_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            ip_address=ip_address,
            user_agent=user_agent,
            exception=exception,
            extra=extra,
        )

        line = json.dumps(event, ensure_ascii=False)
        event_size = len(line.encode("utf-8"))

        # Route to the correct buffer
        resolved_org = org_id or "_system"
        resolved_type = log_type if log_type in VALID_LOG_TYPES else "general"
        key = (resolved_org, resolved_type)

        self._buffers[key].append(line)
        self._buffer_bytes[key] += event_size

        # Check flush conditions for this specific buffer
        should_flush = (
            self._buffer_bytes[key] >= self.flush_size
            or len(self._buffers[key]) >= self.max_buffer_events
        )

        if should_flush:
            asyncio.create_task(self._flush_buffer(key))

    async def _periodic_flush(self) -> None:
        """Background task that flushes all buffers every flush_interval seconds."""
        while True:
            await asyncio.sleep(self.flush_interval)
            await self.flush()

    async def flush(self) -> None:
        """Flush all non-empty buffers to GCS."""
        keys = list(self._buffers.keys())
        for key in keys:
            if self._buffers[key]:
                await self._flush_buffer(key)

    # ── Private ─────────────────────────────────────────────────────────────

    async def _flush_buffer(self, key: Tuple[str, str]) -> None:
        """Flush a single (org_id, log_type) buffer to its GCS path."""
        if not self._buffers[key] or not self._client:
            return

        buffer = self._buffers[key]
        self._buffers[key] = []
        self._buffer_bytes[key] = 0

        org_id, log_type = key

        try:
            content = "\n".join(buffer).encode("utf-8") + b"\n"
            object_name = self._gcs_object_name(org_id, log_type)

            await self._gcs_put_object(object_name, content)

            logger.debug(
                "GCSLogSink flushed",
                extra={
                    "event_count": len(buffer),
                    "bytes": len(content),
                    "object": object_name,
                    "org_id": org_id,
                    "log_type": log_type,
                },
            )
        except Exception as e:
            logger.error(
                "GCSLogSink flush failed: %s (org=%s, type=%s, events=%d)",
                str(e), org_id, log_type, len(buffer),
            )
            # Re-add to buffer on failure (best-effort)
            if not self._buffers[key]:
                self._buffers[key] = buffer

    def _build_event(
        self,
        level: str,
        message: str,
        logger_name: str,
        feature: Optional[str],
        request_id: Optional[str],
        user_id: Optional[str],
        org_id: Optional[str],
        api_key_id: Optional[str],
        endpoint: Optional[str],
        method: Optional[str],
        status_code: Optional[int],
        duration_ms: Optional[float],
        ip_address: Optional[str],
        user_agent: Optional[str],
        exception: Optional[Dict[str, Any]],
        extra: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build a Sentry-compatible event dict with feature tag."""
        event_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        event: Dict[str, Any] = {
            "event_id": event_id,
            "timestamp": timestamp,
            "level": level,
            "platform": "python",
            "logger": logger_name,
            "server_name": self.server_name,
            "message": message,
        }

        # Feature sub-tag (e.g. "failover" within gateway, "scheduler" within agent)
        if feature:
            event["feature"] = feature

        # Tags — used for Sentry's grouping / Helios fingerprinting
        tags: Dict[str, str] = {}
        if request_id:
            tags["request_id"] = request_id
        if org_id:
            tags["org_id"] = str(org_id)
        if api_key_id:
            tags["api_key_id"] = str(api_key_id)
        if endpoint:
            tags["endpoint"] = endpoint
        if method:
            tags["method"] = method
        if extra:
            for tag_key in ("log_type", "event_type", "model", "provider", "trace_id"):
                if extra.get(tag_key):
                    tags[tag_key] = str(extra[tag_key])
        if status_code:
            tags["status_code"] = str(status_code)
            if status_code >= 500:
                tags["is_error"] = "1"
        if level in ("error", "critical"):
            tags["is_error"] = "1"

        if tags:
            event["tags"] = tags

        # User context
        user: Dict[str, Any] = {}
        if user_id:
            user["id"] = str(user_id)
        if org_id:
            user["org_id"] = str(org_id)
        if ip_address:
            user["ip_address"] = ip_address

        if user:
            event["user"] = user

        # Request context
        request: Dict[str, Any] = {}
        if endpoint or method:
            request["url"] = endpoint or ""
            request["method"] = method or ""
            request["query_string"] = ""
        if user_agent:
            request["env"] = {"REMOTE_ADDR": ip_address or "", "HTTP_USER_AGENT": user_agent}

        if request:
            event["request"] = request

        # Exception
        if exception:
            event["exception"] = {
                "values": [
                    {
                        "type": exception.get("type", "Error"),
                        "value": exception.get("message", message),
                        "stacktrace": exception.get("stacktrace"),
                    }
                ]
            }

        # Extra
        if extra:
            event["extra"] = extra

        if duration_ms is not None:
            event.setdefault("extra", {})["duration_ms"] = duration_ms

        return event

    def _hour_key(self) -> str:
        """Return YYYY/MM/DD/HH for the current UTC hour."""
        now = datetime.now(timezone.utc)
        return f"{now.year}/{now.month:02d}/{now.day:02d}/{now.hour:02d}"

    def _gcs_object_name(self, org_id: str, log_type: str) -> str:
        """
        GCS object path for a given org and log type.

        Format: {org_id}/{log_type}/{YYYY}/{MM}/{DD}/{HH}.ndjson
        Example: 550e8400-e29b-41d4-a716-446655440000/gateway/2026/05/27/14.ndjson
        """
        return f"{org_id}/{log_type}/{self._hour_key()}.ndjson"

    async def _gcs_put_object(self, object_name: str, content: bytes) -> None:
        """Upload an object to GCS."""
        if not self._client:
            raise RuntimeError("GCSLogSink not started")

        token = await self._get_access_token()
        if not token:
            raise RuntimeError("Could not obtain GCS access token")

        if len(content) < 5 * 1024 * 1024:
            url = f"https://storage.googleapis.com/upload/storage/v1/b/{self.bucket}/o"
            resp = await self._client.post(
                url,
                params={"uploadType": "media", "name": object_name},
                content=content,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/octet-stream",
                    "x-goog-content-length-range": "0,52428800",
                },
            )
        else:
            raise RuntimeError("Buffer too large for simple upload — increase flush_size")

        if resp.status_code not in (200, 201):
            body = resp.text[:200]
            raise RuntimeError(f"GCS upload failed: {resp.status_code} — {body}")

    def _load_service_account(self) -> Optional[Dict[str, Any]]:
        """Load GCP service account credentials from file or env var."""
        sa_json = None

        if _SA_KEY_PATH and os.path.isfile(_SA_KEY_PATH):
            try:
                with open(_SA_KEY_PATH) as f:
                    sa_json = json.load(f)
                logger.info("GCSLogSink loaded service account from file", extra={"path": _SA_KEY_PATH})
            except Exception as e:
                logger.warning("Failed to load service account file", extra={"path": _SA_KEY_PATH, "error": str(e)})

        if not sa_json and _SA_KEY_JSON:
            try:
                sa_json = json.loads(_SA_KEY_JSON)
                logger.info("GCSLogSink loaded service account from GCS_SERVICE_ACCOUNT_JSON env var")
            except Exception as e:
                logger.warning("Failed to parse GCS_SERVICE_ACCOUNT_JSON", extra={"error": str(e)})

        if sa_json and sa_json.get("type") == "service_account":
            return sa_json
        return None

    def _create_jwt(self, sa: Dict[str, Any]) -> str:
        """Create a signed JWT for Google OAuth2 token exchange."""
        import base64

        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
        except ImportError:
            raise RuntimeError("cryptography package required for service account auth: pip install cryptography")

        now = int(time.time())
        header = {"alg": "RS256", "typ": "JWT"}
        payload = {
            "iss": sa["client_email"],
            "scope": "https://www.googleapis.com/auth/devstorage.read_write",
            "aud": "https://oauth2.googleapis.com/token",
            "iat": now,
            "exp": now + 3600,
        }

        def _b64(data: bytes) -> str:
            return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

        segments = _b64(json.dumps(header).encode()) + "." + _b64(json.dumps(payload).encode())

        private_key = serialization.load_pem_private_key(sa["private_key"].encode(), password=None)
        signature = private_key.sign(segments.encode(), padding.PKCS1v15(), hashes.SHA256())

        return segments + "." + _b64(signature)

    async def _get_sa_token(self) -> Optional[str]:
        """Exchange a service account JWT for an access token."""
        if not self._sa_credentials or not self._client:
            return None

        if self._sa_token and time.time() < self._sa_token_expiry - 300:
            return self._sa_token

        try:
            jwt = self._create_jwt(self._sa_credentials)
            resp = await self._client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": jwt,
                },
                timeout=10.0,
            )
            if resp.status_code == 200:
                token_data = resp.json()
                self._sa_token = token_data["access_token"]
                self._sa_token_expiry = time.time() + token_data.get("expires_in", 3600)
                return self._sa_token
            else:
                logger.warning("SA token exchange failed: %d — %s", resp.status_code, resp.text[:200])
        except Exception as e:
            logger.warning("SA token exchange error: %s", str(e))
        return None

    async def _get_access_token(self) -> Optional[str]:
        """
        Get a GCS access token.

        Priority: service account JWT -> GCP metadata server.
        """
        if self._sa_credentials:
            token = await self._get_sa_token()
            if token:
                return token

        try:
            resp = await self._client.get(
                "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
                headers={"Metadata-Flavor": "Google"},
                timeout=5.0,
            )
            if resp.status_code == 200:
                token_data = resp.json()
                return token_data.get("access_token")
        except Exception as e:
            logger.warning("Failed to get GCS access token from metadata server", extra={"error": str(e)})
        return None


# ── Singleton ──────────────────────────────────────────────────────────────

_gcs_sink: Optional[GCSLogSink] = None


def get_gcs_sink() -> GCSLogSink:
    global _gcs_sink
    if _gcs_sink is None:
        _gcs_sink = GCSLogSink()
    return _gcs_sink


async def start_gcs_sink() -> None:
    sink = get_gcs_sink()
    await sink.start()


async def stop_gcs_sink() -> None:
    if _gcs_sink:
        await _gcs_sink.stop()
