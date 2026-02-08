from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.api.routes import health, providers, models, deployments, routing, compliance, export, costs, users, policies, audit, ai, auth, onboarding, notifications, analytics, gateway
from app.middleware.security import (
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    configure_cors,
)
from app.middleware.audit import AuditMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Bonito API",
    description="Enterprise AI Platform API",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware is applied in reverse order (last added = first executed)
# Order of execution: RequestID → SecurityHeaders → RateLimit → CORS → AuditMiddleware → route

# Audit (innermost — runs closest to route handler, captures response status)
app.add_middleware(AuditMiddleware)

# CORS
configure_cors(app)

# Rate limiting
app.add_middleware(RateLimitMiddleware)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Request ID (outermost — ensures all responses get an ID)
app.add_middleware(RequestIDMiddleware)

# Routes
app.include_router(health.router, prefix="/api")
app.include_router(providers.router, prefix="/api")
app.include_router(models.router, prefix="/api")
app.include_router(deployments.router, prefix="/api")
app.include_router(routing.router, prefix="/api")
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
