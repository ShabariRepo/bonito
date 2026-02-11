"""OpenAI Direct provider — real OpenAI API integration."""

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

MODELS_CACHE_TTL = 300  # 5 minutes

# Static model catalog with pricing (as of 2025)
OPENAI_MODELS = [
    {
        "model_id": "gpt-4o",
        "model_name": "GPT-4o",
        "input_price_per_1m": 2.50,
        "output_price_per_1m": 10.00,
        "context_window": 128000,
        "capabilities": ["text", "vision", "code", "function_calling", "streaming"],
    },
    {
        "model_id": "gpt-4o-mini",
        "model_name": "GPT-4o Mini",
        "input_price_per_1m": 0.15,
        "output_price_per_1m": 0.60,
        "context_window": 128000,
        "capabilities": ["text", "vision", "code", "function_calling", "streaming"],
    },
    {
        "model_id": "o1",
        "model_name": "o1",
        "input_price_per_1m": 15.00,
        "output_price_per_1m": 60.00,
        "context_window": 200000,
        "capabilities": ["text", "reasoning", "code"],
    },
    {
        "model_id": "o3-mini",
        "model_name": "o3 Mini",
        "input_price_per_1m": 1.10,
        "output_price_per_1m": 4.40,
        "context_window": 128000,
        "capabilities": ["text", "reasoning", "code"],
    },
    {
        "model_id": "gpt-3.5-turbo",
        "model_name": "GPT-3.5 Turbo",
        "input_price_per_1m": 0.50,
        "output_price_per_1m": 1.50,
        "context_window": 16385,
        "capabilities": ["text", "code", "function_calling", "streaming"],
    },
    {
        "model_id": "text-embedding-3-large",
        "model_name": "Text Embedding 3 Large",
        "input_price_per_1m": 0.13,
        "output_price_per_1m": 0.00,
        "context_window": 8191,
        "capabilities": ["embeddings"],
    },
    {
        "model_id": "text-embedding-3-small",
        "model_name": "Text Embedding 3 Small",
        "input_price_per_1m": 0.02,
        "output_price_per_1m": 0.00,
        "context_window": 8191,
        "capabilities": ["embeddings"],
    },
    {
        "model_id": "dall-e-3",
        "model_name": "DALL-E 3",
        "input_price_per_1m": 0.04,
        "output_price_per_1m": 0.00,
        "context_window": 0,
        "capabilities": ["image_generation"],
    },
]


