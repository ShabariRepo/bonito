"""
Standard API response schemas and error handling.
Ensures consistent JSON responses across all endpoints.
"""

from typing import Any, Optional, Dict
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import traceback
import logging

logger = logging.getLogger(__name__)


class APIResponse(BaseModel):
    """Standard API response envelope."""
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    request_id: Optional[str] = None


class ErrorDetail(BaseModel):
    """Detailed error information."""
    code: str
    message: str
    field: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error: ErrorDetail
    request_id: Optional[str] = None


def success_response(
    data: Any = None, 
    message: str = None,
    request_id: str = None
) -> APIResponse:
    """Create a successful API response."""
    return APIResponse(
        success=True,
        data=data,
        message=message,
        request_id=request_id
    )


def error_response(
    code: str,
    message: str,
    field: str = None,
    request_id: str = None,
    status_code: int = 400
) -> JSONResponse:
    """Create a standardized error response."""
    error_resp = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            field=field
        ),
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=status_code,
        content=error_resp.dict()
    )


async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    """Global HTTP exception handler with consistent error format."""
    request_id = getattr(request.state, 'request_id', None)
    
    # Log the error
    logger.error(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code
        }
    )
    
    return error_response(
        code=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        request_id=request_id,
        status_code=exc.status_code
    )


async def handle_general_exception(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors."""
    request_id = getattr(request.state, 'request_id', None)
    
    # Log the full traceback — always, so we can actually debug production issues
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {type(exc).__name__}: {str(exc)}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc()
        }
    )
    # Also print to stderr for Railway log capture
    import sys
    print(f"[ERROR] {request.method} {request.url.path} → {type(exc).__name__}: {str(exc)}", file=sys.stderr)
    
    # For gateway /v1/* endpoints, always return the real error (developers need it).
    # For other endpoints, hide internals in production.
    from app.core.config import settings
    is_gateway = request.url.path.startswith("/v1/")
    if is_gateway:
        message = f"{type(exc).__name__}: {str(exc)}"
    elif settings.production_mode:
        message = "Something went wrong. Please try again or contact support."
    else:
        message = str(exc)
    
    return error_response(
        code="INTERNAL_ERROR",
        message=message,
        request_id=request_id,
        status_code=500
    )


# Common error codes
class ErrorCodes:
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    RATE_LIMITED = "RATE_LIMITED"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"