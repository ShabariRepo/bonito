"""
LiteLLM Gateway Service — wraps LiteLLM for multi-provider AI routing.

Reads provider credentials from Vault (per-provider UUID), configures
LiteLLM model list, and provides completion/embedding calls with
automatic failover.
"""

import json
import time
import uuid
import hashlib
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import litellm
from sqlalchemy import select, func, and_, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.vault import vault_client
from app.core.redis import redis_client
from app.core.database import get_db_session
from app.models.cloud_provider import CloudProvider
from app.models.gateway import GatewayRequest, GatewayKey, GatewayRateLimit
from app.models.policy import Policy
from app.models.routing_policy import RoutingPolicy
from app.models.model import Model
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
    "openai": "openai/",
    "anthropic": "anthropic/",
}


async def _get_provider_credentials(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> dict[str, dict]:
    """Fetch provider credentials from Vault using org-specific provider UUIDs.

    Credentials are stored at ``providers/{provider_uuid}`` — not at a
    generic ``providers/aws`` path.  We query the org's active
    CloudProvider rows, then fetch each one's secrets from Vault.
    """
    result = await db.execute(
        select(CloudProvider).where(
            and_(
                CloudProvider.org_id == org_id,
                CloudProvider.status == "active",
            )
        )
    )
    providers = result.scalars().all()

    creds: dict[str, dict] = {}
    for provider in providers:
        try:
            data = await vault_client.get_secrets(f"providers/{provider.id}")
            if data:
                creds[provider.provider_type] = data
        except Exception as e:
            logger.warning(
                "Failed to fetch %s credentials for provider %s: %s",
                provider.provider_type,
                provider.id,
                e,
            )
    return creds


async def _build_model_list(creds: dict, db: AsyncSession = None, org_id: uuid.UUID = None) -> list[dict]:
    """Build LiteLLM model_list dynamically from DB-synced models + provider credentials.
    
    If db/org_id are provided, reads the actual model catalog from the DB
    (synced from cloud providers). Falls back to a minimal hardcoded list
    if DB is unavailable.
    """
    model_list = []

    # Try dynamic model list from DB first
    if db and org_id:
        try:
            result = await db.execute(
                select(Model, CloudProvider)
                .join(CloudProvider, Model.provider_id == CloudProvider.id)
                .where(
                    and_(
                        CloudProvider.org_id == org_id,
                        CloudProvider.status == "active",
                    )
                )
            )
            rows = result.all()
            
            for model, provider in rows:
                provider_type = provider.provider_type
                if provider_type not in creds:
                    continue
                
                c = creds[provider_type]
                model_id = model.model_id
                litellm_params: dict = {}
                
                if provider_type == "aws":
                    litellm_params = {
                        "model": f"bedrock/{model_id}",
                        "aws_access_key_id": c.get("access_key_id", ""),
                        "aws_secret_access_key": c.get("secret_access_key", ""),
                        "aws_region_name": c.get("region", "us-east-1"),
                    }
                elif provider_type == "azure":
                    api_key = c.get("api_key") or c.get("client_secret", "")
                    base_url = c.get("endpoint", "")
                    if not (base_url and api_key):
                        continue
                    litellm_params = {
                        "model": f"azure/{model_id}",
                        "api_base": base_url,
                        "api_key": api_key,
                        "api_version": "2024-02-01",
                    }
                elif provider_type == "gcp":
                    sa_json = c.get("service_account_json")
                    vertex_credentials = None
                    if sa_json:
                        vertex_credentials = json.dumps(sa_json) if isinstance(sa_json, dict) else sa_json
                    litellm_params = {
                        "model": f"vertex_ai/{model_id}",
                        "vertex_project": c.get("project_id", ""),
                        "vertex_location": c.get("region", "us-central1"),
                    }
                    if vertex_credentials:
                        litellm_params["vertex_credentials"] = vertex_credentials
                elif provider_type == "openai":
                    litellm_params = {
                        "model": f"openai/{model_id}",
                        "api_key": c.get("api_key", ""),
                    }
                    org = c.get("organization_id")
                    if org:
                        litellm_params["organization"] = org
                elif provider_type == "anthropic":
                    litellm_params = {
                        "model": f"anthropic/{model_id}",
                        "api_key": c.get("api_key", ""),
                    }
                else:
                    continue
                
                model_list.append({
                    "model_name": model_id,
                    "litellm_params": litellm_params,
                })
            
            if model_list:
                logger.info(f"Built dynamic model list: {len(model_list)} models for org {org_id}")
                return model_list
        except Exception as e:
            logger.warning(f"Failed to build dynamic model list from DB: {e}, falling back to hardcoded")

    # Fallback: hardcoded model list (for when DB is unavailable)
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
            "meta.llama3-70b-instruct-v1:0",
        ]:
            model_list.append({
                "model_name": model,
                "litellm_params": {"model": f"bedrock/{model}", **common},
            })

    if "azure" in creds:
        c = creds["azure"]
        base_url = c.get("endpoint", "")
        api_key = c.get("api_key") or c.get("client_secret", "")
        if base_url and api_key:
            for model in ["gpt-4o", "gpt-4o-mini"]:
                model_list.append({
                    "model_name": model,
                    "litellm_params": {
                        "model": f"azure/{model}",
                        "api_base": base_url,
                        "api_key": api_key,
                        "api_version": "2024-02-01",
                    },
                })

    if "gcp" in creds:
        c = creds["gcp"]
        sa_json = c.get("service_account_json")
        vertex_credentials = json.dumps(sa_json) if isinstance(sa_json, dict) else sa_json if sa_json else None
        for model in ["gemini-1.5-pro", "gemini-1.5-flash"]:
            params: dict = {
                "model": f"vertex_ai/{model}",
                "vertex_project": c.get("project_id", ""),
                "vertex_location": c.get("region", "us-central1"),
            }
            if vertex_credentials:
                params["vertex_credentials"] = vertex_credentials
            model_list.append({"model_name": model, "litellm_params": params})

    return model_list


