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
from app.core.redis import get_redis

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
    """Return the direct connection IP for rate-limiting.

    Never trust X-Forwarded-For blindly — it can be spoofed by any client.
    We use the socket-level peer address which cannot be forged.
    """
    return request.client.host if request.client else "unknown"


# ---------------------------------------------------------------------------
# Request Body Size Limit Middleware
# ---------------------------------------------------------------------------
# Maximum body size for /v1/* gateway endpoints (1 MB).
# Other endpoints (dashboard API) are not restricted here.
GATEWAY_MAX_BODY_BYTES = 1 * 1024 * 1024


class RequestBodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject oversized request bodies on gateway /v1/* endpoints.

    This prevents attackers from sending massive prompts that incur
    cloud costs. Returns 413 Payload Too Large if exceeded.
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/v1/"):
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > GATEWAY_MAX_BODY_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "message": f"Request body too large. Maximum size is {GATEWAY_MAX_BODY_BYTES // 1024}KB.",
                            "type": "invalid_request_error",
                            "code": "payload_too_large",
                        }
                    },
                )
        return await call_next(request)


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
            client = await get_redis()
            pipe = client.pipeline()
            pipe.incr(key)
            pipe.ttl(key)
            count, ttl = await pipe.execute()

            if ttl == -1:  # no expiry set yet
                await client.expire(key, window)

            if count > limit:
                retry_after = ttl if ttl > 0 else window
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Try again later."},
                    headers={"Retry-After": str(retry_after)},
                )
        except Exception as e:
            # Redis down — fail closed (return 429) in production for security
            logger.error(f"Rate limiter: Redis unavailable: {e}")
            if not _is_dev():
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limiting service unavailable. Please try again later."},
                    headers={"Retry-After": "60"},
                )
            # In dev mode, log warning but continue
            logger.warning("Rate limiter: Redis unavailable in dev mode, passing through")

        return await call_next(request)


# ---------------------------------------------------------------------------
# Request ID Middleware
# ---------------------------------------------------------------------------
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        
        start_time = time.time()
        response: Response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)
        
        # Log the request
        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }
        )
        
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
