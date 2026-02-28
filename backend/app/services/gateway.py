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
from sqlalchemy import select, func, and_, cast, Date, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.vault import vault_client
from app.core.redis import redis_client
from app.core.database import get_db_session
from app.models.cloud_provider import CloudProvider
from app.models.gateway import GatewayRequest, GatewayKey, GatewayRateLimit
from app.models.policy import Policy
from app.models.routing_policy import RoutingPolicy
from app.models.model import Model
from app.models.deployment import Deployment
from app.schemas.gateway import RoutingStrategy
from app.services.log_emitters import emit_gateway_event
from app.services.managed_inference import calculate_marked_up_cost

logger = logging.getLogger(__name__)

# Suppress litellm's verbose logging
litellm.suppress_debug_info = True
litellm.drop_params = True  # silently drop unsupported params per provider


# ─── Provider credential mapping ───

import httpx

# ─── Azure AD token cache ───
_azure_ad_cache: dict[str, tuple[str, float]] = {}  # key → (token, expires_at)


async def _get_azure_ad_token(
    tenant_id: str, client_id: str, client_secret: str
) -> str:
    """Get an Azure AD token for Cognitive Services via client credentials flow.

    Tokens are cached and refreshed 60 s before expiry.
    """
    cache_key = f"{tenant_id}:{client_id}"
    cached = _azure_ad_cache.get(cache_key)
    if cached and time.time() < cached[1] - 60:
        return cached[0]

    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "https://cognitiveservices.azure.com/.default",
            },
            timeout=10.0,
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Azure AD token request failed ({resp.status_code}): {resp.text}"
            )
        data = resp.json()
        token = data["access_token"]
        expires_at = time.time() + data.get("expires_in", 3600)
        _azure_ad_cache[cache_key] = (token, expires_at)
        return token


# ─── Model alias resolution ───

import re


