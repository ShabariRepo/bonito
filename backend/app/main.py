from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings

# Initialize Sentry before FastAPI app
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        send_default_pii=True,
        traces_sample_rate=0.2 if settings.production_mode else 1.0,
        profile_session_sample_rate=0.1 if settings.production_mode else 1.0,
        profile_lifecycle="trace",
        environment="production" if settings.production_mode else "development",
    )
from app.core.logging import setup_logging
from app.core.responses import handle_http_exception, handle_general_exception
from app.api.routes import health, providers, models, deployments, routing, compliance, export, costs, users, policies, audit, ai, auth, onboarding, notifications, analytics, gateway, routing_policies, admin, knowledge_base, sso, sso_admin, bonobot_projects, bonobot_agents, agent_groups, mcp_servers, rbac, logging as logging_routes, subscriptions, bonbon, widget, agent_memory, agent_scheduler, agent_approval, github_app, secrets
from app.middleware.security import (
    RateLimitMiddleware,
    RequestBodySizeLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    configure_cors,
)
from app.middleware.audit import AuditMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize logging, Redis, and load secrets from Vault
    setup_logging(
        level="INFO", 
        json_logs=settings.production_mode
    )
    await settings.load_secrets_from_vault()
    
    # Initialize Redis connection
    from app.core.redis import init_redis
    await init_redis()
    
    # Start the log service background flush loop
    from app.services.log_service import log_service
    await log_service.start()
    
    # Start the GCS structured log sink
    from app.core.gcs_log_sink import start_gcs_sink
    await start_gcs_sink()

    # Start background model sync (refreshes provider model catalogs every 24h)
    from app.services.model_sync import start_model_sync
    await start_model_sync()

    # Note: Alembic migrations run in start-prod.sh BEFORE uvicorn starts.
    # Don't run them again here — with multiple workers they'd race each other.

    yield
    
    # Shutdown: Stop log service, clean up connections
    from app.services.log_service import log_service as _log_service
    try:
        await _log_service.stop()
    except Exception:
        pass

    from app.core.gcs_log_sink import stop_gcs_sink
    try:
        await stop_gcs_sink()
    except Exception:
        pass

    from app.core.database import database
    from app.core.redis import close_redis

    try:
        if database:
            await database.disconnect()
    except Exception:
        pass

    try:
        await close_redis()
    except Exception:
        pass

    from app.services.model_sync import stop_model_sync
    try:
        await stop_model_sync()
    except Exception:
        pass


fastapi_app = FastAPI(
    title="Bonito API",
    description="Enterprise AI Platform API",
    version="0.1.0",
    lifespan=lifespan,
    redirect_slashes=False,  # Must be False — Vercel strips trailing slashes (308), conflicting with FastAPI 307 redirects
)
app = fastapi_app  # alias; reassigned to TrailingSlashMiddleware wrapper at bottom of file

# Add global exception handlers
app.add_exception_handler(HTTPException, handle_http_exception)
app.add_exception_handler(Exception, handle_general_exception)

# Middleware is applied in reverse order (last added = first executed)
# Order of execution: RequestID → SecurityHeaders → BodySizeLimit → RateLimit → CORS → AuditMiddleware → route

# Audit (innermost — runs closest to route handler, captures response status)
app.add_middleware(AuditMiddleware)

# CORS
configure_cors(app)

# Rate limiting
app.add_middleware(RateLimitMiddleware)

# Request body size limit for /v1/* gateway endpoints (rejects before rate-limit slot is consumed)
app.add_middleware(RequestBodySizeLimitMiddleware)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Request ID (outermost — ensures all responses get an ID)
app.add_middleware(RequestIDMiddleware)

# Structured log emit to GCS (after RequestIDMiddleware so request_id is available)
from app.middleware.log_emit import LogEmitMiddleware
app.add_middleware(LogEmitMiddleware)

# GZip compression (very outer layer)
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Routes
app.include_router(health.router, prefix="/api")
app.include_router(providers.router, prefix="/api")
app.include_router(models.router, prefix="/api")
app.include_router(deployments.router, prefix="/api")
app.include_router(routing.router, prefix="/api")
app.include_router(routing_policies.router, prefix="/api")
app.include_router(compliance.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(costs.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(policies.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(onboarding.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(notifications.alert_router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(knowledge_base.router, prefix="/api")
app.include_router(secrets.router, prefix="/api")

app.include_router(sso.router, prefix="/api")
app.include_router(sso_admin.router, prefix="/api")
app.include_router(admin.router, prefix="/api")

# Logging & observability routes
app.include_router(logging_routes.router, prefix="/api")
app.include_router(logging_routes.integration_router, prefix="/api")
app.include_router(logging_routes.audit_router, prefix="/api")

# Bonobot routes
app.include_router(bonobot_projects.router, prefix="/api")
app.include_router(bonobot_agents.router, prefix="/api")
app.include_router(agent_groups.router, prefix="/api")
app.include_router(mcp_servers.router, prefix="/api")
app.include_router(rbac.router, prefix="/api")
app.include_router(subscriptions.router, prefix="/api")

# Enterprise Bonobot features
app.include_router(agent_memory.router, prefix="/api")
app.include_router(agent_scheduler.router, prefix="/api")
app.include_router(agent_approval.router, prefix="/api")

# BonBon routes
app.include_router(bonbon.router, prefix="/api")
app.include_router(widget.router, prefix="/api")

# GitHub App routes
app.include_router(github_app.router, prefix="/api/v1")

# Access requests (lazy-loaded to avoid import chain issues)
from app.api.routes import access_requests
app.include_router(access_requests.public_router, prefix="/api")
app.include_router(access_requests.admin_router, prefix="/api")

# Contact form
from app.api.routes import contact
app.include_router(contact.router, prefix="/api")

# Gateway routes — mounted at root (not /api) because /v1/* is OpenAI-compatible
app.include_router(gateway.router)


# ─── Trailing Slash Normalization (MUST be after all routers) ───
# Wraps the ASGI app to strip trailing slashes before routing.
# Required because: redirect_slashes=False (Vercel 308 conflicts with FastAPI 307),
# but some frontend calls still include trailing slashes.
from starlette.types import ASGIApp, Receive, Scope, Send

class TrailingSlashMiddleware:
    """Strip trailing slashes from request paths (except root /)."""
    def __init__(self, inner: ASGIApp):
        self.inner = inner
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http" and scope["path"] != "/" and scope["path"].endswith("/"):
            scope["path"] = scope["path"].rstrip("/")
            if scope.get("raw_path"):
                scope["raw_path"] = scope["raw_path"].rstrip(b"/")
        await self.inner(scope, receive, send)

app = TrailingSlashMiddleware(app)  # type: ignore[assignment]
