"""
LiteLLM Gateway Service — wraps LiteLLM for multi-provider AI routing.

Reads provider credentials from Vault, configures LiteLLM model list,
and provides completion/embedding calls with automatic failover.
"""

import time
import uuid
import hashlib
import secrets
import logging
from datetime import datetime, timezone
from typing import Optional

import litellm
from sqlalchemy import select, func, and_, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.vault import vault_client
from app.core.redis import redis_client
from app.models.gateway import GatewayRequest, GatewayKey, GatewayRateLimit
from app.schemas.gateway import RoutingStrategy

logger = logging.getLogger(__name__)

# Suppress litellm's verbose logging
litellm.suppress_debug_info = True
litellm.drop_params = True  # silently drop unsupported params per provider


# ─── Provider credential mapping ───

PROVIDER_MODEL_PREFIXES = {
    "aws": "bedrock/",
    "azure": "azure/",
    "gcp": "vertex_ai/",
}


async def _get_provider_credentials() -> dict:
    """Fetch all provider credentials from Vault."""
    creds = {}
    for provider in ("aws", "azure", "gcp"):
        try:
            data = await vault_client.get_secrets(f"providers/{provider}")
            if data:
                creds[provider] = data
        except Exception as e:
            logger.warning(f"Failed to fetch {provider} credentials: {e}")
    return creds


async def _build_model_list(creds: dict) -> list[dict]:
    """Build LiteLLM model_list from available provider credentials."""
    model_list = []

    if "aws" in creds:
        c = creds["aws"]
        common = {
            "aws_access_key_id": c.get("access_key_id", ""),
            "aws_secret_access_key": c.get("secret_access_key", ""),
            "aws_region_name": c.get("region", "us-east-1"),
        }
        for model in [
            "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "anthropic.claude-3-haiku-20240307-v1:0",
            "amazon.titan-embed-text-v2:0",
            "meta.llama3-70b-instruct-v1:0",
        ]:
            model_list.append({
                "model_name": model,
                "litellm_params": {"model": f"bedrock/{model}", **common},
            })

    if "azure" in creds:
        c = creds["azure"]
        base_url = c.get("endpoint", "")
        api_key = c.get("client_secret", "")
        if base_url and api_key:
            for model, deployment in [
                ("gpt-4o", "gpt-4o"),
                ("gpt-4o-mini", "gpt-4o-mini"),
                ("text-embedding-3-small", "text-embedding-3-small"),
            ]:
                model_list.append({
                    "model_name": model,
                    "litellm_params": {
                        "model": f"azure/{deployment}",
                        "api_base": base_url,
                        "api_key": api_key,
                        "api_version": "2024-02-01",
                    },
                })

    if "gcp" in creds:
        c = creds["gcp"]
        project = c.get("project_id", "")
        region = c.get("region", "us-central1")
        for model in [
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "text-embedding-004",
        ]:
            model_list.append({
                "model_name": model,
                "litellm_params": {
                    "model": f"vertex_ai/{model}",
                    "vertex_project": project,
                    "vertex_location": region,
                },
            })

    return model_list


# ─── Router singleton ───

_router: Optional[litellm.Router] = None


async def get_router() -> litellm.Router:
    """Get or create the LiteLLM router with current provider configs."""
    global _router
    if _router is not None:
        return _router

    creds = await _get_provider_credentials()
    model_list = await _build_model_list(creds)

    if not model_list:
        # Return a router with empty model list — calls will fail gracefully
        _router = litellm.Router(model_list=[], routing_strategy="simple-shuffle")
        return _router

    _router = litellm.Router(
        model_list=model_list,
        routing_strategy="simple-shuffle",
        num_retries=2,
        retry_after=1,
        timeout=60,
        allowed_fails=2,
        cooldown_time=30,
    )
    return _router


async def reset_router():
    """Force router re-initialization (e.g. after adding a new provider)."""
    global _router
    _router = None


