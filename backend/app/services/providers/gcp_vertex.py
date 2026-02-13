"""Google Vertex AI provider — real GCP integration."""

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

MODELS_CACHE_TTL = 300

# Vertex AI pricing (per 1M tokens)
VERTEX_PRICING: dict[str, tuple[float, float, int]] = {
    # Gemini
    "gemini-2.0-flash": (0.10, 0.40, 1_000_000),
    "gemini-2.0-pro": (1.25, 5.00, 1_000_000),
    "gemini-1.5-pro": (1.25, 5.00, 2_000_000),
    "gemini-1.5-flash": (0.075, 0.30, 1_000_000),
    "gemini-1.0-pro": (0.50, 1.50, 32_000),
    # Claude on Vertex
    "claude-3-5-sonnet": (3.00, 15.00, 200_000),
    "claude-3-5-haiku": (1.00, 5.00, 200_000),
    "claude-3-opus": (15.00, 75.00, 200_000),
    # Llama on Vertex
    "llama-3.1-405b": (5.32, 16.00, 128_000),
    "llama-3.1-70b": (2.65, 3.50, 128_000),
    "llama-3.1-8b": (0.30, 0.60, 128_000),
    # PaLM
    "text-bison": (0.25, 0.50, 8_192),
    "chat-bison": (0.25, 0.50, 8_192),
    "code-bison": (0.25, 0.50, 6_144),
    "codechat-bison": (0.25, 0.50, 6_144),
    # Embeddings
    "text-embedding-005": (0.025, 0.0, 2_048),
    "text-embedding-004": (0.025, 0.0, 2_048),
    "textembedding-gecko": (0.025, 0.0, 3_072),
    # Imagen
    "imagen-3.0": (0.0, 0.0, 0),
    "imagegeneration": (0.0, 0.0, 0),
}


def _get_vertex_pricing(model_id: str) -> tuple[float, float]:
    for prefix in sorted(VERTEX_PRICING.keys(), key=len, reverse=True):
        if prefix.lower() in model_id.lower():
            return VERTEX_PRICING[prefix][0], VERTEX_PRICING[prefix][1]
    return 0.0, 0.0


def _get_vertex_context(model_id: str) -> int:
    for prefix in sorted(VERTEX_PRICING.keys(), key=len, reverse=True):
        if prefix.lower() in model_id.lower():
            return VERTEX_PRICING[prefix][2]
    return 0


def _estimate_cost(model_id: str, inp: int, out: int) -> float:
    ip, op = _get_vertex_pricing(model_id)
    return (inp * ip / 1_000_000) + (out * op / 1_000_000)


