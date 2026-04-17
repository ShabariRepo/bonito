"""
Log Emit Middleware — streams structured request/response events to the GCS log sink.

Every HTTP request/response is emitted as a Sentry-compatible event to GCS,
enabling Helios on the Orin to ingest, group, and analyze Bonito's operational logs.

Events are emitted fire-and-forget (async, non-blocking) to avoid adding
latency to the request path.
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.gcs_log_sink import get_gcs_sink

logger = logging.getLogger(__name__)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _user_agent(request: Request) -> str:
    return request.headers.get("user-agent", "")


async def _get_org_id(request: Request) -> Optional[str]:
    """Extract org_id from the JWT bearer token without full validation."""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    try:
        from app.services.auth_service import decode_token
        payload = decode_token(auth_header[7:])
        org_id = payload.get("org_id")
        return str(org_id) if org_id else None
    except Exception:
        return None


async def _get_user_id(request: Request) -> Optional[str]:
    """Extract user_id from request state (set by auth middleware) or JWT."""
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return str(user_id)

    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    try:
        from app.services.auth_service import decode_token
        payload = decode_token(auth_header[7:])
        return payload.get("sub")
    except Exception:
        return None


async def _get_api_key_id(request: Request) -> Optional[str]:
    """Extract api_key_id from request state."""
    return getattr(request.state, "api_key_id", None)


class LogEmitMiddleware(BaseHTTPMiddleware):
    """
    Emit a structured event for every HTTP request/response to the GCS log sink.

    Two events are emitted per request:
    - request_start: level=info, emitted at the start of the request
    - request_end: level based on response status (info/warning/error),
      emitted at the end with duration_ms

    Both events share the same `request_id` for correlation.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or retrieve request ID
        request_id = getattr(request.state, "request_id", None)
        if not request_id:
            request_id = str(uuid.uuid4())
            request.state.request_id = request_id

        # Capture start time
        start = time.monotonic()

        # Extract context (non-blocking)
        client_ip = _client_ip(request)
        ua = _user_agent(request)

        # Get the GCS sink
        sink = get_gcs_sink()

        # Emit request_start event (non-blocking)
        sink.emit(
            level="info",
            message=f"{request.method} {request.url.path}",
            logger_name="bonito.http",
            request_id=request_id,
            endpoint=request.url.path,
            method=request.method,
            ip_address=client_ip,
            user_agent=ua,
            extra={
                "event_type": "request_start",
                "query_string": str(request.url.query),
                "path_params": dict(request.path_params) if request.path_params else {},
            },
        )

        # Process request
        response: Response = await call_next(request)

        # Calculate duration
        duration_ms = round((time.monotonic() - start) * 1000)

        # Get user/org context (only available after auth middleware runs)
        user_id = await _get_user_id(request)
        org_id = await _get_org_id(request)
        api_key_id = await _get_api_key_id(request)

        # Determine log level from status code
        status_code = response.status_code
        if status_code >= 500:
            level = "error"
        elif status_code >= 400:
            level = "warning"
        else:
            level = "info"

        # Build exception dict if 5xx (for Sentry grouping)
        exception: Optional[dict] = None
        if status_code >= 500:
            exception = {
                "type": f"HTTP{status_code}",
                "message": f"{request.method} {request.url.path} returned {status_code}",
            }

        # Emit request_end event
        sink.emit(
            level=level,
            message=f"{request.method} {request.url.path} {status_code} {duration_ms}ms",
            logger_name="bonito.http",
            request_id=request_id,
            user_id=user_id,
            org_id=org_id,
            api_key_id=api_key_id,
            endpoint=request.url.path,
            method=request.method,
            status_code=status_code,
            duration_ms=duration_ms,
            ip_address=client_ip,
            user_agent=ua,
            exception=exception,
            extra={
                "event_type": "request_end",
            },
        )

        return response