class OpenAIDirectProvider(CloudProvider):
    """Direct OpenAI API integration using httpx."""

    def __init__(self, api_key: str, organization_id: Optional[str] = None):
        self._api_key = api_key
        self._organization_id = organization_id
        self._base_url = "https://api.openai.com/v1"
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if organization_id:
            self._headers["OpenAI-Organization"] = organization_id

    # ── Credential validation ──────────────────────────────────────

    async def validate_credentials(self) -> CredentialInfo:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._base_url}/models",
                    headers=self._headers,
                    timeout=10.0,
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    # Extract organization from response if available
                    org_id = self._organization_id or "default"
                    return CredentialInfo(
                        valid=True,
                        account_id=org_id,
                        user_id="openai_user",
                        message="Credentials valid",
                    )
                elif resp.status_code == 401:
                    return CredentialInfo(
                        valid=False,
                        message="Invalid API key",
                    )
                elif resp.status_code == 429:
                    return CredentialInfo(
                        valid=False,
                        message="Rate limited - API key may be valid but quota exceeded",
                    )
                else:
                    return CredentialInfo(
                        valid=False,
                        message=f"API error: {resp.status_code} - {resp.text}",
                    )
        except httpx.TimeoutException:
            return CredentialInfo(valid=False, message="Connection timeout")
        except Exception as e:
            return CredentialInfo(valid=False, message=f"Connection error: {str(e)}")

    # ── Model listing ──────────────────────────────────────────────

    async def list_models(self) -> List[ModelInfo]:
        # Check Redis cache
        cache_key = f"openai:models:{self._organization_id or 'default'}"
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                return [ModelInfo(**m) for m in json.loads(cached)]
        except Exception:
            pass  # Redis down — continue without cache

        try:
            # Combine static catalog with live API discovery
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._base_url}/models",
                    headers=self._headers,
                    timeout=10.0,
                )
                
                if resp.status_code == 200:
                    api_models = resp.json().get("data", [])
                    api_model_ids = {m["id"] for m in api_models}
                else:
                    # Fall back to static catalog if API fails
                    api_model_ids = set()

            models = []
            for model_def in OPENAI_MODELS:
                # Only include models that exist in API or use static catalog as fallback
                if not api_model_ids or model_def["model_id"] in api_model_ids:
                    models.append(ModelInfo(
                        model_id=model_def["model_id"],
                        model_name=model_def["model_name"],
                        provider_name="OpenAI",
                        input_modalities=["TEXT"] + (["IMAGE"] if "vision" in model_def["capabilities"] else []),
                        output_modalities=["TEXT"] + (["IMAGE"] if "image_generation" in model_def["capabilities"] else []),
                        streaming_supported="streaming" in model_def["capabilities"],
                        context_window=model_def["context_window"],
                        input_price_per_1m_tokens=model_def["input_price_per_1m"],
                        output_price_per_1m_tokens=model_def["output_price_per_1m"],
                        status="ACTIVE",
                        capabilities=model_def["capabilities"],
                    ))

            # Cache in Redis
            try:
                serialized = json.dumps([
                    {
                        "model_id": m.model_id,
                        "model_name": m.model_name,
                        "provider_name": m.provider_name,
                        "input_modalities": m.input_modalities,
                        "output_modalities": m.output_modalities,
                        "streaming_supported": m.streaming_supported,
                        "context_window": m.context_window,
                        "input_price_per_1m_tokens": m.input_price_per_1m_tokens,
                        "output_price_per_1m_tokens": m.output_price_per_1m_tokens,
                        "status": m.status,
                        "capabilities": m.capabilities,
                    }
                    for m in models
                ])
                await redis_client.setex(cache_key, MODELS_CACHE_TTL, serialized)
            except Exception:
                pass

            return models

        except Exception as e:
            logger.error(f"OpenAI list_models error: {e}")
            # Fall back to static catalog
            return [ModelInfo(
                model_id=model_def["model_id"],
                model_name=model_def["model_name"],
                provider_name="OpenAI",
                input_modalities=["TEXT"] + (["IMAGE"] if "vision" in model_def["capabilities"] else []),
                output_modalities=["TEXT"] + (["IMAGE"] if "image_generation" in model_def["capabilities"] else []),
                streaming_supported="streaming" in model_def["capabilities"],
                context_window=model_def["context_window"],
                input_price_per_1m_tokens=model_def["input_price_per_1m"],
                output_price_per_1m_tokens=model_def["output_price_per_1m"],
                status="ACTIVE",
                capabilities=model_def["capabilities"],
            ) for model_def in OPENAI_MODELS]

    async def get_model(self, model_id: str) -> Optional[ModelInfo]:
        models = await self.list_models()
        for m in models:
            if m.model_id == model_id:
                return m
        return None

    # ── Model invocation ───────────────────────────────────────────

    async def invoke_model(
        self, model_id: str, prompt: str, max_tokens: int = 1024, temperature: float = 0.7
    ) -> InvocationResult:
        body = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        start = time.monotonic()
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=self._headers,
                    json=body,
                    timeout=60.0,
                )
                latency_ms = (time.monotonic() - start) * 1000

                if resp.status_code == 200:
                    result_body = resp.json()
                    
                    # Parse response
                    text = ""
                    choices = result_body.get("choices", [])
                    if choices:
                        message = choices[0].get("message", {})
                        text = message.get("content", "")

                    # Parse usage
                    usage = result_body.get("usage", {})
                    input_tokens = usage.get("prompt_tokens", 0)
                    output_tokens = usage.get("completion_tokens", 0)

                    # Estimate cost
                    model_info = await self.get_model(model_id)
                    estimated_cost = 0.0
                    if model_info:
                        estimated_cost = (
                            (input_tokens / 1_000_000) * model_info.input_price_per_1m_tokens +
                            (output_tokens / 1_000_000) * model_info.output_price_per_1m_tokens
                        )

                    return InvocationResult(
                        response_text=text,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        latency_ms=round(latency_ms, 1),
                        estimated_cost=round(estimated_cost, 6),
                        model_id=model_id,
                    )
                else:
                    error_text = resp.text
                    if resp.status_code == 401:
                        raise RuntimeError("Invalid API key")
                    elif resp.status_code == 429:
                        raise RuntimeError("Rate limited — please try again shortly")
                    elif resp.status_code == 400:
                        raise RuntimeError(f"Invalid request: {error_text}")
                    else:
                        raise RuntimeError(f"OpenAI API error ({resp.status_code}): {error_text}")

        except httpx.TimeoutException:
            raise RuntimeError("Request timed out — try a smaller prompt or check connectivity")
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"OpenAI invocation error: {str(e)}")

    # ── Cost data ──────────────────────────────────────────────────

    async def get_costs(self, start_date: date, end_date: date) -> CostData:
        # OpenAI doesn't provide a simple cost API, so we return empty data
        # In a production system, you might integrate with their usage API or track costs locally
        try:
            # You could integrate with OpenAI's usage API here:
            # https://api.openai.com/v1/usage
            # But it requires specific permissions and is not always available
            
            return CostData(
                total=0.0,
                currency="USD",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                daily_costs=[],
            )
        except Exception as e:
            logger.error(f"OpenAI get_costs error: {e}")
            return CostData(
                total=0.0,
                currency="USD",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                daily_costs=[],
            )

    # ── Health check ───────────────────────────────────────────────

    async def health_check(self) -> HealthStatus:
        start = time.monotonic()
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._base_url}/models",
                    headers=self._headers,
                    timeout=10.0,
                )
                latency = (time.monotonic() - start) * 1000
                
                if resp.status_code == 200:
                    return HealthStatus(
                        healthy=True,
                        latency_ms=round(latency, 1),
                        account_id=self._organization_id or "default",
                        message="Connection healthy",
                    )
                else:
                    return HealthStatus(
                        healthy=False,
                        latency_ms=round(latency, 1),
                        message=f"Health check failed: HTTP {resp.status_code}",
                    )
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return HealthStatus(
                healthy=False,
                latency_ms=round(latency, 1),
                message=f"Health check failed: {str(e)}",
            )