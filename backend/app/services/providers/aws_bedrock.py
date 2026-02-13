"""AWS Bedrock provider — real boto3 integration."""

import json
import time
import logging
from datetime import date
from typing import List, Optional

import aioboto3
from botocore.exceptions import ClientError

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
from app.services.providers.aws_pricing import (
    estimate_cost,
    get_context_window,
    get_pricing,
)

logger = logging.getLogger(__name__)

MODELS_CACHE_TTL = 300  # 5 minutes


class AWSBedrockProvider(CloudProvider):
    """Real AWS Bedrock integration using aioboto3."""

    def __init__(self, access_key_id: str, secret_access_key: str, region: str = "us-east-1"):
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._region = region
        self._session = aioboto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
        )

    # ── Credential validation ──────────────────────────────────────

    async def validate_credentials(self) -> CredentialInfo:
        try:
            async with self._session.client("sts") as sts:
                resp = await sts.get_caller_identity()
                return CredentialInfo(
                    valid=True,
                    account_id=resp["Account"],
                    arn=resp["Arn"],
                    user_id=resp["UserId"],
                    message="Credentials valid",
                )
        except ClientError as e:
            code = e.response["Error"]["Code"]
            messages = {
                "InvalidClientTokenId": "Invalid Access Key ID",
                "SignatureDoesNotMatch": "Invalid Secret Access Key",
                "ExpiredToken": "Credentials have expired",
                "AccessDenied": "Access denied — check IAM permissions",
            }
            return CredentialInfo(
                valid=False,
                message=messages.get(code, f"AWS error: {code} — {e.response['Error']['Message']}"),
            )
        except Exception as e:
            return CredentialInfo(valid=False, message=f"Connection error: {str(e)}")

    # ── Model listing ──────────────────────────────────────────────

    async def list_models(self) -> List[ModelInfo]:
        # Check Redis cache
        cache_key = f"bedrock:models:{self._region}"
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                return [ModelInfo(**m) for m in json.loads(cached)]
        except Exception:
            pass  # Redis down — continue without cache

        try:
            async with self._session.client("bedrock") as bedrock:
                # Get models the account actually has access to
                enabled_ids: set[str] = set()
                try:
                    paginator = bedrock.get_paginator("list_inference_profiles") if hasattr(bedrock, "get_paginator") else None
                    # list_foundation_models with byInferenceType or check model access
                    access_resp = await bedrock.list_foundation_models(byOutputModality="TEXT")
                    # Also try to get enabled model access list
                    try:
                        access_list = await bedrock.list_model_access()
                        for entry in access_list.get("modelAccessList", []):
                            if entry.get("accessStatus") == "ENABLED":
                                enabled_ids.add(entry.get("modelId", ""))
                    except Exception:
                        pass  # API might not be available, continue showing all
                except Exception:
                    pass

                resp = await bedrock.list_foundation_models()
                models = []
                for m in resp.get("modelSummaries", []):
                    model_id = m["modelId"]
                    inp_price, out_price = get_pricing(model_id)
                    ctx = get_context_window(model_id)

                    # Derive provider name from modelId prefix
                    provider_name = model_id.split(".")[0].capitalize() if "." in model_id else "Unknown"
                    provider_map = {
                        "Anthropic": "Anthropic",
                        "Meta": "Meta",
                        "Amazon": "Amazon",
                        "Cohere": "Cohere",
                        "Mistral": "Mistral",
                        "Ai21": "AI21 Labs",
                        "Stability": "Stability AI",
                    }
                    provider_name = provider_map.get(provider_name, provider_name)

                    # Build capabilities list
                    caps = []
                    input_mods = m.get("inputModalities", [])
                    output_mods = m.get("outputModalities", [])
                    if "TEXT" in input_mods:
                        caps.append("text")
                    if "IMAGE" in input_mods:
                        caps.append("vision")
                    if "IMAGE" in output_mods:
                        caps.append("image_generation")
                    if "EMBEDDING" in output_mods:
                        caps.append("embeddings")
                    streaming = m.get("responseStreamingSupported", False)
                    if streaming:
                        caps.append("streaming")

                    # Determine access status
                    lifecycle = m.get("modelLifecycle", {}).get("status", "ACTIVE")
                    if enabled_ids:
                        access_status = "ENABLED" if model_id in enabled_ids else "NOT_ENABLED"
                    else:
                        access_status = lifecycle  # Fallback if we couldn't get access list

                    models.append(ModelInfo(
                        model_id=model_id,
                        model_name=m.get("modelName", model_id),
                        provider_name=provider_name,
                        input_modalities=input_mods,
                        output_modalities=output_mods,
                        streaming_supported=streaming,
                        context_window=ctx,
                        input_price_per_1m_tokens=inp_price,
                        output_price_per_1m_tokens=out_price,
                        status=access_status,
                        capabilities=caps,
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

        except ClientError as e:
            logger.error(f"Bedrock list_models error: {e}")
            raise RuntimeError(f"Failed to list models: {e.response['Error']['Message']}")

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
        body = self._build_request_body(model_id, prompt, max_tokens, temperature)

        start = time.monotonic()
        try:
            async with self._session.client("bedrock-runtime") as runtime:
                resp = await runtime.invoke_model(
                    modelId=model_id,
                    body=json.dumps(body),
                    contentType="application/json",
                    accept="application/json",
                )
                latency_ms = (time.monotonic() - start) * 1000
                result_body = json.loads(await resp["body"].read())
                text, inp_tok, out_tok = self._parse_response(model_id, result_body)

                return InvocationResult(
                    response_text=text,
                    input_tokens=inp_tok,
                    output_tokens=out_tok,
                    latency_ms=round(latency_ms, 1),
                    estimated_cost=estimate_cost(model_id, inp_tok, out_tok),
                    model_id=model_id,
                )

        except ClientError as e:
            code = e.response["Error"]["Code"]
            msg = e.response["Error"]["Message"]
            error_map = {
                "ModelNotReadyException": "Model is not yet available in this region",
                "ThrottlingException": "Rate limited — please try again shortly",
                "ValidationException": f"Invalid request: {msg}",
                "AccessDeniedException": "Access denied — check IAM permissions for bedrock:InvokeModel",
                "ModelTimeoutException": "Model timed out — try a smaller prompt or different model",
                "ServiceQuotaExceededException": "Quota exceeded — request a limit increase in AWS console",
            }
            raise RuntimeError(error_map.get(code, f"AWS error ({code}): {msg}"))

    def _build_request_body(self, model_id: str, prompt: str, max_tokens: int, temperature: float) -> dict:
        """Build model-specific request body."""
        if model_id.startswith("anthropic."):
            return {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
        elif model_id.startswith("meta.llama"):
            return {
                "prompt": prompt,
                "max_gen_len": max_tokens,
                "temperature": temperature,
            }
        elif model_id.startswith("amazon.titan-text"):
            return {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": max_tokens,
                    "temperature": temperature,
                },
            }
        elif model_id.startswith("cohere.command"):
            return {
                "message": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        elif model_id.startswith("mistral."):
            return {
                "prompt": f"<s>[INST] {prompt} [/INST]",
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        elif model_id.startswith("ai21."):
            return {
                "prompt": prompt,
                "maxTokens": max_tokens,
                "temperature": temperature,
            }
        else:
            # Generic fallback
            return {
                "inputText": prompt,
                "textGenerationConfig": {"maxTokenCount": max_tokens, "temperature": temperature},
            }

    def _parse_response(self, model_id: str, body: dict) -> tuple[str, int, int]:
        """Parse model-specific response. Returns (text, input_tokens, output_tokens)."""
        if model_id.startswith("anthropic."):
            text = ""
            for block in body.get("content", []):
                if block.get("type") == "text":
                    text += block["text"]
            usage = body.get("usage", {})
            return text, usage.get("input_tokens", 0), usage.get("output_tokens", 0)

        elif model_id.startswith("meta.llama"):
            return (
                body.get("generation", ""),
                body.get("prompt_token_count", 0),
                body.get("generation_token_count", 0),
            )

        elif model_id.startswith("amazon.titan-text"):
            results = body.get("results", [{}])
            text = results[0].get("outputText", "") if results else ""
            inp = body.get("inputTextTokenCount", 0)
            out = results[0].get("tokenCount", 0) if results else 0
            return text, inp, out

        elif model_id.startswith("cohere.command"):
            return (
                body.get("text", ""),
                body.get("meta", {}).get("billed_units", {}).get("input_tokens", 0),
                body.get("meta", {}).get("billed_units", {}).get("output_tokens", 0),
            )

        elif model_id.startswith("mistral."):
            outputs = body.get("outputs", [{}])
            text = outputs[0].get("text", "") if outputs else ""
            return text, 0, 0  # Mistral doesn't return token counts in Bedrock

        elif model_id.startswith("ai21."):
            completions = body.get("completions", [{}])
            text = completions[0].get("data", {}).get("text", "") if completions else ""
            return text, 0, 0

        else:
            return str(body), 0, 0

    # ── Cost data ──────────────────────────────────────────────────

    async def get_costs(self, start_date: date, end_date: date) -> CostData:
        try:
            async with self._session.client("ce", region_name="us-east-1") as ce:
                resp = await ce.get_cost_and_usage(
                    TimePeriod={
                        "Start": start_date.isoformat(),
                        "End": end_date.isoformat(),
                    },
                    Granularity="DAILY",
                    Metrics=["UnblendedCost"],
                    Filter={
                        "Dimensions": {
                            "Key": "SERVICE",
                            "Values": ["Amazon Bedrock"],
                        }
                    },
                    GroupBy=[{"Type": "DIMENSION", "Key": "USAGE_TYPE"}],
                )

                daily_costs = []
                total = 0.0
                for period in resp.get("ResultsByTime", []):
                    day = period["TimePeriod"]["Start"]
                    for group in period.get("Groups", []):
                        amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                        usage_type = group["Keys"][0] if group["Keys"] else ""
                        total += amount
                        daily_costs.append(DailyCost(
                            date=day,
                            amount=round(amount, 6),
                            currency="USD",
                            service="Amazon Bedrock",
                            usage_type=usage_type,
                        ))

                return CostData(
                    total=round(total, 2),
                    currency="USD",
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                    daily_costs=daily_costs,
                )

        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == "DataUnavailableException":
                return CostData(
                    total=0.0,
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                    daily_costs=[],
                )
            raise RuntimeError(f"Cost Explorer error: {e.response['Error']['Message']}")

    # ── Health check ───────────────────────────────────────────────

    async def health_check(self) -> HealthStatus:
        start = time.monotonic()
        try:
            async with self._session.client("sts") as sts:
                resp = await sts.get_caller_identity()
                latency = (time.monotonic() - start) * 1000
                return HealthStatus(
                    healthy=True,
                    latency_ms=round(latency, 1),
                    account_id=resp["Account"],
                    arn=resp["Arn"],
                    message="Connection healthy",
                )
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return HealthStatus(
                healthy=False,
                latency_ms=round(latency, 1),
                message=f"Health check failed: {str(e)}",
            )
