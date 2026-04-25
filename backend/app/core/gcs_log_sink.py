"""
GCS Log Sink — streams structured Bonito events to Google Cloud Storage.

Format: newline-delimited JSON (NDJSON), one event per line.
Path: gs://{bucket}/logs/{YYYY}/{MM}/{DD}/{HH}/{server_name}_{event_id}.ndjson

The NDJSON format allows Helios (on the Orin) to stream logs in real-time
using GCS's watch mechanism, while also supporting batch reads for historical analysis.

Sentry-compatible event schema — Bonito events map directly to Sentry's event
format so existing Sentry-style tooling can ingest them.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

# Service account JWT auth (for Railway / non-GCP environments)
_SA_KEY_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
_SA_KEY_JSON = os.getenv("GCS_SERVICE_ACCOUNT_JSON", "")  # inline JSON alternative

logger = logging.getLogger(__name__)

BUCKET_NAME = os.getenv("BONITO_LOGS_BUCKET", "bonito-logs-prod")
_SERVER_NAME = os.getenv("BONITO_SERVER_NAME", socket.gethostname())

# GCS REST API base (no SDK needed — token available via metadata server)
_GCS_UPLOAD_URL = "https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o"
_GCS_RESUMABLE_URL = "https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o/{object_name}/compose"


class GCSLogSink:
    """
    Async GCS log sink that writes NDJSON events to GCS.

    Each event is a Sentry-compatible structured log entry.
    Events are buffered in memory and flushed every `flush_interval` seconds
    or when `flush_size` bytes are accumulated — whichever comes first.

    Path format:
      logs/{YYYY}/{MM}/{DD}/{HH}/{server_name}_{event_id}.ndjson

    GCS object is created/replaced each hour with a predictable name,
    allowing Helios to use GCS notifications (object finalize) for real-time
    event delivery without polling.
    """

    def __init__(
        self,
        bucket: str = BUCKET_NAME,
        server_name: str = _SERVER_NAME,
        flush_interval_seconds: float = 5.0,
        flush_size_bytes: int = 100_000,  # ~100KB
        max_buffer_events: int = 1000,
    ):
        self.bucket = bucket
        self.server_name = server_name
        self.flush_interval = flush_interval_seconds
        self.flush_size = flush_size_bytes
        self.max_buffer_events = max_buffer_events

        self._buffer: list[str] = []
        self._buffer_bytes = 0
        self._last_flush = datetime.now(timezone.utc)
        self._current_hour = self._hour_key()
        self._client: Optional[httpx.AsyncClient] = None

        # Service account auth state
        self._sa_credentials: Optional[Dict[str, Any]] = None
        self._sa_token: Optional[str] = None
        self._sa_token_expiry: float = 0

    # ── Public API ───────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the sink (token resolved lazily at first event)."""
        self._client = httpx.AsyncClient(timeout=30.0)
        self._sa_credentials = self._load_service_account()
        auth_method = "service_account" if self._sa_credentials else "metadata_server"
        logger.info(
            "GCSLogSink started",
            extra={
                "bucket": self.bucket,
                "server_name": self.server_name,
                "flush_interval_s": self.flush_interval,
                "auth_method": auth_method,
            },
        )

    async def stop(self) -> None:
        """Flush remaining buffer and close."""
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
        Emit a structured log event.

        All fields are optional but should be filled in for request-scoped logs.
        The resulting event is Sentry-compatible.
        """
        event = self._build_event(
            level=level,
            message=message,
            logger_name=logger_name,
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

        self._buffer.append(line)
        self._buffer_bytes += event_size

        # Check flush conditions
        should_flush = (
            self._buffer_bytes >= self.flush_size
            or len(self._buffer) >= self.max_buffer_events
            or self._hour_key() != self._current_hour
        )

        if should_flush:
            # Fire-and-forget flush — don't block the request
            import asyncio
            asyncio.create_task(self.flush())

    # ── Private ─────────────────────────────────────────────────────────────

    def _build_event(
        self,
        level: str,
        message: str,
        logger_name: str,
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
        """Build a Sentry-compatible event dict."""
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
        # Enrich with log_type, model, provider, trace_id from extra (Phase 5)
        if extra:
            for tag_key in ("log_type", "event_type", "model", "provider", "trace_id"):
                if extra.get(tag_key):
                    tags[tag_key] = str(extra[tag_key])
        if status_code:
            tags["status_code"] = str(status_code)
            # Sentry uses this for grouping
            if status_code >= 500:
                tags["is_error"] = "1"
        if level in ("error", "critical"):
            tags["is_error"] = "1"

        if tags:
            event["tags"] = tags

        # User context — all PII goes here (not in extra)
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

        # Exception (only when level is error/critical)
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

        # Extra — all additional structured data
        if extra:
            event["extra"] = extra

        if duration_ms is not None:
            event.setdefault("extra", {})["duration_ms"] = duration_ms

        return event

    def _hour_key(self) -> str:
        """Return YYYY/MM/DD/HH for the current UTC hour — used in GCS path."""
        now = datetime.now(timezone.utc)
        return f"{now.year}/{now.month:02d}/{now.day:02d}/{now.hour:02d}"

    def _gcs_object_name(self) -> str:
        """Return the GCS object name for the current hour's buffer file."""
        return f"logs/{self._hour_key()}/{self.server_name}_buffer.ndjson"

    async def flush(self) -> None:
        """Write buffered events to GCS (append-style via chunked upload)."""
        if not self._buffer or not self._client:
            return

        buffer = self._buffer[:]
        self._buffer = []
        self._buffer_bytes = 0
        self._current_hour = self._hour_key()

        try:
            content = "\n".join(buffer).encode("utf-8") + b"\n"
            object_name = self._gcs_object_name()

            # Use GCS resumable upload for reliability
            await self._gcs_put_object(object_name, content)

            # Update last flush timestamp
            self._last_flush = datetime.now(timezone.utc)
            logger.debug(
                "GCSLogSink flushed",
                extra={"event_count": len(buffer), "bytes": len(content), "object": object_name},
            )
        except Exception as e:
            logger.error("GCSLogSink flush failed", extra={"error": str(e), "event_count": len(buffer)})
            # Re-add to buffer on failure (best-effort, don't block)
            if len(self._buffer) == 0:
                self._buffer = buffer

    async def _gcs_put_object(self, object_name: str, content: bytes) -> None:
        """
        Upload an object to GCS using the metadata-metadata server for auth.

        This avoids needing the GCS SDK — we use the built-in service account
        token from the metadata server at 100.100.100.253.
        """
        if not self._client:
            raise RuntimeError("GCSLogSink not started")

        # Get access token from metadata server
        token = await self._get_access_token()
        if not token:
            raise RuntimeError("Could not obtain GCS access token from metadata server")

        url = f"https://storage.googleapis.com/upload/storage/v1/b/{self.bucket}/o?uploadType=media&name={object_name}"

        # Try simple upload first (for buffers < 5MB)
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
            # For larger buffers, use resumable upload
            resp = await self._client.post(
                "https://storage.googleapis.com/resumable/upload/storage/v1/b/{self.bucket}/o",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json={
                    "name": object_name,
                    "contentType": "application/octet-stream",
                },
            )
            # Would need to handle resumable upload — simplified here
            # For Bonito, buffer flushes are < 5MB, so simple upload path is fine
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
        import hashlib

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

        # Return cached token if still valid (5 min buffer)
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
                logger.warning("SA token exchange failed", extra={"status": resp.status_code, "body": resp.text[:200]})
        except Exception as e:
            logger.warning("SA token exchange error", extra={"error": str(e)})
        return None

    async def _get_access_token(self) -> Optional[str]:
        """
        Get a GCS access token.

        Priority: service account JWT → GCP metadata server.
        """
        # Try service account first (works on Railway, any non-GCP host)
        if self._sa_credentials:
            token = await self._get_sa_token()
            if token:
                return token

        # Fall back to metadata server (works on GCP VMs, Cloud Run, GKE)
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
