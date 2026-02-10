"""
API Gateway routes — OpenAI-compatible proxy + management endpoints.

Auth model:
- /v1/* endpoints: authenticated via Gateway API key (Bearer bn-...)
- /api/gateway/* endpoints: authenticated via JWT (dashboard user)
"""

import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.gateway import GatewayKey, GatewayRequest, GatewayConfig
from app.schemas.gateway import (
    ChatCompletionRequest,
    CompletionRequest,
    EmbeddingRequest,
    GatewayKeyCreate,
    GatewayKeyResponse,
    GatewayKeyCreated,
    GatewayLogEntry,
    UsageSummary,
    GatewayConfigResponse,
    GatewayConfigUpdate,
)
from app.services import gateway as gateway_service
from app.services.gateway import PolicyViolation

logger = logging.getLogger(__name__)

router = APIRouter(tags=["gateway"])

bearer_scheme = HTTPBearer(auto_error=False)

# Maximum request body size for /v1/* endpoints (1 MB)
MAX_REQUEST_BODY_BYTES = 1 * 1024 * 1024


# ─── Gateway API key auth dependency ───

async def get_gateway_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> GatewayKey:
    """Authenticate a gateway request via API key."""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")

    raw_key = credentials.credentials
    if not raw_key.startswith("bn-"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key format")

    key = await gateway_service.validate_api_key(db, raw_key)
    if not key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked API key")

    # Check rate limit
    allowed = await gateway_service.check_rate_limit(key.id, key.rate_limit)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

    return key


# ─── OpenAI-compatible endpoints (/v1/*) ───

@router.post("/v1/chat/completions")
async def chat_completions(
    raw_request: Request,
    request: ChatCompletionRequest,
    key: GatewayKey = Depends(get_gateway_key),
    db: AsyncSession = Depends(get_db),
):
    """OpenAI-compatible chat completions endpoint."""
    # Body size check — reject oversized payloads before any processing
    content_length = raw_request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_BODY_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Request body too large. Maximum size is {MAX_REQUEST_BODY_BYTES // 1024}KB.",
        )

    # Policy enforcement — check before forwarding to upstream
    try:
        await gateway_service.enforce_policies(db, key, request.model)
    except PolicyViolation as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    try:
        data = request.model_dump(exclude_none=True)

        # Streaming path
        if request.stream:
            return await _handle_streaming_completion(data, key, db)

        # Non-streaming path (existing behavior)
        result = await gateway_service.chat_completion(data, key.org_id, key.id, db)
        return result
    except HTTPException:
        raise
    except PolicyViolation as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Upstream error: {str(e)}")


async def _handle_streaming_completion(
    request_data: dict,
    key: GatewayKey,
    db: AsyncSession,
):
    """Handle a streaming chat completion — returns SSE StreamingResponse."""
    import time
    import litellm

    router = await gateway_service.get_router(db, key.org_id)
    model = request_data.get("model", "")
    start = time.time()

    # Ensure stream=True in the request data
    request_data["stream"] = True

    log_entry = GatewayRequest(
        org_id=key.org_id,
        key_id=key.id,
        model_requested=model,
        status="success",
    )

    async def sse_generator():
        total_prompt_tokens = 0
        total_completion_tokens = 0
        model_used = model
        error_occurred = False

        try:
            response = await router.acompletion(**request_data)

            async for chunk in response:
                # Extract usage from chunks if available
                chunk_dict = chunk.model_dump()
                if chunk_dict.get("model"):
                    model_used = chunk_dict["model"]

                # Accumulate token counts from the last chunk (OpenAI includes usage in final chunk)
                usage = chunk_dict.get("usage")
                if usage:
                    total_prompt_tokens = usage.get("prompt_tokens", total_prompt_tokens)
                    total_completion_tokens = usage.get("completion_tokens", total_completion_tokens)

                yield f"data: {json.dumps(chunk_dict)}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            error_occurred = True
            log_entry.status = "error"
            log_entry.error_message = str(e)[:1000]
            # Send error as SSE event before closing
            error_data = {
                "error": {
                    "message": str(e),
                    "type": "upstream_error",
                }
            }
            yield f"data: {json.dumps(error_data)}\n\n"
            yield "data: [DONE]\n\n"

        finally:
            # Log the completed request
            elapsed_ms = int((time.time() - start) * 1000)
            log_entry.model_used = model_used
            log_entry.input_tokens = total_prompt_tokens
            log_entry.output_tokens = total_completion_tokens
            log_entry.latency_ms = elapsed_ms

            # Attempt to compute cost from token counts
            try:
                if total_prompt_tokens or total_completion_tokens:
                    log_entry.cost = litellm.completion_cost(
                        model=model_used,
                        prompt_tokens=total_prompt_tokens,
                        completion_tokens=total_completion_tokens,
                    ) or 0.0
                else:
                    log_entry.cost = 0.0
            except Exception:
                log_entry.cost = 0.0

            # Determine provider
            if "bedrock" in model_used or "anthropic" in model_used or "amazon" in model_used:
                log_entry.provider = "aws"
            elif "azure" in model_used:
                log_entry.provider = "azure"
            elif "vertex" in model_used or "gemini" in model_used:
                log_entry.provider = "gcp"

            try:
                db.add(log_entry)
                await db.flush()
            except Exception as log_err:
                logger.error(f"Failed to log streaming request: {log_err}")

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/v1/completions")
async def completions(
    raw_request: Request,
    request: CompletionRequest,
    key: GatewayKey = Depends(get_gateway_key),
    db: AsyncSession = Depends(get_db),
):
    """Legacy completions endpoint."""
    # Body size check
    content_length = raw_request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_BODY_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Request body too large. Maximum size is {MAX_REQUEST_BODY_BYTES // 1024}KB.",
        )

    # Policy enforcement
    try:
        await gateway_service.enforce_policies(db, key, request.model)
    except PolicyViolation as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    try:
        data = request.model_dump(exclude_none=True)
        result = await gateway_service.completion(data, key.org_id, key.id, db)
        return result
    except HTTPException:
        raise
    except PolicyViolation as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Upstream error: {str(e)}")


@router.post("/v1/embeddings")
async def embeddings(
    raw_request: Request,
    request: EmbeddingRequest,
    key: GatewayKey = Depends(get_gateway_key),
    db: AsyncSession = Depends(get_db),
):
    """Embeddings endpoint."""
    # Body size check
    content_length = raw_request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_BODY_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Request body too large. Maximum size is {MAX_REQUEST_BODY_BYTES // 1024}KB.",
        )

    # Policy enforcement
    try:
        await gateway_service.enforce_policies(db, key, request.model)
    except PolicyViolation as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    try:
        data = request.model_dump(exclude_none=True)
        result = await gateway_service.embedding(data, key.org_id, key.id, db)
        return result
    except HTTPException:
        raise
    except PolicyViolation as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Upstream error: {str(e)}")


@router.get("/v1/models")
async def list_models(
    key: GatewayKey = Depends(get_gateway_key),
    db: AsyncSession = Depends(get_db),
):
    """List available models."""
    models = await gateway_service.get_available_models(db, key.org_id)
    return {"object": "list", "data": models}


# ─── Dashboard management endpoints (/api/gateway/*) ───

@router.get("/api/gateway/usage", response_model=UsageSummary)
async def get_usage(
    days: int = 30,
    team_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get gateway usage statistics."""
    stats = await gateway_service.get_usage_stats(db, user.org_id, days=days, team_id=team_id)
    return stats


@router.get("/api/gateway/keys", response_model=list[GatewayKeyResponse])
async def list_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all API keys for the org."""
    result = await db.execute(
        select(GatewayKey)
        .where(GatewayKey.org_id == user.org_id)
        .order_by(GatewayKey.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/api/gateway/keys", response_model=GatewayKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_key(
    body: GatewayKeyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new gateway API key."""
    raw_key, key_hash, key_prefix = gateway_service.generate_api_key()

    key = GatewayKey(
        org_id=user.org_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=body.name,
        team_id=body.team_id,
        rate_limit=body.rate_limit,
        allowed_models=body.allowed_models,
    )
    db.add(key)
    await db.flush()

    return GatewayKeyCreated(
        id=key.id,
        name=key.name,
        key_prefix=key.key_prefix,
        team_id=key.team_id,
        rate_limit=key.rate_limit,
        created_at=key.created_at,
        key=raw_key,
    )


@router.delete("/api/gateway/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_key(
    key_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a gateway API key."""
    result = await db.execute(
        select(GatewayKey).where(
            and_(GatewayKey.id == key_id, GatewayKey.org_id == user.org_id)
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    if key.revoked_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Key already revoked")

    key.revoked_at = datetime.now(timezone.utc)
    await db.flush()


@router.get("/api/gateway/logs", response_model=list[GatewayLogEntry])
async def get_logs(
    limit: int = 50,
    offset: int = 0,
    model: Optional[str] = None,
    status_filter: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get gateway request logs."""
    logs = await gateway_service.get_request_logs(
        db, user.org_id, limit=limit, offset=offset, model=model, status=status_filter
    )
    return logs


@router.get("/api/gateway/config", response_model=GatewayConfigResponse)
async def get_gateway_config(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get gateway configuration for the organization."""
    result = await db.execute(
        select(GatewayConfig).where(GatewayConfig.org_id == user.org_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        # Create default config if none exists
        config = GatewayConfig(
            org_id=user.org_id,
            enabled_providers={"aws": True, "azure": True, "gcp": True},
            routing_strategy="cost-optimized",
            fallback_models={},
            default_rate_limit=60,
            cost_tracking_enabled=True,
            custom_routing_rules={}
        )
        db.add(config)
        await db.flush()
    
    return config


@router.put("/api/gateway/config", response_model=GatewayConfigResponse)
async def update_gateway_config(
    body: GatewayConfigUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update gateway configuration for the organization."""
    result = await db.execute(
        select(GatewayConfig).where(GatewayConfig.org_id == user.org_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        # Create new config if none exists
        config = GatewayConfig(
            org_id=user.org_id,
            enabled_providers={"aws": True, "azure": True, "gcp": True},
            routing_strategy="cost-optimized",
            fallback_models={},
            default_rate_limit=60,
            cost_tracking_enabled=True,
            custom_routing_rules={}
        )
        db.add(config)
    
    # Update provided fields
    update_data = body.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    
    await db.flush()
    
    # Reset router to pick up configuration changes
    await gateway_service.reset_router(org_id=user.org_id)
    
    return config
