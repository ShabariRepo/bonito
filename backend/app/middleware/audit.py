"""Audit logging middleware — writes to audit_logs table for sensitive endpoints."""

import uuid
import time
import logging
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.database import async_session as async_session_factory
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)

# Endpoints (prefixes) that trigger audit logging
AUDITED_PREFIXES = [
    "/api/providers/connect",
    "/api/auth/",
    "/api/routing/invoke",
]

# Also audit any path containing /invoke
AUDITED_PATTERNS = ["/invoke"]

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _should_audit(path: str, method: str) -> bool:
    # Always audit mutating methods on sensitive paths
    if method in ("GET", "OPTIONS", "HEAD"):
        return False
    for prefix in AUDITED_PREFIXES:
        if path.startswith(prefix):
            return True
    for pattern in AUDITED_PATTERNS:
        if pattern in path:
            return True
    return False


def _derive_action(method: str, path: str) -> tuple[str, str]:
    """Return (action, resource_type) from the request."""
    if "/invoke" in path:
        return "invoke", "model"
    if "/connect" in path:
        return "connect", "provider"
    if "/auth/" in path:
        if "login" in path:
            return "login", "auth"
        if "register" in path:
            return "register", "auth"
        return "auth_action", "auth"
    return method.lower(), "unknown"


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        if not _should_audit(path, method):
            return await call_next(request)

        start = time.monotonic()
        response: Response = await call_next(request)
        elapsed_ms = round((time.monotonic() - start) * 1000)

        # Fire-and-forget audit write
        try:
            action, resource_type = _derive_action(method, path)
            ip = _client_ip(request)

            # Try to get user info from request state (set by auth middleware)
            user_id = getattr(request.state, "user_id", None)
            user_name = getattr(request.state, "user_name", None)
            request_id = getattr(request.state, "request_id", None)

            # Extract resource_id from path (e.g. provider UUID)
            resource_id = None
            parts = path.strip("/").split("/")
            for part in parts:
                try:
                    uuid.UUID(part)
                    resource_id = part
                    break
                except ValueError:
                    continue

            details = {
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "latency_ms": elapsed_ms,
                "request_id": request_id,
            }

            async with async_session_factory() as session:
                log_entry = AuditLog(
                    id=uuid.uuid4(),
                    org_id=DEFAULT_ORG_ID,
                    user_id=user_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details_json=details,
                    ip_address=ip,
                    user_name=user_name,
                )
                session.add(log_entry)
                await session.commit()
        except Exception:
            logger.exception("Failed to write audit log")

        return response
