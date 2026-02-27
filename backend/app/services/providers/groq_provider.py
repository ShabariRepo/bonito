"""Groq provider — ultra-fast LPU inference via OpenAI-compatible API."""

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

# Static model catalog with pricing (as of early 2026)
GROQ_MODELS = [
    {
        "model_id": "llama-3.3-70b-versatile",
        "model_name": "Llama 3.3 70B",
        "input_price_per_1m": 0.59,
        "output_price_per_1m": 0.79,
        "context_window": 128000,
        "capabilities": ["text", "code", "function_calling", "streaming"],
    },
    {
        "model_id": "llama-3.1-8b-instant",
        "model_name": "Llama 3.1 8B",
        "input_price_per_1m": 0.05,
        "output_price_per_1m": 0.08,
        "context_window": 128000,
        "capabilities": ["text", "code", "streaming"],
    },
    {
        "model_id": "llama-3.3-70b-specdec",
        "model_name": "Llama 3.3 70B Speculative Decoding",
        "input_price_per_1m": 0.59,
        "output_price_per_1m": 0.79,
        "context_window": 32000,
        "capabilities": ["text", "code", "streaming"],
    },
    {
        "model_id": "mixtral-8x7b-32768",
        "model_name": "Mixtral 8x7B",
        "input_price_per_1m": 0.24,
        "output_price_per_1m": 0.24,
        "context_window": 32768,
        "capabilities": ["text", "code", "streaming"],
    },
    {
        "model_id": "gemma2-9b-it",
        "model_name": "Gemma 2 9B",
        "input_price_per_1m": 0.20,
        "output_price_per_1m": 0.20,
        "context_window": 8000,
        "capabilities": ["text", "code", "streaming"],
    },
    {
        "model_id": "deepseek-r1-distill-llama-70b",
        "model_name": "DeepSeek R1 Distill 70B",
        "input_price_per_1m": 0.75,
        "output_price_per_1m": 0.99,
        "context_window": 128000,
        "capabilities": ["text", "reasoning", "code", "streaming"],
    },
    {
        "model_id": "qwen-2.5-coder-32b",
        "model_name": "Qwen 2.5 Coder 32B",
        "input_price_per_1m": 0.20,
        "output_price_per_1m": 0.20,
        "context_window": 128000,
        "capabilities": ["text", "code", "streaming"],
    },
    {
        "model_id": "llama-3.2-1b-preview",
        "model_name": "Llama 3.2 1B",
        "input_price_per_1m": 0.04,
        "output_price_per_1m": 0.04,
        "context_window": 128000,
        "capabilities": ["text", "streaming"],
    },
    {
        "model_id": "llama-3.2-3b-preview",
        "model_name": "Llama 3.2 3B",
        "input_price_per_1m": 0.06,
        "output_price_per_1m": 0.06,
        "context_window": 128000,
        "capabilities": ["text", "code", "streaming"],
    },
    {
        "model_id": "llama-3.2-11b-vision-preview",
        "model_name": "Llama 3.2 11B Vision",
        "input_price_per_1m": 0.18,
        "output_price_per_1m": 0.18,
        "context_window": 128000,
        "capabilities": ["text", "vision", "streaming"],
    },
    {
        "model_id": "llama-3.2-90b-vision-preview",
        "model_name": "Llama 3.2 90B Vision",
        "input_price_per_1m": 0.90,
        "output_price_per_1m": 0.90,
        "context_window": 128000,
        "capabilities": ["text", "vision", "streaming"],
    },
]


class GroqProvider(CloudProvider):
    """Groq LPU inference via OpenAI-compatible API."""

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._base_url = "https://api.groq.com/openai/v1"
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

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
                    return CredentialInfo(
                        valid=True,
                        account_id="groq",
                        user_id="groq_user",
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
        cache_key = "groq:models:default"
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
            for model_def in GROQ_MODELS:
                # Only include models that exist in API or use static catalog as fallback
                if not api_model_ids or model_def["model_id"] in api_model_ids:
                    models.append(ModelInfo(
                        model_id=model_def["model_id"],
                        model_name=model_def["model_name"],
                        provider_name="Groq",
                        input_modalities=["TEXT"] + (["IMAGE"] if "vision" in model_def["capabilities"] else []),
                        output_modalities=["TEXT"],
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
            logger.error(f"Groq list_models error: {e}")
            # Fall back to static catalog
            return [ModelInfo(
                model_id=model_def["model_id"],
                model_name=model_def["model_name"],
                provider_name="Groq",
                input_modalities=["TEXT"] + (["IMAGE"] if "vision" in model_def["capabilities"] else []),
                output_modalities=["TEXT"],
                streaming_supported="streaming" in model_def["capabilities"],
                context_window=model_def["context_window"],
                input_price_per_1m_tokens=model_def["input_price_per_1m"],
                output_price_per_1m_tokens=model_def["output_price_per_1m"],
                status="ACTIVE",
                capabilities=model_def["capabilities"],
            ) for model_def in GROQ_MODELS]

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
                        raise RuntimeError(f"Groq API error ({resp.status_code}): {error_text}")

        except httpx.TimeoutException:
            raise RuntimeError("Request timed out — try a smaller prompt or check connectivity")
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"Groq invocation error: {str(e)}")

    # ── Cost data ──────────────────────────────────────────────────

    async def get_costs(self, start_date: date, end_date: date) -> CostData:
        # Groq doesn't provide a cost API — track costs locally
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
                        account_id="groq",
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
