"""
API Gateway routes — OpenAI-compatible proxy + management endpoints.

Auth model:
- /v1/* endpoints: authenticated via Gateway API key (Bearer bn-...)
- /api/gateway/* endpoints: authenticated via JWT (dashboard user)
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.gateway import GatewayKey, GatewayRequest
from app.schemas.gateway import (
    ChatCompletionRequest,
    CompletionRequest,
    EmbeddingRequest,
    GatewayKeyCreate,
    GatewayKeyResponse,
    GatewayKeyCreated,
    GatewayLogEntry,
    UsageSummary,
)
from app.services import gateway as gateway_service

router = APIRouter(tags=["gateway"])

bearer_scheme = HTTPBearer(auto_error=False)


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
    request: ChatCompletionRequest,
    key: GatewayKey = Depends(get_gateway_key),
    db: AsyncSession = Depends(get_db),
):
    """OpenAI-compatible chat completions endpoint."""
    try:
        data = request.model_dump(exclude_none=True)
        result = await gateway_service.chat_completion(data, key.org_id, key.id, db)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Upstream error: {str(e)}")


@router.post("/v1/completions")
async def completions(
    request: CompletionRequest,
    key: GatewayKey = Depends(get_gateway_key),
    db: AsyncSession = Depends(get_db),
):
    """Legacy completions endpoint."""
    try:
        data = request.model_dump(exclude_none=True)
        result = await gateway_service.completion(data, key.org_id, key.id, db)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Upstream error: {str(e)}")


@router.post("/v1/embeddings")
async def embeddings(
    request: EmbeddingRequest,
    key: GatewayKey = Depends(get_gateway_key),
    db: AsyncSession = Depends(get_db),
):
    """Embeddings endpoint."""
    try:
        data = request.model_dump(exclude_none=True)
        result = await gateway_service.embedding(data, key.org_id, key.id, db)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Upstream error: {str(e)}")


@router.get("/v1/models")
async def list_models(key: GatewayKey = Depends(get_gateway_key)):
    """List available models."""
    models = await gateway_service.get_available_models()
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
