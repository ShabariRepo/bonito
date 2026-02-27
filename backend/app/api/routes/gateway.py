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
from app.models.routing_policy import RoutingPolicy
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
from app.core.database import get_db_session
from app.services import gateway as gateway_service
from app.services.gateway import PolicyViolation
from app.models.cloud_provider import CloudProvider
from app.models.model import Model
from app.services.usage_tracker import usage_tracker
from app.services.managed_inference import calculate_marked_up_cost

logger = logging.getLogger(__name__)


async def _resolve_provider(model_name: str, org_id, db: AsyncSession) -> Optional[str]:
    """Look up the cloud provider type for a model from the DB."""
    try:
        async with db.begin_nested():
            result = await db.execute(
                select(CloudProvider.provider_type)
                .join(Model, Model.provider_id == CloudProvider.id)
                .where(
                    and_(
                        CloudProvider.org_id == org_id,
                        Model.model_id == model_name,
                    )
                )
                .limit(1)
            )
            row = result.scalar_one_or_none()
            if row:
                return row
    except Exception:
        pass
    # Fallback: heuristic from model name
    if any(k in model_name for k in ("bedrock", "anthropic", "amazon", "nova", "titan")):
        return "aws"
    elif any(k in model_name for k in ("azure", "gpt-", "o1-", "o3-", "o4-", "dall-e")):
        return "azure"
    elif any(k in model_name for k in ("vertex", "gemini", "palm")):
        return "gcp"
    return None

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