def _generate_model_aliases(model_id: str) -> list[str]:
    """Generate common aliases for a model ID.

    Users often request shorthand model names (e.g. ``gemini-2.0-flash``)
    while the DB stores the versioned canonical name
    (``gemini-2.0-flash-001``).  This function produces the shorthand
    variants so both resolve to the same deployment.

    Patterns handled:
    - GCP version suffixes: ``gemini-2.0-flash-001`` -> ``gemini-2.0-flash``
    - OpenAI/Azure date suffixes: ``gpt-4o-mini-2024-07-18`` -> ``gpt-4o-mini``
    - GCP preview suffixes: ``gemini-2.5-flash-preview-04-17`` -> ``gemini-2.5-flash``
    - AWS version tags: ``amazon.nova-lite-v1:0`` is already stable (no aliases needed)
    """
    aliases: set[str] = set()

    # Strip GCP version suffix (-001, -002, etc.)
    stripped = re.sub(r"-\d{3}$", "", model_id)
    if stripped != model_id:
        aliases.add(stripped)

    # Strip OpenAI/Azure date suffix (-2024-07-18, etc.)
    stripped = re.sub(r"-\d{4}-\d{2}-\d{2}$", "", model_id)
    if stripped != model_id:
        aliases.add(stripped)

    # Strip GCP preview+date suffix (-preview-04-17, etc.)
    stripped = re.sub(r"-preview-\d{2}-\d{2}$", "", model_id)
    if stripped != model_id:
        aliases.add(stripped)

    # Strip preview tag entirely (gemini-2.5-flash-preview-04-17 -> gemini-2.5-flash)
    stripped = re.sub(r"-preview.*$", "", model_id)
    if stripped != model_id:
        aliases.add(stripped)

    # Don't include the canonical name itself
    aliases.discard(model_id)

    return list(aliases)


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
            
            # Pre-fetch active Azure deployments for this org so we can
            # map catalog models → real deployment names that Azure needs.
            azure_deployments_by_model: dict[uuid.UUID, Deployment] = {}
            try:
                dep_result = await db.execute(
                    select(Deployment).where(
                        and_(
                            Deployment.org_id == org_id,
                            Deployment.status.in_(["active", "deploying"]),
                        )
                    )
                )
                for dep in dep_result.scalars().all():
                    if (dep.config or {}).get("provider_type") == "azure":
                        azure_deployments_by_model[dep.model_id] = dep
            except Exception as e:
                logger.warning(f"Failed to fetch Azure deployments: {e}")
            
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
                    # Azure requires explicit deployments. Only include
                    # models that have an active Deployment record whose
                    # config contains the real Azure deployment name.
                    deployment = azure_deployments_by_model.get(model.id)
                    if not deployment:
                        continue  # no deployment → skip this model
                    deployment_name = (deployment.config or {}).get("name")
                    if not deployment_name:
                        continue
                    
                    base_url = c.get("endpoint", "")
                    if not base_url:
                        continue
                    
                    # Read azure_mode from credentials (default to "openai" for backward compat)
                    azure_mode = c.get("azure_mode", "openai")
                    
                    if azure_mode == "foundry":
                        # Foundry mode: use azure_ai/ prefix with api_key
                        api_key = c.get("api_key", "")
                        if not api_key:
                            continue  # Foundry requires API key
                        litellm_params = {
                            "model": f"azure_ai/{deployment_name}",
                            "api_base": base_url,
                            "api_key": api_key,
                        }
                    else:  # azure_mode == "openai" 
                        # OpenAI mode: original logic with azure/ prefix
                        # Prefer direct API key if available; otherwise use
                        # Azure AD token from service principal credentials.
                        api_key = c.get("api_key", "")
                        azure_ad_token = None
                        if not api_key:
                            tenant = c.get("tenant_id", "")
                            client_id = c.get("client_id", "")
                            client_secret = c.get("client_secret", "")
                            if tenant and client_id and client_secret:
                                try:
                                    azure_ad_token = await _get_azure_ad_token(
                                        tenant, client_id, client_secret
                                    )
                                except Exception as e:
                                    logger.warning(f"Azure AD token fetch failed: {e}")
                                    continue
                            else:
                                continue
                        litellm_params = {
                            "model": f"azure/{deployment_name}",
                            "api_base": base_url,
                            "api_version": "2024-12-01-preview",
                        }
                        if azure_ad_token:
                            litellm_params["azure_ad_token"] = azure_ad_token
                        else:
                            litellm_params["api_key"] = api_key
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
                elif provider_type == "groq":
                    litellm_params = {
                        "model": f"groq/{model_id}",
                        "api_key": c.get("api_key", ""),
                    }
                else:
                    continue
                
                model_list.append({
                    "model_name": model_id,
                    "litellm_params": litellm_params,
                })
            
            if model_list:
                # Register aliases so shorthand names resolve to the same
                # deployment (e.g. "gemini-2.0-flash" -> "gemini-2.0-flash-001").
                canonical_names = {m["model_name"] for m in model_list}
                alias_entries: list[dict] = []
                for entry in model_list:
                    for alias in _generate_model_aliases(entry["model_name"]):
                        if alias not in canonical_names:
                            alias_entries.append({
                                "model_name": alias,
                                "litellm_params": entry["litellm_params"].copy(),
                            })
                            canonical_names.add(alias)  # prevent duplicate aliases
                model_list.extend(alias_entries)

                if alias_entries:
                    logger.info(
                        f"Registered {len(alias_entries)} model aliases "
                        f"(e.g. {alias_entries[0]['model_name']})"
                    )
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

    # Azure fallback: skipped — Azure requires explicit deployments tracked
    # in the Deployment table (queried in the dynamic path above). Without
    # DB access the fallback cannot resolve deployment names, so Azure
    # models are only available via the dynamic model list.

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


# ─── Per-org router cache (with TTL for token refresh) ───

_routers: dict[uuid.UUID, tuple[litellm.Router, float]] = {}  # org → (router, created_at)
_ROUTER_TTL = 3000  # 50 minutes — refresh before Azure AD tokens expire (1 hr)