async def get_available_models() -> list[dict]:
    """Return list of available models from all configured providers."""
    creds = await _get_provider_credentials()
    model_list = await _build_model_list(creds)
    seen = set()
    models = []
    for m in model_list:
        name = m["model_name"]
        if name not in seen:
            seen.add(name)
            provider = "unknown"
            lp = m["litellm_params"]["model"]
            if lp.startswith("bedrock/"):
                provider = "aws"
            elif lp.startswith("azure/"):
                provider = "azure"
            elif lp.startswith("vertex_ai/"):
                provider = "gcp"
            models.append({"id": name, "object": "model", "created": 0, "owned_by": provider})
    return models


# ─── Completions ───

async def chat_completion(
    request_data: dict,
    org_id: uuid.UUID,
    key_id: uuid.UUID,
    db: AsyncSession,
) -> dict:
    """Execute a chat completion via LiteLLM router and log the request."""
    router = await get_router()
    model = request_data.get("model", "")
    start = time.time()

    log_entry = GatewayRequest(
        org_id=org_id,
        key_id=key_id,
        model_requested=model,
        status="success",
    )

    try:
        response = await router.acompletion(**request_data)
        elapsed_ms = int((time.time() - start) * 1000)

        usage = getattr(response, "usage", None)
        log_entry.model_used = getattr(response, "model", model)
        log_entry.input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        log_entry.output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        log_entry.latency_ms = elapsed_ms
        log_entry.cost = litellm.completion_cost(completion_response=response) or 0.0

        # Determine provider from model used
        model_used = log_entry.model_used or ""
        if "bedrock" in model_used or "anthropic" in model_used or "amazon" in model_used:
            log_entry.provider = "aws"
        elif "azure" in model_used:
            log_entry.provider = "azure"
        elif "vertex" in model_used or "gemini" in model_used:
            log_entry.provider = "gcp"

        db.add(log_entry)
        await db.flush()

        return response.model_dump()

    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        log_entry.status = "error"
        log_entry.error_message = str(e)[:1000]
        log_entry.latency_ms = elapsed_ms
        db.add(log_entry)
        await db.flush()
        raise


async def completion(request_data: dict, org_id: uuid.UUID, key_id: uuid.UUID, db: AsyncSession) -> dict:
    """Legacy text completion."""
    router = await get_router()
    model = request_data.get("model", "")
    start = time.time()

    log_entry = GatewayRequest(org_id=org_id, key_id=key_id, model_requested=model, status="success")

    try:
        response = await router.atext_completion(**request_data)
        elapsed_ms = int((time.time() - start) * 1000)
        usage = getattr(response, "usage", None)
        log_entry.model_used = getattr(response, "model", model)
        log_entry.input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        log_entry.output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        log_entry.latency_ms = elapsed_ms
        log_entry.cost = litellm.completion_cost(completion_response=response) or 0.0
        db.add(log_entry)
        await db.flush()
        return response.model_dump()
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        log_entry.status = "error"
        log_entry.error_message = str(e)[:1000]
        log_entry.latency_ms = elapsed_ms
        db.add(log_entry)
        await db.flush()
        raise


async def embedding(request_data: dict, org_id: uuid.UUID, key_id: uuid.UUID, db: AsyncSession) -> dict:
    """Embedding via LiteLLM."""
    router = await get_router()
    model = request_data.get("model", "")
    start = time.time()

    log_entry = GatewayRequest(org_id=org_id, key_id=key_id, model_requested=model, status="success")

    try:
        response = await router.aembedding(**request_data)
        elapsed_ms = int((time.time() - start) * 1000)
        usage = getattr(response, "usage", None)
        log_entry.model_used = model
        log_entry.input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        log_entry.latency_ms = elapsed_ms
        log_entry.cost = litellm.completion_cost(completion_response=response) or 0.0
        db.add(log_entry)
        await db.flush()
        return response.model_dump()
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        log_entry.status = "error"
        log_entry.error_message = str(e)[:1000]
        log_entry.latency_ms = elapsed_ms
        db.add(log_entry)
        await db.flush()
        raise


