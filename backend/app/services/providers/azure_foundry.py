"""Azure AI Foundry provider — real Azure SDK integration."""

import json
import time
import logging
from datetime import date
from typing import List, Optional

import httpx
from app.core.redis import redis_client
from app.services.providers.base import (
    CloudProvider,
    CostData,
    CredentialInfo,
    DailyCost,
    HealthStatus,
    InvocationResult,
    ModelInfo,
)

logger = logging.getLogger(__name__)

MODELS_CACHE_TTL = 300  # 5 min

# Azure OpenAI model pricing (per 1M tokens)
AZURE_PRICING: dict[str, tuple[float, float, int]] = {
    # GPT-4o family
    "gpt-4o": (2.50, 10.00, 128_000),
    "gpt-4o-mini": (0.15, 0.60, 128_000),
    "gpt-4o-realtime": (5.00, 20.00, 128_000),
    # GPT-4
    "gpt-4-turbo": (10.00, 30.00, 128_000),
    "gpt-4": (30.00, 60.00, 8_192),
    "gpt-4-32k": (60.00, 120.00, 32_768),
    # GPT-3.5
    "gpt-35-turbo": (0.50, 1.50, 16_385),
    "gpt-35-turbo-16k": (3.00, 4.00, 16_385),
    # o-series reasoning
    "o1-preview": (15.00, 60.00, 128_000),
    "o1-mini": (3.00, 12.00, 128_000),
    "o3-mini": (1.10, 4.40, 200_000),
    # Embeddings
    "text-embedding-3-large": (0.13, 0.0, 8_191),
    "text-embedding-3-small": (0.02, 0.0, 8_191),
    "text-embedding-ada-002": (0.10, 0.0, 8_191),
    # DALL-E (per image, not tokens)
    "dall-e-3": (0.0, 0.0, 0),
    # Whisper
    "whisper": (0.0, 0.0, 0),
    # Phi
    "phi-3-medium-128k-instruct": (0.20, 0.40, 128_000),
    "phi-3-mini-128k-instruct": (0.10, 0.20, 128_000),
    "phi-3-small-128k-instruct": (0.15, 0.30, 128_000),
    # Mistral (via Azure)
    "mistral-large-latest": (4.00, 12.00, 128_000),
    "mistral-small-latest": (1.00, 3.00, 32_000),
    # Meta Llama (via Azure)
    "meta-llama-3.1-405b-instruct": (5.33, 16.00, 128_000),
    "meta-llama-3.1-70b-instruct": (2.68, 3.58, 128_000),
    "meta-llama-3.1-8b-instruct": (0.30, 0.61, 128_000),
    # Cohere
    "cohere-command-r-plus": (3.00, 15.00, 128_000),
    "cohere-command-r": (0.50, 1.50, 128_000),
}


def _get_azure_pricing(model_id: str) -> tuple[float, float]:
    for prefix in sorted(AZURE_PRICING.keys(), key=len, reverse=True):
        if model_id.lower().startswith(prefix.lower()):
            return AZURE_PRICING[prefix][0], AZURE_PRICING[prefix][1]
    return 0.0, 0.0


def _get_azure_context(model_id: str) -> int:
    for prefix in sorted(AZURE_PRICING.keys(), key=len, reverse=True):
        if model_id.lower().startswith(prefix.lower()):
            return AZURE_PRICING[prefix][2]
    return 0


def _estimate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    inp, out = _get_azure_pricing(model_id)
    return (input_tokens * inp / 1_000_000) + (output_tokens * out / 1_000_000)


