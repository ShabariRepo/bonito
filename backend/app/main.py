from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.responses import handle_http_exception, handle_general_exception
from app.api.routes import health, providers, models, deployments, routing, compliance, export, costs, users, policies, audit, ai, auth, onboarding, notifications, analytics, gateway, routing_policies
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
    
    # Run Alembic migrations automatically on startup (safe — idempotent)
    try:
        import logging
        import os
        _log = logging.getLogger("bonito.startup")
        _log.info("Running database migrations...")
        from alembic.config import Config as AlembicConfig
        from alembic import command as alembic_command
        
        # Resolve paths relative to the backend directory
        backend_dir = os.path.join(os.path.dirname(__file__), "..")
        alembic_cfg = AlembicConfig(os.path.join(backend_dir, "alembic.ini"))
        alembic_cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
        
        # Use sync URL for Alembic (strip asyncpg)
        sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
        
        alembic_command.upgrade(alembic_cfg, "head")
        _log.info("Database migrations complete.")
    except Exception as e:
        import logging
        logging.getLogger("bonito.startup").warning(f"Migration failed (non-fatal): {e}")
    
    yield
    
    # Shutdown: Clean up connections
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

# Gateway routes — mounted at root (not /api) because /v1/* is OpenAI-compatible
app.include_router(gateway.router)
