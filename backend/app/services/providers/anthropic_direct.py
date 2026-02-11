"""Anthropic Direct provider — real Anthropic API integration."""

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
ANTHROPIC_MODELS = [
    {
        "model_id": "claude-3-5-sonnet-20241022",
        "model_name": "Claude 3.5 Sonnet",
        "input_price_per_1m": 3.00,
        "output_price_per_1m": 15.00,
        "context_window": 200000,
        "capabilities": ["text", "vision", "code", "function_calling", "streaming"],
    },
    {
        "model_id": "claude-3-5-haiku-20241022",
        "model_name": "Claude 3.5 Haiku",
        "input_price_per_1m": 0.80,
        "output_price_per_1m": 4.00,
        "context_window": 200000,
        "capabilities": ["text", "vision", "code", "streaming"],
    },
    {
        "model_id": "claude-3-opus-20240229",
        "model_name": "Claude 3 Opus",
        "input_price_per_1m": 15.00,
        "output_price_per_1m": 75.00,
        "context_window": 200000,
        "capabilities": ["text", "vision", "code", "function_calling", "streaming"],
    },
    {
        "model_id": "claude-3-sonnet-20240229",
        "model_name": "Claude 3 Sonnet",
        "input_price_per_1m": 3.00,
        "output_price_per_1m": 15.00,
        "context_window": 200000,
        "capabilities": ["text", "vision", "code", "streaming"],
    },
    {
        "model_id": "claude-3-haiku-20240307",
        "model_name": "Claude 3 Haiku",
        "input_price_per_1m": 0.25,
        "output_price_per_1m": 1.25,
        "context_window": 200000,
        "capabilities": ["text", "vision", "code", "streaming"],
    },
]


class AnthropicDirectProvider(CloudProvider):
    """Direct Anthropic API integration using httpx."""

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._base_url = "https://api.anthropic.com/v1"
        self._headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

    # ── Credential validation ──────────────────────────────────────

    async def validate_credentials(self) -> CredentialInfo:
        try:
            # Test with a minimal completion request since Anthropic doesn't have a models endpoint
            async with httpx.AsyncClient() as client:
                test_body = {
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hi"}]
                }
                
                resp = await client.post(
                    f"{self._base_url}/messages",
                    headers=self._headers,
                    json=test_body,
                    timeout=10.0,
                )
                
                if resp.status_code == 200:
                    return CredentialInfo(
                        valid=True,
                        account_id="anthropic_user",
                        user_id="anthropic_user",
                        message="Credentials valid",
                    )
                elif resp.status_code == 401:
                    error_detail = ""
                    try:
                        error_data = resp.json()
                        error_detail = error_data.get("error", {}).get("message", "")
                    except:
                        pass
                    return CredentialInfo(
                        valid=False,
                        message=f"Invalid API key{': ' + error_detail if error_detail else ''}",
                    )
                elif resp.status_code == 429:
                    return CredentialInfo(
                        valid=False,
                        message="Rate limited - API key may be valid but quota exceeded",
                    )
                else:
                    error_text = resp.text
                    return CredentialInfo(
                        valid=False,
                        message=f"API error: {resp.status_code} - {error_text}",
                    )
        except httpx.TimeoutException:
            return CredentialInfo(valid=False, message="Connection timeout")
        except Exception as e:
            return CredentialInfo(valid=False, message=f"Connection error: {str(e)}")

    # ── Model listing ──────────────────────────────────────────────

    async def list_models(self) -> List[ModelInfo]:
        # Check Redis cache
        cache_key = "anthropic:models:default"
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                return [ModelInfo(**m) for m in json.loads(cached)]
        except Exception:
            pass  # Redis down — continue without cache

        # Anthropic doesn't have a models endpoint, so we use static catalog
        try:
            models = []
            for model_def in ANTHROPIC_MODELS:
                models.append(ModelInfo(
                    model_id=model_def["model_id"],
                    model_name=model_def["model_name"],
                    provider_name="Anthropic",
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
            logger.error(f"Anthropic list_models error: {e}")
            # Return static catalog as fallback
            return [ModelInfo(
                model_id=model_def["model_id"],
                model_name=model_def["model_name"],
                provider_name="Anthropic",
                input_modalities=["TEXT"] + (["IMAGE"] if "vision" in model_def["capabilities"] else []),
                output_modalities=["TEXT"],
                streaming_supported="streaming" in model_def["capabilities"],
                context_window=model_def["context_window"],
                input_price_per_1m_tokens=model_def["input_price_per_1m"],
                output_price_per_1m_tokens=model_def["output_price_per_1m"],
                status="ACTIVE",
                capabilities=model_def["capabilities"],
            ) for model_def in ANTHROPIC_MODELS]

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
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }

        start = time.monotonic()
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._base_url}/messages",
                    headers=self._headers,
                    json=body,
                    timeout=60.0,
                )
                latency_ms = (time.monotonic() - start) * 1000

                if resp.status_code == 200:
                    result_body = resp.json()
                    
                    # Parse response
                    text = ""
                    content = result_body.get("content", [])
                    for block in content:
                        if block.get("type") == "text":
                            text += block.get("text", "")

                    # Parse usage
                    usage = result_body.get("usage", {})
                    input_tokens = usage.get("input_tokens", 0)
                    output_tokens = usage.get("output_tokens", 0)

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
                    error_detail = ""
                    try:
                        error_data = resp.json()
                        error_detail = error_data.get("error", {}).get("message", "")
                    except:
                        pass

                    if resp.status_code == 401:
                        raise RuntimeError("Invalid API key")
                    elif resp.status_code == 429:
                        raise RuntimeError("Rate limited — please try again shortly")
                    elif resp.status_code == 400:
                        raise RuntimeError(f"Invalid request: {error_detail or error_text}")
                    else:
                        raise RuntimeError(f"Anthropic API error ({resp.status_code}): {error_detail or error_text}")

        except httpx.TimeoutException:
            raise RuntimeError("Request timed out — try a smaller prompt or check connectivity")
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"Anthropic invocation error: {str(e)}")

    # ── Cost data ──────────────────────────────────────────────────

    async def get_costs(self, start_date: date, end_date: date) -> CostData:
        # Anthropic doesn't provide a cost API, so we return empty data
        # In a production system, you might track costs locally based on usage
        try:
            return CostData(
                total=0.0,
                currency="USD",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                daily_costs=[],
            )
        except Exception as e:
            logger.error(f"Anthropic get_costs error: {e}")
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
            # Use a minimal completion request for health check
            async with httpx.AsyncClient() as client:
                test_body = {
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 5,
                    "messages": [{"role": "user", "content": "Hi"}]
                }
                
                resp = await client.post(
                    f"{self._base_url}/messages",
                    headers=self._headers,
                    json=test_body,
                    timeout=10.0,
                )
                latency = (time.monotonic() - start) * 1000
                
                if resp.status_code == 200:
                    return HealthStatus(
                        healthy=True,
                        latency_ms=round(latency, 1),
                        account_id="anthropic_user",
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