# Custom auth dependency that handles both gateway keys and routing policies
async def get_auth_context(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> tuple[Optional[GatewayKey], Optional[RoutingPolicy]]:
    """Get authentication context - either a gateway key or routing policy."""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")

    raw_key = credentials.credentials
    
    # Check for routing policy key (rt-xxxxxxxx format)
    if raw_key.startswith("rt-"):
        policy = await gateway_service.resolve_routing_policy_by_key(raw_key, db)
        if not policy:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid routing policy key")
        return None, policy
    
    # Check for regular gateway key (bn- format)
    elif raw_key.startswith("bn-"):
        key = await gateway_service.validate_api_key(db, raw_key)
        if not key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked API key")

        # Check rate limit
        allowed = await gateway_service.check_rate_limit(key.id, key.rate_limit)
        if not allowed:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

        return key, None
    
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key format")


# ─── OpenAI-compatible endpoints (/v1/*) ───

@router.post("/v1/chat/completions")
async def chat_completions(
    raw_request: Request,
    request: ChatCompletionRequest,
    auth_context: tuple[Optional[GatewayKey], Optional[RoutingPolicy]] = Depends(get_auth_context),
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

    key, policy = auth_context
    
    # Track usage (check limits before processing request)
    org_id = key.org_id if key else (policy.org_id if policy else None)
    if org_id:
        try:
            await usage_tracker.track_gateway_request(db, str(org_id))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(e)
            )

    # Detect knowledge base from header
    kb_header = raw_request.headers.get("X-Bonito-Knowledge-Base")
    
    # Handle routing policy requests
    if policy:
        try:
            data = request.model_dump(exclude_none=True)
            
            # Inject knowledge base if specified in header
            if kb_header:
                data.setdefault("bonito", {})["knowledge_base"] = kb_header
            
            # Apply routing policy to select model
            selected_model = await gateway_service.apply_routing_policy(policy, data, db)
            data["model"] = selected_model
            
            # Log which policy was used
            logger.info(f"Applied routing policy {policy.name} (id: {policy.id}) for request")
            
            # Use the policy's org_id; key_id must be None (FK to gateway_keys)
            org_id = policy.org_id
            key_id = None  # Routing policy requests don't have a gateway key
            
            # Streaming path
            if request.stream:
                return await _handle_streaming_completion_policy(data, org_id, key_id, db)
            
            # Non-streaming path
            result = await gateway_service.chat_completion(data, org_id, key_id, db)
            return result
            
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Routing error: {str(e)}")
    
    # Handle regular gateway key requests
    elif key:
        # Check monthly gateway call limit based on tier
        try:
            from app.services.feature_gate import feature_gate
            await feature_gate.require_usage_limit(db, str(key.org_id), "gateway_calls_per_month")
        except HTTPException as e:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=e.detail)

        # Policy enforcement — check before forwarding to upstream
        try:
            await gateway_service.enforce_policies(db, key, request.model)
        except PolicyViolation as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)
        except Exception as e:
            logger.error(f"Policy enforcement failed: {type(e).__name__}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Policy check failed: {str(e)}")

        try:
            data = request.model_dump(exclude_none=True)
            
            # Inject knowledge base if specified in header
            if kb_header:
                data.setdefault("bonito", {})["knowledge_base"] = kb_header

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
            logger.error(f"Gateway completion failed: {type(e).__name__}: {e}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Upstream error: {str(e)}")
    
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")


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

    # Capture org/key IDs — the db session from the dependency will be
    # closed by the time the SSE generator's finally block runs, so we
    # log in a standalone session instead.
    org_id = key.org_id
    key_id = key.id

    # Capture messages for token estimation (streaming chunks often lack usage)
    messages = request_data.get("messages", [])

    async def sse_generator():
        total_prompt_tokens = 0
        total_completion_tokens = 0
        model_used = model
        error_occurred = False
        error_message = None
        streamed_content = []

        try:
            response = await router.acompletion(**request_data)

            async for chunk in response:
                chunk_dict = chunk.model_dump()
                if chunk_dict.get("model"):
                    model_used = chunk_dict["model"]

                # Accumulate token counts if the provider includes them
                usage = chunk_dict.get("usage")
                if usage:
                    total_prompt_tokens = usage.get("prompt_tokens", total_prompt_tokens)
                    total_completion_tokens = usage.get("completion_tokens", total_completion_tokens)

                # Track streamed content for token estimation fallback
                choices = chunk_dict.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        streamed_content.append(content)

                yield f"data: {json.dumps(chunk_dict)}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            error_occurred = True
            error_message = str(e)[:1000]
            error_data = {
                "error": {
                    "message": str(e),
                    "type": "upstream_error",
                }
            }
            yield f"data: {json.dumps(error_data)}\n\n"
            yield "data: [DONE]\n\n"

        finally:
            elapsed_ms = int((time.time() - start) * 1000)

            # Estimate tokens if the provider didn't include them in chunks
            if not total_prompt_tokens and messages:
                try:
                    total_prompt_tokens = litellm.token_counter(
                        model=model_used, messages=messages
                    )
                except Exception:
                    pass
            if not total_completion_tokens and streamed_content:
                try:
                    full_output = "".join(streamed_content)
                    total_completion_tokens = litellm.token_counter(
                        model=model_used,
                        text=full_output,
                    )
                except Exception:
                    pass

            cost = 0.0
            try:
                if total_prompt_tokens or total_completion_tokens:
                    # Determine the provider-prefixed model name for cost lookup
                    cost_model = model_used
                    if "bedrock" not in cost_model and "azure" not in cost_model and "vertex_ai" not in cost_model:
                        if "amazon" in cost_model or "anthropic.claude" in cost_model or "meta.llama" in cost_model:
                            cost_model = f"bedrock/{cost_model}"
                        elif "gemini" in cost_model:
                            cost_model = f"vertex_ai/{cost_model}"
                    prompt_cost, compl_cost = litellm.cost_per_token(
                        model=cost_model,
                        prompt_tokens=total_prompt_tokens,
                        completion_tokens=total_completion_tokens,
                    )
                    cost = (prompt_cost + compl_cost) or 0.0
            except Exception:
                pass

            try:
                async with get_db_session() as log_db:
                    provider = await _resolve_provider(model_used or model, org_id, log_db)
                    log_entry = GatewayRequest(
                        org_id=org_id,
                        key_id=key_id,
                        model_requested=model,
                        model_used=model_used,
                        status="error" if error_occurred else "success",
                        error_message=error_message,
                        input_tokens=total_prompt_tokens,
                        output_tokens=total_completion_tokens,
                        latency_ms=elapsed_ms,
                        cost=cost,
                        provider=provider,
                    )
                    log_db.add(log_entry)
                    await log_db.flush()

                    # Track managed inference (markup + provider counters)
                    if not error_occurred and provider and cost > 0:
                        try:
                            from app.services.gateway import _track_managed_inference
                            await _track_managed_inference(log_db, log_entry, org_id)
                        except Exception as mi_err:
                            logger.warning(f"Failed to track managed inference (streaming): {mi_err}")
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