async def get_router(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> litellm.Router:
    """Get or create a LiteLLM router for *org_id*."""
    cached = _routers.get(org_id)
    if cached and time.time() - cached[1] < _ROUTER_TTL:
        return cached[0]

    creds = await _get_provider_credentials(db, org_id)
    model_list = await _build_model_list(creds, db=db, org_id=org_id)

    now = time.time()

    if not model_list:
        # Return a router with empty model list — calls will fail gracefully
        router = litellm.Router(model_list=[], routing_strategy="simple-shuffle")
        _routers[org_id] = (router, now)
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
    _routers[org_id] = (router, now)
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
    """Return list of available models from the org's configured providers.

    Includes both canonical model IDs and their shorthand aliases so
    users can see all valid names they can pass in API requests.
    """
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
            elif lp.startswith("azure/") or lp.startswith("azure_ai/"):
                provider = "azure"
            elif lp.startswith("vertex_ai/"):
                provider = "gcp"
            elif lp.startswith("openai/"):
                provider = "openai"
            elif lp.startswith("anthropic/"):
                provider = "anthropic"
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

    max_daily = float(max_daily_spend)
    
    # Notify at 80% threshold
    if today_cost >= max_daily * 0.8 and today_cost < max_daily:
        try:
            from app.services.notifications import notification_service
            await notification_service.notify_org_admins(
                db,
                org_id,
                type="cost_alert",
                title=f"⚠️ Spend alert: ${today_cost:.2f} of ${max_daily:.2f} daily cap ({today_cost/max_daily*100:.0f}%)",
                body=f"Your organization has used {today_cost/max_daily*100:.0f}% of the daily spend cap. Requests will be blocked at ${max_daily:.2f}.",
            )
        except Exception as e:
            logger.warning(f"Failed to send spend alert notification: {e}")
    
    if today_cost >= max_daily:
        try:
            from app.services.notifications import notification_service
            await notification_service.notify_org_admins(
                db,
                org_id,
                type="cost_alert",
                title=f"🚫 Daily spend cap exceeded: ${today_cost:.2f} / ${max_daily:.2f}",
                body=f"All gateway requests are now blocked. Increase the spend cap in Governance → Policies or wait until tomorrow.",
            )
        except Exception as e:
            logger.warning(f"Failed to send spend cap notification: {e}")
        
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

    # 4. Monthly gateway call quota
    await check_monthly_quota(db, key.org_id)


async def check_monthly_quota(db: AsyncSession, org_id: uuid.UUID) -> None:
    """Check if org has exceeded monthly gateway call quota for their tier.

    Emits a notification at 80% usage and blocks at 100%.
    """
    from app.services.feature_gate import feature_gate

    try:
        usage_info = await feature_gate.check_usage_limit(
            db, str(org_id), "gateway_calls_per_month"
        )

        # Unlimited plans skip the check
        if usage_info["limit"] == float("inf"):
            return

        limit = int(usage_info["limit"])
        current = usage_info["current"]

        # At limit - block the request
        if usage_info["at_limit"]:
            raise PolicyViolation(
                f"Monthly gateway call limit reached ({limit:,} calls). "
                f"Upgrade your plan at getbonito.com/pricing for higher limits."
            )

        # At 80% - emit a warning notification (once per month)
        if current >= int(limit * 0.8):
            warning_key = f"quota_warning:{org_id}:{usage_info.get('month', 'current')}"
            try:
                from app.core.redis import get_redis
                redis = await get_redis()
                already_warned = await redis.get(warning_key)
                if not already_warned:
                    await redis.setex(warning_key, 86400 * 31, "1")
                    logger.warning(
                        f"Org {org_id} at {current}/{limit} gateway calls "
                        f"({int(current/limit*100)}%% of monthly quota)"
                    )
            except Exception:
                pass  # Redis unavailable, skip warning dedup

    except PolicyViolation:
        raise
    except Exception as e:
        # Don't block requests if the quota check itself fails
        logger.warning(f"Quota check failed for org {org_id}: {e}")


# ─── Managed inference tracking ───

async def _track_managed_inference(
    db: AsyncSession,
    log_entry: GatewayRequest,
    org_id: uuid.UUID,
) -> None:
    """Check if the request used a managed provider and apply markup.

    Looks up the CloudProvider for the org+provider, checks is_managed,
    and if true: sets is_managed on the log entry, calculates marked-up
    cost, and increments the provider's managed usage counters.
    """
    if not log_entry.provider or not log_entry.cost:
        return

    try:
        result = await db.execute(
            select(CloudProvider).where(
                and_(
                    CloudProvider.org_id == org_id,
                    CloudProvider.provider_type == log_entry.provider,
                    CloudProvider.status == "active",
                    CloudProvider.is_managed.is_(True),
                )
            ).limit(1)
        )
        managed_provider = result.scalar_one_or_none()

        if managed_provider:
            base_cost = log_entry.cost or 0.0
            marked_up = calculate_marked_up_cost(base_cost)
            log_entry.is_managed = True
            log_entry.marked_up_cost = marked_up

            # Increment provider-level managed usage counters
            total_tokens = (log_entry.input_tokens or 0) + (log_entry.output_tokens or 0)
            managed_provider.managed_usage_tokens = (
                (managed_provider.managed_usage_tokens or 0) + total_tokens
            )
            managed_provider.managed_usage_cost = (
                float(managed_provider.managed_usage_cost or 0) + marked_up
            )
    except Exception as e:
        logger.warning(f"Failed to track managed inference for org {org_id}: {e}")


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
    
    # RAG Enhancement: Check for knowledge base in request
    kb_context = None
    kb_name = None
    retrieval_cost = 0.0
    retrieval_time_ms = 0
    
    # Check for knowledge base in bonito extension field
    bonito_params = request_data.get("bonito", {})
    if isinstance(bonito_params, dict):
        kb_name = bonito_params.get("knowledge_base")
    
    if kb_name:
        try:
            retrieval_start = time.time()
            kb_context = await _perform_rag_retrieval(kb_name, request_data.get("messages", []), org_id, db)
            retrieval_time_ms = int((time.time() - retrieval_start) * 1000)
            
            if kb_context:
                # Inject context into the request
                request_data = _inject_rag_context(request_data, kb_context)
                logger.info(f"Injected RAG context from KB '{kb_name}' with {len(kb_context['chunks'])} chunks")
            
        except Exception as e:
            logger.error(f"RAG retrieval failed for KB '{kb_name}': {e}")
            # Continue without RAG rather than failing the request

    # Strip Bonito extension fields before forwarding to upstream provider
    # (LiteLLM/Azure/etc. will reject unknown fields)
    request_data.pop("bonito", None)

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
        try:
            log_entry.cost = litellm.completion_cost(completion_response=response) or 0.0
        except Exception:
            # Some providers (e.g. Groq) return model names without provider prefix,
            # causing litellm cost lookup to fail. Fall back to 0.
            log_entry.cost = 0.0

        # Determine provider from DB lookup, fallback to heuristic
        model_used = log_entry.model_used or ""
        try:
            result = await db.execute(
                select(CloudProvider.provider_type)
                .join(Model, Model.provider_id == CloudProvider.id)
                .where(and_(CloudProvider.org_id == org_id, Model.model_id == model_used))
                .limit(1)
            )
            log_entry.provider = result.scalar_one_or_none()
        except Exception:
            log_entry.provider = None
        if not log_entry.provider:
            if any(k in model_used for k in ("bedrock", "amazon", "nova", "titan")):
                log_entry.provider = "aws"
            elif any(k in model_used for k in ("azure",)):
                log_entry.provider = "azure"
            elif any(k in model_used for k in ("vertex", "gemini", "palm")):
                log_entry.provider = "gcp"
            elif any(k in model_used for k in ("gpt-", "o1-", "o3-", "o4-", "dall-e", "chatgpt")):
                log_entry.provider = "openai"
            elif any(k in model_used for k in ("claude",)):
                log_entry.provider = "anthropic"
            elif any(k in model_used for k in ("llama", "mixtral", "gemma")):
                log_entry.provider = "groq"

        db.add(log_entry)
        await db.flush()

        # Track managed inference (markup + provider counters)
        await _track_managed_inference(db, log_entry, org_id)

        # Add RAG metadata to response
        response_dict = response.model_dump()
        if kb_context:
            response_dict["bonito"] = {
                "knowledge_base": kb_name,
                "sources": kb_context["sources"],
                "retrieval_cost": retrieval_cost,
                "retrieval_latency_ms": retrieval_time_ms
            }

        # Emit to platform logging system (fire-and-forget)
        try:
            await emit_gateway_event(
                org_id, "request",
                resource_type="model",
                message=f"Chat completion: {model}",
                duration_ms=elapsed_ms,
                cost=log_entry.cost,
                metadata={
                    "model": model,
                    "model_used": log_entry.model_used,
                    "input_tokens": log_entry.input_tokens,
                    "output_tokens": log_entry.output_tokens,
                    "provider": log_entry.provider,
                    "kb_name": kb_name,
                },
            )
        except Exception:
            pass

        return response_dict

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

        # Emit error to platform logging system
        try:
            await emit_gateway_event(
                org_id, "error",
                severity="error",
                message=f"Chat completion error: {model} — {str(e)[:200]}",
                duration_ms=elapsed_ms,
                metadata={"model": model, "error": str(e)[:500]},
            )
        except Exception:
            pass

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
    if not api_key.startswith('rt-'):
        return None
    
    # Use the full key as the prefix (rt-xxxxxxxxxxxxxxxx)
    result = await db.execute(
        select(RoutingPolicy).where(
            and_(
                RoutingPolicy.api_key_prefix == api_key,
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
        select(Model)
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


# ─── RAG (Retrieval-Augmented Generation) Functions ───

async def _perform_rag_retrieval(kb_name: str, messages: list, org_id: uuid.UUID, db: AsyncSession) -> Optional[dict]:
    """
    Perform RAG retrieval for a knowledge base.
    
    Uses its own DB session to avoid poisoning the gateway's transaction
    if a pgvector query fails (e.g., dimension mismatch).
    
    Returns context dictionary with chunks and source information, or None if no results.
    """
    from app.models.knowledge_base import KnowledgeBase, KBChunk, KBDocument
    from app.services.kb_ingestion import EmbeddingGenerator
    
    # Use a separate session so RAG errors don't poison the gateway transaction
    async with get_db_session() as rag_db:
        return await _perform_rag_retrieval_inner(kb_name, messages, org_id, rag_db)


async def _perform_rag_retrieval_inner(kb_name: str, messages: list, org_id: uuid.UUID, db: AsyncSession) -> Optional[dict]:
    """Inner RAG retrieval with its own DB session."""
    from app.models.knowledge_base import KnowledgeBase, KBChunk, KBDocument
    from app.services.kb_ingestion import EmbeddingGenerator
    
    # Find knowledge base by name
    kb_result = await db.execute(
        select(KnowledgeBase).where(
            and_(KnowledgeBase.org_id == org_id, KnowledgeBase.name == kb_name)
        )
    )
    kb = kb_result.scalar_one_or_none()
    if not kb:
        logger.warning(f"Knowledge base '{kb_name}' not found for org {org_id}")
        return None
    
    if kb.status != "ready":
        logger.warning(f"Knowledge base '{kb_name}' is not ready (status: {kb.status})")
        return None
    
    # Extract user query from messages
    user_query = _extract_user_query(messages)
    if not user_query:
        logger.warning("No user query found in messages")
        return None
    
    # Generate embedding for the query using the SAME model as ingestion
    embedding_gen = EmbeddingGenerator(org_id)
    kb_embed_model = getattr(kb, 'embedding_model', None)
    embed_model = kb_embed_model if (kb_embed_model and kb_embed_model != 'auto') else None
    try:
        embed_dims = getattr(kb, 'embedding_dimensions', None)
        query_embeddings = await embedding_gen.generate_embeddings([user_query], model=embed_model, dimensions=embed_dims)
        if not query_embeddings:
            logger.error("Failed to generate query embedding")
            return None
        
        query_embedding = query_embeddings[0]
    except Exception as e:
        logger.error(f"Failed to generate query embedding: {e}")
        return None
    
    # Vector similarity search using pgvector cosine distance
    top_k = 5
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    
    try:
        search_result = await db.execute(
            sa_text("""
                SELECT c.id, c.content, c.token_count, c.chunk_index,
                       c.source_file, c.source_page, c.source_section,
                       1 - (c.embedding <=> CAST(:query_vec AS vector)) AS relevance_score
                FROM kb_chunks c
                WHERE c.knowledge_base_id = :kb_id
                  AND c.org_id = :org_id
                  AND c.embedding IS NOT NULL
                ORDER BY c.embedding <=> CAST(:query_vec AS vector)
                LIMIT :top_k
            """),
            {
                "query_vec": embedding_str,
                "kb_id": str(kb.id),
                "org_id": str(org_id),
                "top_k": top_k,
            },
        )
        rows = search_result.fetchall()
    except Exception as e:
        logger.error(f"pgvector search failed: {e}")
        return None
    
    if not rows:
        logger.info(f"No matching chunks found in KB '{kb_name}' for query")
        return None
    
    chunks = []
    sources = []
    for row in rows:
        chunk = {
            "content": row.content,
            "source_file": row.source_file,
            "source_page": row.source_page,
            "source_section": row.source_section,
            "relevance_score": round(float(row.relevance_score), 4) if row.relevance_score else 0,
        }
        chunks.append(chunk)
        sources.append({
            "document": row.source_file or "unknown",
            "page": row.source_page,
            "section": row.source_section,
            "relevance_score": chunk["relevance_score"],
            "chunk_preview": row.content[:150] + "…" if len(row.content) > 150 else row.content,
        })
    
    logger.info(f"RAG retrieval: {len(chunks)} chunks for query '{user_query[:80]}…' in KB {kb.id}")
    
    return {
        "chunks": chunks,
        "sources": sources,
        "query": user_query,
        "knowledge_base_id": str(kb.id),
    }


def _extract_user_query(messages: list) -> str:
    """Extract the most recent user message as the search query."""
    for message in reversed(messages):
        if isinstance(message, dict) and message.get("role") == "user":
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
    return ""


def _inject_rag_context(request_data: dict, kb_context: dict) -> dict:
    """
    Inject RAG context into the chat completion request.
    
    Adds retrieved chunks as system context before the user messages.
    """
    messages = request_data.get("messages", [])
    if not messages or not kb_context.get("chunks"):
        return request_data
    
    # Build context from chunks
    context_parts = ["Use the following context to answer the user's question. Cite sources when possible. If the context doesn't contain the answer, say so."]
    context_parts.append("")  # Empty line
    context_parts.append("Context:")
    
    for i, chunk in enumerate(kb_context["chunks"], 1):
        source_info = ""
        if chunk.get("source_file"):
            source_info = f" (source: {chunk['source_file']}"
            if chunk.get("source_page"):
                source_info += f", p.{chunk['source_page']}"
            source_info += ")"
        
        context_parts.append(f"[{i}] {chunk['content']}{source_info}")
    
    context_parts.append("")  # Empty line before user query
    
    context_message = {
        "role": "system",
        "content": "\n".join(context_parts)
    }
    
    # Create new request with injected context
    new_request = request_data.copy()
    new_request["messages"] = [context_message] + messages
    
    return new_request


async def detect_knowledge_base_from_policy(policy_id: uuid.UUID, db: AsyncSession) -> Optional[str]:
    """
    Check if a routing policy has an attached knowledge base.
    
    TODO: Implement when routing policy KB attachment is added.
    """
    # Placeholder - will be implemented when routing policy page is updated
    return None
