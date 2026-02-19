"""
Convenience wrappers to emit platform logs from key application flows.

These are thin helpers around log_service.emit() that provide a consistent
interface for each feature area. Import and call from route handlers / services.

Usage:
    from app.services.log_emitters import emit_auth_event, emit_gateway_event
    
    await emit_auth_event(org_id, user_id, "login_success", metadata={"ip": "1.2.3.4"})
"""

import uuid
from typing import Optional, Dict, Any

from app.services.log_service import log_service


# ── Gateway Events ──

async def emit_gateway_event(
    org_id: uuid.UUID,
    event_type: str,
    *,
    severity: str = "info",
    user_id: Optional[uuid.UUID] = None,
    resource_id: Optional[uuid.UUID] = None,
    resource_type: str = "model",
    action: str = "execute",
    message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[int] = None,
    cost: Optional[float] = None,
    trace_id: Optional[uuid.UUID] = None,
):
    """Log a gateway/proxy event (request, error, rate_limit, etc.)."""
    await log_service.emit(
        org_id=org_id,
        log_type="gateway",
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        resource_id=resource_id,
        resource_type=resource_type,
        action=action,
        message=message,
        metadata=metadata,
        duration_ms=duration_ms,
        cost=cost,
        trace_id=trace_id,
    )


# ── Auth Events ──

async def emit_auth_event(
    org_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    event_type: str,
    *,
    severity: str = "info",
    message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Log an auth event (login_success, login_failed, logout, token_refresh, sso, etc.)."""
    await log_service.emit(
        org_id=org_id,
        log_type="auth",
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        resource_type="user",
        resource_id=user_id,
        action="execute",
        message=message,
        metadata=metadata,
    )


# ── Agent Events ──

async def emit_agent_event(
    org_id: uuid.UUID,
    event_type: str,
    *,
    severity: str = "info",
    user_id: Optional[uuid.UUID] = None,
    resource_id: Optional[uuid.UUID] = None,
    message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[int] = None,
    cost: Optional[float] = None,
    trace_id: Optional[uuid.UUID] = None,
):
    """Log an agent execution event (start, complete, error, tool_use)."""
    await log_service.emit(
        org_id=org_id,
        log_type="agent",
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        resource_id=resource_id,
        resource_type="agent",
        action="execute",
        message=message,
        metadata=metadata,
        duration_ms=duration_ms,
        cost=cost,
        trace_id=trace_id,
    )


# ── Knowledge Base Events ──

async def emit_kb_event(
    org_id: uuid.UUID,
    event_type: str,
    *,
    severity: str = "info",
    user_id: Optional[uuid.UUID] = None,
    resource_id: Optional[uuid.UUID] = None,
    action: str = "execute",
    message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[int] = None,
):
    """Log a knowledge base event (upload, search, delete)."""
    await log_service.emit(
        org_id=org_id,
        log_type="kb",
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        resource_id=resource_id,
        resource_type="knowledge_base",
        action=action,
        message=message,
        metadata=metadata,
        duration_ms=duration_ms,
    )


# ── Admin Events ──

async def emit_admin_event(
    org_id: uuid.UUID,
    event_type: str,
    *,
    severity: str = "info",
    user_id: Optional[uuid.UUID] = None,
    resource_id: Optional[uuid.UUID] = None,
    resource_type: str = "config",
    action: str = "update",
    message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Log an admin action (user_invite, role_change, config_change, etc.)."""
    await log_service.emit(
        org_id=org_id,
        log_type="admin",
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        resource_id=resource_id,
        resource_type=resource_type,
        action=action,
        message=message,
        metadata=metadata,
    )


# ── Deployment Events ──

async def emit_deployment_event(
    org_id: uuid.UUID,
    event_type: str,
    *,
    severity: str = "info",
    user_id: Optional[uuid.UUID] = None,
    resource_id: Optional[uuid.UUID] = None,
    action: str = "update",
    message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[int] = None,
):
    """Log a deployment event (deploy, scale, status_change)."""
    await log_service.emit(
        org_id=org_id,
        log_type="deployment",
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        resource_id=resource_id,
        resource_type="deployment",
        action=action,
        message=message,
        metadata=metadata,
        duration_ms=duration_ms,
    )