async def _handle_streaming_completion_policy(
    request_data: dict,
    org_id: uuid.UUID,
    policy_id: uuid.UUID,
    db: AsyncSession,
):
    """Handle a streaming chat completion with routing policy — returns SSE StreamingResponse."""
    import time
    import litellm

    router = await gateway_service.get_router(db, org_id)
    model = request_data.get("model", "")
    start = time.time()

    # Ensure stream=True in the request data
    request_data["stream"] = True
    messages = request_data.get("messages", [])

    async def sse_generator():
        total_prompt_tokens = 0
        total_completion_tokens = 0
        model_used = model
        error_occurred = False
        error_message = None
        streamed_content = []

        try:
            response = await router.acompletion(**request_data)

            async for chunk in response:
                chunk_dict = chunk.model_dump()
                if chunk_dict.get("model"):
                    model_used = chunk_dict["model"]

                usage = chunk_dict.get("usage")
                if usage:
                    total_prompt_tokens = usage.get("prompt_tokens", total_prompt_tokens)
                    total_completion_tokens = usage.get("completion_tokens", total_completion_tokens)

                choices = chunk_dict.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        streamed_content.append(content)

                yield f"data: {json.dumps(chunk_dict)}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            error_occurred = True
            error_message = str(e)[:1000]
            error_data = {
                "error": {
                    "message": str(e),
                    "type": "upstream_error",
                }
            }
            yield f"data: {json.dumps(error_data)}\n\n"
            yield "data: [DONE]\n\n"

        finally:
            elapsed_ms = int((time.time() - start) * 1000)

            if not total_prompt_tokens and messages:
                try:
                    total_prompt_tokens = litellm.token_counter(
                        model=model_used, messages=messages
                    )
                except Exception:
                    pass
            if not total_completion_tokens and streamed_content:
                try:
                    total_completion_tokens = litellm.token_counter(
                        model=model_used, text="".join(streamed_content)
                    )
                except Exception:
                    pass

            cost = 0.0
            try:
                if total_prompt_tokens or total_completion_tokens:
                    cost_model = model_used
                    if "bedrock" not in cost_model and "azure" not in cost_model and "vertex_ai" not in cost_model:
                        if "amazon" in cost_model or "anthropic.claude" in cost_model or "meta.llama" in cost_model:
                            cost_model = f"bedrock/{cost_model}"
                        elif "gemini" in cost_model:
                            cost_model = f"vertex_ai/{cost_model}"
                    prompt_cost, compl_cost = litellm.cost_per_token(
                        model=cost_model,
                        prompt_tokens=total_prompt_tokens,
                        completion_tokens=total_completion_tokens,
                    )
                    cost = (prompt_cost + compl_cost) or 0.0
            except Exception:
                pass

            try:
                async with get_db_session() as log_db:
                    provider = await _resolve_provider(model_used or model, org_id, log_db)
                    log_entry = GatewayRequest(
                        org_id=org_id,
                        key_id=None,  # Routing policy requests don't have a gateway key
                        model_requested=model,
                        model_used=model_used,
                        status="error" if error_occurred else "success",
                        error_message=error_message,
                        input_tokens=total_prompt_tokens,
                        output_tokens=total_completion_tokens,
                        latency_ms=elapsed_ms,
                        cost=cost,
                        provider=provider,
                    )
                    log_db.add(log_entry)
                    await log_db.flush()

                    # Track managed inference (markup + provider counters)
                    if not error_occurred and provider and cost > 0:
                        try:
                            from app.services.gateway import _track_managed_inference
                            await _track_managed_inference(log_db, log_entry, org_id)
                        except Exception as mi_err:
                            logger.warning(f"Failed to track managed inference (streaming policy): {mi_err}")
            except Exception as log_err:
                logger.error(f"Failed to log streaming policy request: {log_err}")

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
        allowed_models=key.allowed_models,
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
    await db.refresh(config)
    
    # Reset router to pick up configuration changes
    await gateway_service.reset_router(org_id=user.org_id)
    
    return config