# ─── Per-org router cache ───

_routers: dict[uuid.UUID, litellm.Router] = {}


async def get_router(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> litellm.Router:
    """Get or create a LiteLLM router for *org_id*."""
    if org_id in _routers:
        return _routers[org_id]

    creds = await _get_provider_credentials(db, org_id)
    model_list = await _build_model_list(creds, db=db, org_id=org_id)

    if not model_list:
        # Return a router with empty model list — calls will fail gracefully
        router = litellm.Router(model_list=[], routing_strategy="simple-shuffle")
        _routers[org_id] = router
        return router

    router = litellm.Router(
        model_list=model_list,
        routing_strategy="simple-shuffle",
        num_retries=2,
        retry_after=1,
        timeout=60,
        allowed_fails=2,
        cooldown_time=30,
    )
    _routers[org_id] = router
    return router


async def reset_router(org_id: uuid.UUID | None = None):
    """Force router re-initialization.

    If *org_id* is given only that org's router is cleared; otherwise
    all cached routers are dropped.
    """
    if org_id is not None:
        _routers.pop(org_id, None)
    else:
        _routers.clear()


async def get_available_models(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[dict]:
    """Return list of available models from the org's configured providers."""
    creds = await _get_provider_credentials(db, org_id)
    model_list = await _build_model_list(creds, db=db, org_id=org_id)
    seen: set[str] = set()
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


# ─── Policy enforcement ───


class PolicyViolation(Exception):
    """Raised when a gateway request violates an active policy."""

    def __init__(self, message: str, status_code: int = 403):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


async def check_model_allowed(key: GatewayKey, model: str) -> None:
    """Check if the requested model is in the key's allowed_models list.

    The allowed_models field is a JSON dict like:
        {"models": ["gpt-4o", "claude-3-5-sonnet"], "providers": ["aws", "azure"]}

    If allowed_models is null/empty, all models are allowed (unrestricted key).
    """
    if not key.allowed_models:
        return  # unrestricted key

    allowed = key.allowed_models.get("models") or []
    if allowed and model not in allowed:
        raise PolicyViolation(
            f"Model '{model}' is not allowed for this API key. "
            f"Allowed models: {', '.join(allowed)}",
            status_code=403,
        )


async def check_spend_cap(db: AsyncSession, org_id: uuid.UUID) -> None:
    """Check if the org has exceeded its daily spend cap.

    Reads the active 'spend_limits' policy from the DB and compares
    today's total cost from gateway_requests against max_daily_spend.
    """
    # Fetch active spend_limits policy for this org
    result = await db.execute(
        select(Policy).where(
            and_(
                Policy.org_id == org_id,
                Policy.type == "spend_limits",
                Policy.enabled.is_(True),
            )
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        return  # no spend cap configured

    rules = policy.rules_json or {}
    max_daily_spend = rules.get("max_daily_spend")
    if max_daily_spend is None:
        return  # no cap set in rules

    # Query today's total cost
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    today_cost_result = await db.execute(
        select(func.coalesce(func.sum(GatewayRequest.cost), 0)).where(
            and_(
                GatewayRequest.org_id == org_id,
                GatewayRequest.created_at >= today_start,
                GatewayRequest.status == "success",
            )
        )
    )
    today_cost = float(today_cost_result.scalar())

    if today_cost >= float(max_daily_spend):
        raise PolicyViolation(
            f"Daily spend cap of ${max_daily_spend:.2f} exceeded "
            f"(today's spend: ${today_cost:.2f}). "
            f"Contact your admin to increase the limit.",
            status_code=429,
        )


async def check_model_access_policy(db: AsyncSession, org_id: uuid.UUID, model: str) -> None:
    """Check org-level model_access policies from the DB.

    These are org-wide restrictions beyond per-key allowed_models.
    """
    result = await db.execute(
        select(Policy).where(
            and_(
                Policy.org_id == org_id,
                Policy.type == "model_access",
                Policy.enabled.is_(True),
            )
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        return  # no org-level model restriction

    rules = policy.rules_json or {}
    allowed_models = rules.get("allowed_models") or []
    if allowed_models and model not in allowed_models:
        raise PolicyViolation(
            f"Model '{model}' is not approved by organization policy "
            f"'{policy.name}'. Approved models: {', '.join(allowed_models)}",
            status_code=403,
        )


async def enforce_policies(
    db: AsyncSession,
    key: GatewayKey,
    model: str,
) -> None:
    """Run all policy checks before forwarding a gateway request.

    Raises PolicyViolation if any check fails.
    """
    # 1. Per-key model allow-list
    await check_model_allowed(key, model)

    # 2. Org-level model access policy (from DB)
    await check_model_access_policy(db, key.org_id, model)

    # 3. Daily spend cap
    await check_spend_cap(db, key.org_id)


# ─── Completions ───

async def chat_completion(
    request_data: dict,
    org_id: uuid.UUID,
    key_id: uuid.UUID,
    db: AsyncSession,
) -> dict:
    """Execute a chat completion via LiteLLM router and log the request."""
    router = await get_router(db, org_id)
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
        # Log in a separate session so the error entry persists even when
        # the caller's session rolls back due to the re-raised exception.
        try:
            async with get_db_session() as log_db:
                log_db.add(log_entry)
        except Exception as log_err:
            logger.error(f"Failed to log error request: {log_err}")
        raise


async def completion(request_data: dict, org_id: uuid.UUID, key_id: uuid.UUID, db: AsyncSession) -> dict:
    """Legacy text completion."""
    router = await get_router(db, org_id)
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
        try:
            async with get_db_session() as log_db:
                log_db.add(log_entry)
        except Exception as log_err:
            logger.error(f"Failed to log error request: {log_err}")
        raise


async def embedding(request_data: dict, org_id: uuid.UUID, key_id: uuid.UUID, db: AsyncSession) -> dict:
    """Embedding via LiteLLM."""
    router = await get_router(db, org_id)
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
        try:
            async with get_db_session() as log_db:
                log_db.add(log_entry)
        except Exception as log_err:
            logger.error(f"Failed to log error request: {log_err}")
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
    """Check and increment rate limit. Returns True if allowed.
    
    Gracefully allows all requests if Redis is unavailable (fail-open).
    """
    if redis_client is None:
        return True  # No Redis → skip rate limiting (fail-open)
    
    try:
        now = int(time.time())
        window = now - (now % 60)  # 1-minute window
        redis_key = f"gateway:ratelimit:{key_id}:{window}"

        count = await redis_client.incr(redis_key)
        if count == 1:
            await redis_client.expire(redis_key, 120)  # expire after 2 minutes

        return count <= rate_limit
    except Exception as e:
        logger.warning(f"Rate limit check failed (allowing request): {e}")
        return True  # Fail-open: allow request if Redis is down


# ─── Routing Policy Support ───

async def resolve_routing_policy_by_key(api_key: str, db: AsyncSession) -> Optional[RoutingPolicy]:
    """Resolve a routing policy by API key prefix."""
    # Extract potential routing policy prefix from API key (rt-xxxxxxxx)
    if not api_key.startswith('rt-'):
        return None
    
    # The API key format should be: rt-xxxxxxxx (16 chars total)
    api_key_prefix = api_key[:16] if len(api_key) >= 16 else api_key
    
    result = await db.execute(
        select(RoutingPolicy).where(
            and_(
                RoutingPolicy.api_key_prefix == api_key_prefix,
                RoutingPolicy.is_active == True
            )
        )
    )
    return result.scalar_one_or_none()


async def apply_routing_policy(
    policy: RoutingPolicy, 
    request_data: dict, 
    db: AsyncSession
) -> str:
    """Apply routing policy strategy to select the best model."""
    if not policy.models:
        raise ValueError("Routing policy has no models configured")
    
    # Get available models with their display names
    model_ids = [uuid.UUID(model["model_id"]) for model in policy.models]
    result = await db.execute(
        select(Model.id, Model.display_name, Model.model_id)
        .join(CloudProvider, Model.provider_id == CloudProvider.id)
        .where(
            and_(
                Model.id.in_(model_ids),
                CloudProvider.org_id == policy.org_id,
                CloudProvider.status == "active"
            )
        )
    )
    available_models = {str(model.id): model for model in result.scalars().all()}
    
    if not available_models:
        raise ValueError("No available models found for routing policy")
    
    # Apply strategy-specific logic
    selected_model_config = None
    
    if policy.strategy == "cost_optimized":
        # Select model with lowest cost (for demo, just select first)
        selected_model_config = policy.models[0]
    
    elif policy.strategy == "latency_optimized":
        # Select model with lowest latency (for demo, just select first)  
        selected_model_config = policy.models[0]
    
    elif policy.strategy == "balanced":
        # Balance between cost and latency (for demo, just select first)
        selected_model_config = policy.models[0]
    
    elif policy.strategy == "failover":
        # Try primary first, then fallbacks
        for model_config in policy.models:
            if model_config.get("role") == "primary" or not model_config.get("role"):
                model_id = model_config["model_id"]
                if model_id in available_models:
                    selected_model_config = model_config
                    break
        
        # If no primary available, try first fallback
        if not selected_model_config:
            for model_config in policy.models:
                if model_config.get("role") == "fallback":
                    model_id = model_config["model_id"]
                    if model_id in available_models:
                        selected_model_config = model_config
                        break
    
    elif policy.strategy == "ab_test":
        # Simple weight-based selection (for demo, select by weight)
        import random
        rand = random.random() * 100
        cumulative_weight = 0
        
        for model_config in policy.models:
            weight = model_config.get("weight", 0)
            cumulative_weight += weight
            if rand <= cumulative_weight:
                selected_model_config = model_config
                break
    
    # Default to first available model if strategy didn't select one
    if not selected_model_config:
        selected_model_config = policy.models[0]
    
    selected_model_id = selected_model_config["model_id"]
    if selected_model_id not in available_models:
        raise ValueError(f"Selected model {selected_model_id} is not available")
    
    selected_model = available_models[selected_model_id]
    
    # Return the provider-prefixed model name for LiteLLM
    provider_model_name = f"{selected_model.model_id}"  # This should include provider prefix
    
    logger.info(
        f"Routing policy {policy.name} selected model {selected_model.display_name} "
        f"using strategy {policy.strategy}"
    )
    
    return provider_model_name


# ─── Usage queries ───

async def get_usage_stats(
    db: AsyncSession,
    org_id: uuid.UUID,
    days: int = 30,
    team_id: Optional[str] = None,
) -> dict:
    """Get usage statistics for the org."""
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