class AzureFoundryProvider(CloudProvider):
    """Real Azure AI Foundry integration using REST APIs + Azure Identity."""

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        subscription_id: str,
        resource_group: str = "",
        endpoint: str = "",
    ):
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._subscription_id = subscription_id
        self._resource_group = resource_group
        self._endpoint = endpoint  # Azure OpenAI endpoint URL
        self._token: Optional[str] = None
        self._token_expires: float = 0

    async def _get_token(self, scope: str = "https://management.azure.com/.default") -> str:
        """Get OAuth2 token via client credentials flow."""
        if self._token and time.time() < self._token_expires - 60:
            return self._token

        url = f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "scope": scope,
            })
            if resp.status_code != 200:
                raise RuntimeError(f"Azure auth failed ({resp.status_code}): {resp.text}")
            data = resp.json()
            self._token = data["access_token"]
            self._token_expires = time.time() + data.get("expires_in", 3600)
            return self._token

    async def _get_cognitive_token(self) -> str:
        """Get token scoped for Azure Cognitive Services (OpenAI)."""
        return await self._get_token("https://cognitiveservices.azure.com/.default")

    # ── Credential validation ──────────────────────────────────────

    async def validate_credentials(self) -> CredentialInfo:
        try:
            token = await self._get_token()
            # Verify by listing subscriptions
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://management.azure.com/subscriptions/{self._subscription_id}?api-version=2022-12-01",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 200:
                    sub = resp.json()
                    return CredentialInfo(
                        valid=True,
                        account_id=self._subscription_id,
                        user_id=self._client_id,
                        message=f"Connected to subscription: {sub.get('displayName', self._subscription_id)}",
                    )
                elif resp.status_code == 401:
                    return CredentialInfo(valid=False, message="Authentication failed — check client credentials")
                elif resp.status_code == 403:
                    return CredentialInfo(valid=False, message="Access denied — service principal lacks Reader role on subscription")
                else:
                    return CredentialInfo(valid=False, message=f"Azure error ({resp.status_code}): {resp.text[:200]}")
        except httpx.ConnectError:
            return CredentialInfo(valid=False, message="Cannot reach Azure — check network connectivity")
        except Exception as e:
            return CredentialInfo(valid=False, message=f"Connection error: {str(e)}")

    # ── Model listing ──────────────────────────────────────────────

    async def list_models(self) -> List[ModelInfo]:
        cache_key = f"azure:models:{self._subscription_id}"
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                return [ModelInfo(**m) for m in json.loads(cached)]
        except Exception:
            pass

        models: List[ModelInfo] = []

        try:
            # List Azure OpenAI deployments if we have an endpoint
            if self._endpoint:
                cog_token = await self._get_cognitive_token()
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"{self._endpoint.rstrip('/')}/openai/deployments?api-version=2024-06-01",
                        headers={"Authorization": f"Bearer {cog_token}"},
                    )
                    if resp.status_code == 200:
                        for d in resp.json().get("data", []):
                            model_name = d.get("model", d.get("id", "unknown"))
                            inp, out = _get_azure_pricing(model_name)
                            ctx = _get_azure_context(model_name)
                            caps = ["text"]
                            if "gpt-4o" in model_name or "gpt-4-turbo" in model_name:
                                caps.extend(["vision", "function_calling"])
                            if "embedding" in model_name:
                                caps = ["embeddings"]
                            if "dall-e" in model_name:
                                caps = ["image_generation"]
                            if "whisper" in model_name:
                                caps = ["speech_to_text"]

                            models.append(ModelInfo(
                                model_id=d["id"],
                                model_name=d.get("model", d["id"]),
                                provider_name="Azure OpenAI",
                                input_modalities=["TEXT"] + (["IMAGE"] if "vision" in caps else []),
                                output_modalities=["TEXT"] + (["IMAGE"] if "image_generation" in caps else []),
                                streaming_supported=True,
                                context_window=ctx,
                                input_price_per_1m_tokens=inp,
                                output_price_per_1m_tokens=out,
                                status=d.get("status", "succeeded").upper(),
                                capabilities=caps,
                            ))

            # Also list available models from Azure AI Model Catalog (MaaS)
            token = await self._get_token()
            async with httpx.AsyncClient() as client:
                # List Azure OpenAI accounts in subscription to discover endpoints
                resp = await client.get(
                    f"https://management.azure.com/subscriptions/{self._subscription_id}"
                    f"/providers/Microsoft.CognitiveServices/accounts?api-version=2024-10-01",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 200:
                    for account in resp.json().get("value", []):
                        if account.get("kind") in ("OpenAI", "AIServices"):
                            endpoint = account.get("properties", {}).get("endpoint", "")
                            if endpoint and not self._endpoint:
                                # Discover deployments from this account too
                                cog_token = await self._get_cognitive_token()
                                dep_resp = await client.get(
                                    f"{endpoint.rstrip('/')}/openai/deployments?api-version=2024-06-01",
                                    headers={"Authorization": f"Bearer {cog_token}"},
                                )
                                if dep_resp.status_code == 200:
                                    existing_ids = {m.model_id for m in models}
                                    for d in dep_resp.json().get("data", []):
                                        if d["id"] not in existing_ids:
                                            model_name = d.get("model", d.get("id", "unknown"))
                                            inp, out = _get_azure_pricing(model_name)
                                            ctx = _get_azure_context(model_name)
                                            caps = ["text"]
                                            if "embedding" in model_name:
                                                caps = ["embeddings"]
                                            models.append(ModelInfo(
                                                model_id=d["id"],
                                                model_name=model_name,
                                                provider_name="Azure OpenAI",
                                                input_modalities=["TEXT"],
                                                output_modalities=["TEXT"],
                                                streaming_supported=True,
                                                context_window=ctx,
                                                input_price_per_1m_tokens=inp,
                                                output_price_per_1m_tokens=out,
                                                status="ACTIVE",
                                                capabilities=caps,
                                            ))

        except Exception as e:
            logger.error(f"Azure list_models error: {e}")
            if not models:
                raise RuntimeError(f"Failed to list Azure models: {str(e)}")

        # Cache
        try:
            serialized = json.dumps([{
                "model_id": m.model_id, "model_name": m.model_name,
                "provider_name": m.provider_name, "input_modalities": m.input_modalities,
                "output_modalities": m.output_modalities, "streaming_supported": m.streaming_supported,
                "context_window": m.context_window,
                "input_price_per_1m_tokens": m.input_price_per_1m_tokens,
                "output_price_per_1m_tokens": m.output_price_per_1m_tokens,
                "status": m.status, "capabilities": m.capabilities,
            } for m in models])
            await redis_client.setex(cache_key, MODELS_CACHE_TTL, serialized)
        except Exception:
            pass

        return models

    async def get_model(self, model_id: str) -> Optional[ModelInfo]:
        models = await self.list_models()
        return next((m for m in models if m.model_id == model_id), None)

    # ── Model invocation ───────────────────────────────────────────

    async def invoke_model(
        self, model_id: str, prompt: str, max_tokens: int = 1024, temperature: float = 0.7
    ) -> InvocationResult:
        if not self._endpoint:
            raise RuntimeError("No Azure OpenAI endpoint configured — set endpoint when connecting")

        token = await self._get_cognitive_token()
        body = {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self._endpoint.rstrip('/')}/openai/deployments/{model_id}/chat/completions?api-version=2024-06-01",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
                latency_ms = (time.monotonic() - start) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    text = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    inp_tok = usage.get("prompt_tokens", 0)
                    out_tok = usage.get("completion_tokens", 0)
                    return InvocationResult(
                        response_text=text,
                        input_tokens=inp_tok,
                        output_tokens=out_tok,
                        latency_ms=round(latency_ms, 1),
                        estimated_cost=_estimate_cost(model_id, inp_tok, out_tok),
                        model_id=model_id,
                    )
                elif resp.status_code == 404:
                    raise RuntimeError(f"Deployment '{model_id}' not found — check Azure OpenAI deployments")
                elif resp.status_code == 429:
                    raise RuntimeError("Rate limited — Azure OpenAI quota exceeded, try again shortly")
                elif resp.status_code == 401:
                    raise RuntimeError("Authentication failed — credentials may have expired")
                else:
                    raise RuntimeError(f"Azure OpenAI error ({resp.status_code}): {resp.text[:300]}")

        except httpx.TimeoutException:
            raise RuntimeError("Model invocation timed out — try a shorter prompt")
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Invocation failed: {str(e)}")

    # ── Cost data ──────────────────────────────────────────────────

    async def get_costs(self, start_date: date, end_date: date) -> CostData:
        try:
            token = await self._get_token()
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"https://management.azure.com/subscriptions/{self._subscription_id}"
                    f"/providers/Microsoft.CostManagement/query?api-version=2023-11-01",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "type": "ActualCost",
                        "timeframe": "Custom",
                        "timePeriod": {
                            "from": f"{start_date.isoformat()}T00:00:00+00:00",
                            "to": f"{end_date.isoformat()}T23:59:59+00:00",
                        },
                        "dataset": {
                            "granularity": "Daily",
                            "aggregation": {
                                "totalCost": {"name": "Cost", "function": "Sum"},
                            },
                            "filter": {
                                "dimensions": {
                                    "name": "ServiceName",
                                    "operator": "In",
                                    "values": ["Azure OpenAI Service", "Azure AI Services", "Cognitive Services"],
                                },
                            },
                            "grouping": [
                                {"type": "Dimension", "name": "ServiceName"},
                            ],
                        },
                    },
                )

                if resp.status_code != 200:
                    if resp.status_code == 401:
                        raise RuntimeError("Cost Management auth failed — check credentials")
                    raise RuntimeError(f"Cost Management error ({resp.status_code}): {resp.text[:200]}")

                data = resp.json()
                daily_costs = []
                total = 0.0
                columns = [c["name"] for c in data.get("properties", {}).get("columns", [])]
                cost_idx = columns.index("Cost") if "Cost" in columns else 0
                date_idx = columns.index("UsageDate") if "UsageDate" in columns else 1
                svc_idx = columns.index("ServiceName") if "ServiceName" in columns else 2

                for row in data.get("properties", {}).get("rows", []):
                    amount = float(row[cost_idx])
                    day = str(row[date_idx])[:10]  # YYYYMMDD or ISO
                    if len(day) == 8:
                        day = f"{day[:4]}-{day[4:6]}-{day[6:8]}"
                    service = str(row[svc_idx]) if len(row) > svc_idx else "Azure AI"
                    total += amount
                    daily_costs.append(DailyCost(
                        date=day, amount=round(amount, 6),
                        currency="USD", service=service,
                    ))

                return CostData(
                    total=round(total, 2), currency="USD",
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                    daily_costs=daily_costs,
                )

        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Azure cost query error: {e}")
            return CostData(
                total=0.0, start_date=start_date.isoformat(),
                end_date=end_date.isoformat(), daily_costs=[],
            )

    # ── Health check ───────────────────────────────────────────────

    async def health_check(self) -> HealthStatus:
        start = time.monotonic()
        try:
            token = await self._get_token()
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://management.azure.com/subscriptions/{self._subscription_id}?api-version=2022-12-01",
                    headers={"Authorization": f"Bearer {token}"},
                )
                latency = (time.monotonic() - start) * 1000
                if resp.status_code == 200:
                    sub = resp.json()
                    return HealthStatus(
                        healthy=True,
                        latency_ms=round(latency, 1),
                        account_id=self._subscription_id,
                        message=f"Connected: {sub.get('displayName', 'Azure')}",
                    )
                return HealthStatus(
                    healthy=False, latency_ms=round(latency, 1),
                    message=f"Azure returned {resp.status_code}",
                )
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return HealthStatus(
                healthy=False, latency_ms=round(latency, 1),
                message=f"Health check failed: {str(e)}",
            )
