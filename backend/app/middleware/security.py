"""Security middleware: rate limiting, request IDs, security headers."""

import uuid
import time
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.redis import redis_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate-limit tiers: (prefix_match, requests, window_seconds)
# ---------------------------------------------------------------------------
RATE_LIMIT_TIERS = [
    ("/api/auth/", 10, 60),
    ("/api/providers/connect", 10, 60),
    ("/api/routing/invoke", 20, 60),
    ("/api/providers/", 20, 60),  # covers /invoke sub-paths too
]
DEFAULT_RATE_LIMIT = (100, 60)  # requests, window


def _get_rate_limit(path: str) -> tuple[int, int]:
    for prefix, limit, window in RATE_LIMIT_TIERS:
        if path.startswith(prefix):
            # Specifically check invoke paths
            if "/invoke" in path:
                return 20, 60
            return limit, window
    return DEFAULT_RATE_LIMIT


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ---------------------------------------------------------------------------
# Rate Limiting Middleware
# ---------------------------------------------------------------------------
class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip = _client_ip(request)
        path = request.url.path
        limit, window = _get_rate_limit(path)

        # Determine bucket key based on tier
        # Use the matching prefix as part of the key for granularity
        bucket = "general"
        for prefix, _, _ in RATE_LIMIT_TIERS:
            if path.startswith(prefix):
                bucket = prefix.strip("/").replace("/", ":")
                break
        if "/invoke" in path:
            bucket = "invoke"

        key = f"rl:{bucket}:{ip}"

        try:
            pipe = redis_client.pipeline()
            pipe.incr(key)
            pipe.ttl(key)
            count, ttl = await pipe.execute()

            if ttl == -1:  # no expiry set yet
                await redis_client.expire(key, window)

            if count > limit:
                retry_after = ttl if ttl > 0 else window
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Try again later."},
                    headers={"Retry-After": str(retry_after)},
                )
        except Exception:
            # Redis down — fail open (don't block requests)
            logger.warning("Rate limiter: Redis unavailable, passing through")

        return await call_next(request)


# ---------------------------------------------------------------------------
# Request ID Middleware
# ---------------------------------------------------------------------------
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ---------------------------------------------------------------------------
# Security Headers Middleware
# ---------------------------------------------------------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        response.headers["Cache-Control"] = "no-store"
        if not _is_dev():
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response


# ---------------------------------------------------------------------------
# CORS helper
# ---------------------------------------------------------------------------
def _is_dev() -> bool:
    return "localhost" in settings.cors_origins or "127.0.0.1" in settings.cors_origins


def configure_cors(app: FastAPI) -> None:
    """Apply CORS: permissive in dev, restrictive in prod."""
    if _is_dev():
        origins = settings.cors_origins.split(",")
        allow_methods = ["*"]
        allow_headers = ["*"]
    else:
        origins = settings.cors_origins.split(",")
        allow_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
        allow_headers = [
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "Accept",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=allow_methods,
        allow_headers=allow_headers,
    )
