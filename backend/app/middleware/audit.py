"""Audit logging middleware — writes to audit_logs table for sensitive endpoints.

SOC2 CC7.2 / CC9.2: Complete audit trail including auth failures and
sensitive data access (GET on credential/key/user endpoints).
"""

import hashlib
import json
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

# Endpoints (prefixes) that trigger audit logging for mutating operations
AUDITED_PREFIXES = [
    "/api/providers/connect",
    "/api/providers/",
    "/api/auth/",
    "/api/routing/invoke",
    "/api/keys/",
    "/api/gateway/keys",
    "/api/users/",
    "/api/admin/",
    "/api/organizations/",
    "/api/log-integrations",
]

# Also audit any path containing /invoke
AUDITED_PATTERNS = ["/invoke"]

# Sensitive GET paths — SOC2 requires logging read access to credentials,
# keys, user data, and audit exports
SENSITIVE_GET_PREFIXES = [
    "/api/providers/",
    "/api/keys/",
    "/api/gateway/keys",
    "/api/users/",
    "/api/admin/",
    "/api/logs/export",
    "/api/audit-logs",
    "/api/log-integrations",
    "/api/organizations/",
]


def _should_audit(path: str, method: str) -> bool:
    if method in ("OPTIONS", "HEAD"):
        return False

    # Audit GET on sensitive paths (SOC2: data access logging)
    if method == "GET":
        for prefix in SENSITIVE_GET_PREFIXES:
            if path.startswith(prefix):
                return True
        return False

    # Audit all mutating operations on audited paths
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

            # Extract org_id from the JWT bearer token
            org_id = None
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                try:
                    from app.services.auth_service import decode_token
                    payload = decode_token(auth_header[7:])
                    org_id_str = payload.get("org_id")
                    if org_id_str:
                        org_id = uuid.UUID(org_id_str)
                    if not user_id:
                        user_id = payload.get("sub")
                except Exception:
                    pass  # Token may be invalid/expired — audit still proceeds

            # SOC2: DO NOT skip audit entries for unauthenticated requests.
            # Auth failures are critical security events that must be logged.

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

            entry_id = uuid.uuid4()
            now = datetime.now(timezone.utc)

            async with async_session_factory() as session:
                # Get previous hash for tamper-evident chain
                from sqlalchemy import select, desc
                prev_hash_query = (
                    select(AuditLog.entry_hash)
                    .order_by(desc(AuditLog.created_at))
                    .limit(1)
                )
                if org_id is not None:
                    prev_hash_query = prev_hash_query.where(AuditLog.org_id == org_id)
                result = await session.execute(prev_hash_query)
                prev_hash = result.scalar() or ""

                # Compute tamper-evident hash
                hash_input = "|".join([
                    prev_hash,
                    str(org_id or ""),
                    str(user_id or ""),
                    action,
                    resource_type,
                    path,
                    str(response.status_code),
                    now.isoformat(),
                ])
                entry_hash = hashlib.sha256(hash_input.encode()).hexdigest()

                log_entry = AuditLog(
                    id=entry_id,
                    org_id=org_id,
                    user_id=user_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details_json=details,
                    ip_address=ip,
                    user_name=user_name,
                    prev_hash=prev_hash,
                    entry_hash=entry_hash,
                )
                session.add(log_entry)
                await session.commit()
        except Exception:
            logger.exception("Failed to write audit log")

        return response
