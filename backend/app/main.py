from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.responses import handle_http_exception, handle_general_exception
from app.api.routes import health, providers, models, deployments, routing, compliance, export, costs, users, policies, audit, ai, auth, onboarding, notifications, analytics, gateway, routing_policies, admin, knowledge_base, sso, sso_admin, bonobot_projects, bonobot_agents, agent_groups, rbac, logging as logging_routes
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
    
    # Note: Alembic migrations run in start-prod.sh BEFORE uvicorn starts.
    # Don't run them again here — with multiple workers they'd race each other.
    
    yield
    
    # Shutdown: Stop log service, clean up connections
    from app.services.log_service import log_service as _log_service
    try:
        await _log_service.stop()
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


app = FastAPI(
    title="Bonito API",
    description="Enterprise AI Platform API",
    version="0.1.0",
    lifespan=lifespan,
    redirect_slashes=False,  # Avoid 307 redirects that break HTTPS behind proxies
)

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

app.include_router(sso.router, prefix="/api")
app.include_router(sso_admin.router, prefix="/api")
app.include_router(admin.router, prefix="/api")

# Logging & observability routes
app.include_router(logging_routes.router, prefix="/api")
app.include_router(logging_routes.integration_router, prefix="/api")

# Bonobot routes
app.include_router(bonobot_projects.router, prefix="/api")
app.include_router(bonobot_agents.router, prefix="/api")
app.include_router(agent_groups.router, prefix="/api")
app.include_router(rbac.router, prefix="/api")

# Gateway routes — mounted at root (not /api) because /v1/* is OpenAI-compatible
app.include_router(gateway.router)