class GCPVertexProvider(CloudProvider):
    """Real Google Vertex AI integration using service account + REST APIs."""

    def __init__(self, project_id: str, service_account_json: str, region: str = "us-central1"):
        self._project_id = project_id
        self._region = region
        if isinstance(service_account_json, dict):
            self._sa_info = service_account_json
        elif isinstance(service_account_json, str):
            try:
                self._sa_info = json.loads(service_account_json)
            except json.JSONDecodeError:
                # Fallback: literal newlines from textarea paste or Vault roundtrip
                self._sa_info = json.loads(service_account_json, strict=False)
        else:
            raise ValueError("service_account_json must be a dict or JSON string")
        self._token: Optional[str] = None
        self._token_expires: float = 0

    async def _get_token(self) -> str:
        """Get access token via service account JWT flow."""
        if self._token and time.time() < self._token_expires - 60:
            return self._token

        import jwt as pyjwt
        now = int(time.time())
        payload = {
            "iss": self._sa_info["client_email"],
            "scope": "https://www.googleapis.com/auth/cloud-platform",
            "aud": "https://oauth2.googleapis.com/token",
            "iat": now,
            "exp": now + 3600,
        }
        signed_jwt = pyjwt.encode(payload, self._sa_info["private_key"], algorithm="RS256")

        async with httpx.AsyncClient() as client:
            resp = await client.post("https://oauth2.googleapis.com/token", data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": signed_jwt,
            })
            if resp.status_code != 200:
                raise RuntimeError(f"GCP auth failed ({resp.status_code}): {resp.text[:200]}")
            data = resp.json()
            self._token = data["access_token"]
            self._token_expires = time.time() + data.get("expires_in", 3600)
            return self._token

    # ── Credential validation ──────────────────────────────────────

    async def validate_credentials(self) -> CredentialInfo:
        try:
            token = await self._get_token()
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://cloudresourcemanager.googleapis.com/v1/projects/{self._project_id}",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 200:
                    proj = resp.json()
                    return CredentialInfo(
                        valid=True,
                        account_id=self._project_id,
                        user_id=self._sa_info.get("client_email", ""),
                        message=f"Connected to project: {proj.get('name', self._project_id)}",
                    )
                elif resp.status_code == 403:
                    return CredentialInfo(valid=False, message="Access denied — service account lacks project access")
                elif resp.status_code == 404:
                    return CredentialInfo(valid=False, message=f"Project '{self._project_id}' not found")
                else:
                    return CredentialInfo(valid=False, message=f"GCP error ({resp.status_code}): {resp.text[:200]}")
        except json.JSONDecodeError:
            return CredentialInfo(valid=False, message="Invalid service account JSON")
        except Exception as e:
            return CredentialInfo(valid=False, message=f"Connection error: {str(e)}")

    # ── Model listing ──────────────────────────────────────────────

    async def list_models(self) -> List[ModelInfo]:
        cache_key = f"vertex:models:{self._project_id}:{self._region}"
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                return [ModelInfo(**m) for m in json.loads(cached)]
        except Exception:
            pass

        models: List[ModelInfo] = []
        try:
            token = await self._get_token()
            async with httpx.AsyncClient(timeout=30.0) as client:
                # List publisher models (Gemini, PaLM, etc.)
                resp = await client.get(
                    f"https://{self._region}-aiplatform.googleapis.com/v1/"
                    f"publishers/google/models",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 200:
                    for m in resp.json().get("models", resp.json().get("publisherModels", [])):
                        model_id = m.get("name", "").split("/")[-1]
                        display = m.get("displayName", model_id)
                        inp, out = _get_vertex_pricing(model_id)
                        ctx = _get_vertex_context(model_id)

                        caps = []
                        desc = m.get("description", "").lower()
                        if "text" in desc or "chat" in desc or "gemini" in desc:
                            caps.append("text")
                        if "vision" in desc or "image" in desc and "generation" not in desc:
                            caps.append("vision")
                        if "code" in desc:
                            caps.append("code")
                        if "embedding" in desc:
                            caps.append("embeddings")
                        if "image" in desc and "generat" in desc:
                            caps.append("image_generation")
                        if not caps:
                            caps.append("text")

                        models.append(ModelInfo(
                            model_id=model_id,
                            model_name=display,
                            provider_name="Google",
                            input_modalities=["TEXT"] + (["IMAGE"] if "vision" in caps else []),
                            output_modalities=["TEXT"] + (["IMAGE"] if "image_generation" in caps else []),
                            streaming_supported=True,
                            context_window=ctx,
                            input_price_per_1m_tokens=inp,
                            output_price_per_1m_tokens=out,
                            status="ACTIVE",
                            capabilities=caps,
                        ))

                # Also check Model Garden / deployed models
                resp2 = await client.get(
                    f"https://{self._region}-aiplatform.googleapis.com/v1/"
                    f"projects/{self._project_id}/locations/{self._region}/models",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp2.status_code == 200:
                    existing_ids = {m.model_id for m in models}
                    for m in resp2.json().get("models", []):
                        mid = m.get("displayName", m.get("name", "").split("/")[-1])
                        if mid not in existing_ids:
                            models.append(ModelInfo(
                                model_id=mid,
                                model_name=mid,
                                provider_name="Google (Custom)",
                                input_modalities=["TEXT"],
                                output_modalities=["TEXT"],
                                streaming_supported=False,
                                context_window=0,
                                input_price_per_1m_tokens=0.0,
                                output_price_per_1m_tokens=0.0,
                                status="ACTIVE",
                                capabilities=["text"],
                            ))

        except Exception as e:
            logger.error(f"Vertex list_models error: {e}")
            if not models:
                raise RuntimeError(f"Failed to list Vertex AI models: {str(e)}")

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
        token = await self._get_token()

        # Gemini models use generateContent API
        if "gemini" in model_id.lower():
            body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": temperature,
                },
            }
            url = (
                f"https://{self._region}-aiplatform.googleapis.com/v1/"
                f"projects/{self._project_id}/locations/{self._region}/"
                f"publishers/google/models/{model_id}:generateContent"
            )
        else:
            # PaLM / text-bison style
            body = {
                "instances": [{"prompt": prompt}],
                "parameters": {"maxOutputTokens": max_tokens, "temperature": temperature},
            }
            url = (
                f"https://{self._region}-aiplatform.googleapis.com/v1/"
                f"projects/{self._project_id}/locations/{self._region}/"
                f"publishers/google/models/{model_id}:predict"
            )

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                }, json=body)
                latency_ms = (time.monotonic() - start) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    text, inp_tok, out_tok = self._parse_response(model_id, data)
                    return InvocationResult(
                        response_text=text,
                        input_tokens=inp_tok,
                        output_tokens=out_tok,
                        latency_ms=round(latency_ms, 1),
                        estimated_cost=_estimate_cost(model_id, inp_tok, out_tok),
                        model_id=model_id,
                    )
                elif resp.status_code == 404:
                    raise RuntimeError(f"Model '{model_id}' not found in {self._region}")
                elif resp.status_code == 429:
                    raise RuntimeError("Rate limited — Vertex AI quota exceeded")
                elif resp.status_code == 403:
                    raise RuntimeError("Access denied — check Vertex AI API is enabled and service account has aiplatform.endpoints.predict permission")
                else:
                    raise RuntimeError(f"Vertex AI error ({resp.status_code}): {resp.text[:300]}")

        except httpx.TimeoutException:
            raise RuntimeError("Model invocation timed out")
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Invocation failed: {str(e)}")

    def _parse_response(self, model_id: str, data: dict) -> tuple[str, int, int]:
        """Parse Vertex AI response."""
        if "gemini" in model_id.lower():
            candidates = data.get("candidates", [])
            text = ""
            for c in candidates:
                for part in c.get("content", {}).get("parts", []):
                    text += part.get("text", "")
            usage = data.get("usageMetadata", {})
            return text, usage.get("promptTokenCount", 0), usage.get("candidatesTokenCount", 0)
        else:
            # PaLM predict response
            preds = data.get("predictions", [])
            text = preds[0].get("content", str(preds[0])) if preds else ""
            meta = data.get("metadata", {})
            inp = meta.get("tokenMetadata", {}).get("inputTokenCount", {}).get("totalTokens", 0)
            out = meta.get("tokenMetadata", {}).get("outputTokenCount", {}).get("totalTokens", 0)
            return text, inp, out

    # ── Cost data ──────────────────────────────────────────────────

    async def get_costs(self, start_date: date, end_date: date) -> CostData:
        try:
            token = await self._get_token()
            # Use BigQuery billing export or Cloud Billing API
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"https://cloudbilling.googleapis.com/v1/projects/{self._project_id}/billingInfo",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code != 200:
                    logger.warning(f"Billing API error: {resp.status_code}")
                    return CostData(
                        total=0.0, start_date=start_date.isoformat(),
                        end_date=end_date.isoformat(), daily_costs=[],
                    )

                billing_info = resp.json()
                billing_account = billing_info.get("billingAccountName", "")

                if not billing_account:
                    return CostData(
                        total=0.0, start_date=start_date.isoformat(),
                        end_date=end_date.isoformat(), daily_costs=[],
                    )

                # Note: Detailed cost breakdown requires BigQuery export setup.
                # For now, return billing account info and zero costs (user needs
                # to enable billing export to BigQuery for detailed daily costs).
                return CostData(
                    total=0.0, currency="USD",
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                    daily_costs=[],
                )

        except Exception as e:
            logger.error(f"GCP billing error: {e}")
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
                    f"https://cloudresourcemanager.googleapis.com/v1/projects/{self._project_id}",
                    headers={"Authorization": f"Bearer {token}"},
                )
                latency = (time.monotonic() - start) * 1000
                if resp.status_code == 200:
                    proj = resp.json()
                    return HealthStatus(
                        healthy=True, latency_ms=round(latency, 1),
                        account_id=self._project_id,
                        message=f"Connected: {proj.get('name', self._project_id)}",
                    )
                return HealthStatus(
                    healthy=False, latency_ms=round(latency, 1),
                    message=f"GCP returned {resp.status_code}",
                )
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return HealthStatus(
                healthy=False, latency_ms=round(latency, 1),
                message=f"Health check failed: {str(e)}",
            )
