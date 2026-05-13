"""OpenRouter provider — unified API access to 300+ models via OpenAI-compatible API."""

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

# Static fallback catalog — popular models available on OpenRouter
OPENROUTER_MODELS = [
    {
        "model_id": "openai/gpt-4o",
        "model_name": "GPT-4o (via OpenRouter)",
        "input_price_per_1m": 2.50,
        "output_price_per_1m": 10.00,
        "context_window": 128000,
        "capabilities": ["text", "vision", "code", "function_calling", "streaming"],
    },
    {
        "model_id": "openai/gpt-4o-mini",
        "model_name": "GPT-4o Mini (via OpenRouter)",
        "input_price_per_1m": 0.15,
        "output_price_per_1m": 0.60,
        "context_window": 128000,
        "capabilities": ["text", "vision", "code", "function_calling", "streaming"],
    },
    {
        "model_id": "anthropic/claude-sonnet-4-20250514",
        "model_name": "Claude Sonnet 4 (via OpenRouter)",
        "input_price_per_1m": 3.00,
        "output_price_per_1m": 15.00,
        "context_window": 200000,
        "capabilities": ["text", "vision", "code", "function_calling", "streaming"],
    },
    {
        "model_id": "anthropic/claude-3.5-haiku-20241022",
        "model_name": "Claude 3.5 Haiku (via OpenRouter)",
        "input_price_per_1m": 0.80,
        "output_price_per_1m": 4.00,
        "context_window": 200000,
        "capabilities": ["text", "vision", "code", "streaming"],
    },
    {
        "model_id": "google/gemini-2.0-flash-001",
        "model_name": "Gemini 2.0 Flash (via OpenRouter)",
        "input_price_per_1m": 0.10,
        "output_price_per_1m": 0.40,
        "context_window": 1048576,
        "capabilities": ["text", "vision", "code", "function_calling", "streaming"],
    },
    {
        "model_id": "meta-llama/llama-3.3-70b-instruct",
        "model_name": "Llama 3.3 70B (via OpenRouter)",
        "input_price_per_1m": 0.39,
        "output_price_per_1m": 0.39,
        "context_window": 131072,
        "capabilities": ["text", "code", "function_calling", "streaming"],
    },
    {
        "model_id": "deepseek/deepseek-r1",
        "model_name": "DeepSeek R1 (via OpenRouter)",
        "input_price_per_1m": 0.55,
        "output_price_per_1m": 2.19,
        "context_window": 65536,
        "capabilities": ["text", "reasoning", "code", "streaming"],
    },
    {
        "model_id": "mistralai/mistral-large-2411",
        "model_name": "Mistral Large (via OpenRouter)",
        "input_price_per_1m": 2.00,
        "output_price_per_1m": 6.00,
        "context_window": 131072,
        "capabilities": ["text", "code", "function_calling", "streaming"],
    },
    {
        "model_id": "qwen/qwen-2.5-72b-instruct",
        "model_name": "Qwen 2.5 72B (via OpenRouter)",
        "input_price_per_1m": 0.36,
        "output_price_per_1m": 0.36,
        "context_window": 131072,
        "capabilities": ["text", "code", "function_calling", "streaming"],
    },
    {
        "model_id": "cohere/command-r-plus",
        "model_name": "Command R+ (via OpenRouter)",
        "input_price_per_1m": 2.50,
        "output_price_per_1m": 10.00,
        "context_window": 128000,
        "capabilities": ["text", "code", "function_calling", "streaming"],
    },
]


class OpenRouterProvider(CloudProvider):
    """OpenRouter — unified access to 300+ models via OpenAI-compatible API."""

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._base_url = "https://openrouter.ai/api/v1"
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://getbonito.com",
            "X-Title": "Bonito AI",
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
                    data = resp.json().get("data", [])
                    return CredentialInfo(
                        valid=True,
                        account_id="openrouter",
                        user_id="openrouter_user",
                        message=f"Credentials valid — {len(data)} models available",
                    )
                elif resp.status_code == 401:
                    return CredentialInfo(
                        valid=False,
                        message="Invalid API key",
                    )
                elif resp.status_code == 429:
                    return CredentialInfo(
                        valid=False,
                        message="Rate limited — API key may be valid but quota exceeded",
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
        cache_key = "openrouter:models:default"
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                return [ModelInfo(**m) for m in json.loads(cached)]
        except Exception:
            pass

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._base_url}/models",
                    headers=self._headers,
                    timeout=15.0,
                )

                if resp.status_code == 200:
                    api_models = resp.json().get("data", [])
                    models = []
                    for m in api_models:
                        model_id = m.get("id", "")
                        pricing = m.get("pricing", {})
                        input_price = float(pricing.get("prompt", "0")) * 1_000_000 if pricing.get("prompt") else 0
                        output_price = float(pricing.get("completion", "0")) * 1_000_000 if pricing.get("completion") else 0
                        ctx = m.get("context_length", 4096)

                        caps = ["text", "streaming"]
                        arch = m.get("architecture", {})
                        if arch.get("modality", "").startswith("text+image"):
                            caps.append("vision")
                        desc = (m.get("description") or "").lower()
                        if "code" in desc or "coder" in model_id.lower():
                            caps.append("code")
                        if "function" in desc or "tool" in desc:
                            caps.append("function_calling")

                        models.append(ModelInfo(
                            model_id=model_id,
                            model_name=m.get("name", model_id),
                            provider_name="OpenRouter",
                            input_modalities=["TEXT"] + (["IMAGE"] if "vision" in caps else []),
                            output_modalities=["TEXT"],
                            streaming_supported=True,
                            context_window=ctx,
                            input_price_per_1m_tokens=input_price,
                            output_price_per_1m_tokens=output_price,
                            status="ACTIVE",
                            capabilities=caps,
                        ))

                    # Cache results
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
            logger.error(f"OpenRouter list_models error: {e}")

        # Fall back to static catalog
        return [ModelInfo(
            model_id=model_def["model_id"],
            model_name=model_def["model_name"],
            provider_name="OpenRouter",
            input_modalities=["TEXT"] + (["IMAGE"] if "vision" in model_def["capabilities"] else []),
            output_modalities=["TEXT"],
            streaming_supported="streaming" in model_def["capabilities"],
            context_window=model_def["context_window"],
            input_price_per_1m_tokens=model_def["input_price_per_1m"],
            output_price_per_1m_tokens=model_def["output_price_per_1m"],
            status="ACTIVE",
            capabilities=model_def["capabilities"],
        ) for model_def in OPENROUTER_MODELS]

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

                    text = ""
                    choices = result_body.get("choices", [])
                    if choices:
                        message = choices[0].get("message", {})
                        text = message.get("content", "")

                    usage = result_body.get("usage", {})
                    input_tokens = usage.get("prompt_tokens", 0)
                    output_tokens = usage.get("completion_tokens", 0)

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
                        raise RuntimeError(f"OpenRouter API error ({resp.status_code}): {error_text}")

        except httpx.TimeoutException:
            raise RuntimeError("Request timed out — try a smaller prompt or check connectivity")
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"OpenRouter invocation error: {str(e)}")

    # ── Cost data ──────────────────────────────────────────────────

    async def get_costs(self, start_date: date, end_date: date) -> CostData:
        # OpenRouter doesn't provide a cost API — track costs locally
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
                        account_id="openrouter",
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