# ─── API Key management ───

def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key. Returns (raw_key, key_hash, key_prefix)."""
    raw = "bn-" + secrets.token_hex(32)
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    key_prefix = raw[:12] + "..."
    return raw, key_hash, key_prefix


def hash_api_key(raw_key: str) -> str:
    """Hash an API key for lookup."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def validate_api_key(db: AsyncSession, raw_key: str) -> Optional[GatewayKey]:
    """Validate an API key and return the key record if valid."""
    key_hash = hash_api_key(raw_key)
    result = await db.execute(
        select(GatewayKey).where(
            and_(GatewayKey.key_hash == key_hash, GatewayKey.revoked_at.is_(None))
        )
    )
    return result.scalar_one_or_none()


# ─── Rate limiting (Redis-backed) ───

async def check_rate_limit(key_id: uuid.UUID, rate_limit: int) -> bool:
    """Check and increment rate limit. Returns True if allowed."""
    now = int(time.time())
    window = now - (now % 60)  # 1-minute window
    redis_key = f"gateway:ratelimit:{key_id}:{window}"

    count = await redis_client.incr(redis_key)
    if count == 1:
        await redis_client.expire(redis_key, 120)  # expire after 2 minutes

    return count <= rate_limit


# ─── Usage queries ───

async def get_usage_stats(
    db: AsyncSession,
    org_id: uuid.UUID,
    days: int = 30,
    team_id: Optional[str] = None,
) -> dict:
    """Get usage statistics for the org."""
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    base_filter = and_(
        GatewayRequest.org_id == org_id,
        GatewayRequest.created_at >= cutoff,
    )
    if team_id:
        base_filter = and_(base_filter, GatewayRequest.team_id == team_id)

    # Totals
    totals = await db.execute(
        select(
            func.count(GatewayRequest.id).label("total_requests"),
            func.coalesce(func.sum(GatewayRequest.input_tokens), 0).label("total_input_tokens"),
            func.coalesce(func.sum(GatewayRequest.output_tokens), 0).label("total_output_tokens"),
            func.coalesce(func.sum(GatewayRequest.cost), 0).label("total_cost"),
        ).where(base_filter)
    )
    row = totals.one()

    # By model
    by_model_q = await db.execute(
        select(
            GatewayRequest.model_requested,
            func.count(GatewayRequest.id).label("requests"),
            func.coalesce(func.sum(GatewayRequest.cost), 0).label("cost"),
            func.coalesce(func.sum(GatewayRequest.input_tokens + GatewayRequest.output_tokens), 0).label("tokens"),
        ).where(base_filter).group_by(GatewayRequest.model_requested)
    )
    by_model = [{"model": r[0], "requests": r[1], "cost": float(r[2]), "tokens": int(r[3])} for r in by_model_q.all()]

    # By day
    by_day_q = await db.execute(
        select(
            cast(GatewayRequest.created_at, Date).label("day"),
            func.count(GatewayRequest.id).label("requests"),
            func.coalesce(func.sum(GatewayRequest.cost), 0).label("cost"),
        ).where(base_filter).group_by("day").order_by("day")
    )
    by_day = [{"date": str(r[0]), "requests": r[1], "cost": float(r[2])} for r in by_day_q.all()]

    return {
        "total_requests": row[0],
        "total_input_tokens": int(row[1]),
        "total_output_tokens": int(row[2]),
        "total_cost": float(row[3]),
        "by_model": by_model,
        "by_day": by_day,
    }


async def get_request_logs(
    db: AsyncSession,
    org_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
    model: Optional[str] = None,
    status: Optional[str] = None,
) -> list[GatewayRequest]:
    """Get recent gateway request logs."""
    q = select(GatewayRequest).where(GatewayRequest.org_id == org_id)
    if model:
        q = q.where(GatewayRequest.model_requested == model)
    if status:
        q = q.where(GatewayRequest.status == status)
    q = q.order_by(GatewayRequest.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return list(result.scalars().all())
