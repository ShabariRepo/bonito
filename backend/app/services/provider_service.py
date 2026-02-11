"""Provider service — real AWS integration, mock for Azure/GCP."""

import json
import random
import uuid
import logging
from datetime import date, datetime, timezone
from typing import List, Optional, Tuple

from app.core.vault import vault_client
from app.schemas.provider import ModelInfo, ProviderType
from app.services.providers.aws_bedrock import AWSBedrockProvider
from app.services.providers.azure_foundry import AzureFoundryProvider
from app.services.providers.gcp_vertex import GCPVertexProvider
from app.services.providers.openai_direct import OpenAIDirectProvider
from app.services.providers.anthropic_direct import AnthropicDirectProvider
from app.services.providers.base import CloudProvider as CloudProviderInterface

logger = logging.getLogger(__name__)

# ── Mock Model Catalogs (Azure/GCP only now) ────────────────────

AZURE_MODELS: List[ModelInfo] = [
    ModelInfo(id="az-1", name="GPT-4o", provider="azure", provider_model_id="gpt-4o", capabilities=["text", "vision", "code", "function_calling"], context_window=128000, pricing_tier="standard", input_price_per_1k=0.005, output_price_per_1k=0.015),
    ModelInfo(id="az-2", name="GPT-4o Mini", provider="azure", provider_model_id="gpt-4o-mini", capabilities=["text", "vision", "code", "function_calling"], context_window=128000, pricing_tier="economy", input_price_per_1k=0.00015, output_price_per_1k=0.0006),
    ModelInfo(id="az-3", name="GPT-4 Turbo", provider="azure", provider_model_id="gpt-4-turbo", capabilities=["text", "vision", "code", "function_calling"], context_window=128000, pricing_tier="premium", input_price_per_1k=0.01, output_price_per_1k=0.03),
    ModelInfo(id="az-4", name="o1-preview", provider="azure", provider_model_id="o1-preview", capabilities=["text", "reasoning", "code"], context_window=128000, pricing_tier="premium", input_price_per_1k=0.015, output_price_per_1k=0.06),
    ModelInfo(id="az-5", name="Phi-3 Medium 128K", provider="azure", provider_model_id="phi-3-medium-128k-instruct", capabilities=["text", "code"], context_window=128000, pricing_tier="economy", input_price_per_1k=0.0002, output_price_per_1k=0.0004),
    ModelInfo(id="az-6", name="text-embedding-3-large", provider="azure", provider_model_id="text-embedding-3-large", capabilities=["embeddings"], context_window=8191, pricing_tier="economy", input_price_per_1k=0.00013, output_price_per_1k=0.0),
    ModelInfo(id="az-7", name="DALL-E 3", provider="azure", provider_model_id="dall-e-3", capabilities=["image_generation"], context_window=0, pricing_tier="standard", input_price_per_1k=0.04, output_price_per_1k=0.0),
    ModelInfo(id="az-8", name="Whisper", provider="azure", provider_model_id="whisper", capabilities=["speech_to_text"], context_window=0, pricing_tier="economy", input_price_per_1k=0.006, output_price_per_1k=0.0),
]

GCP_MODELS: List[ModelInfo] = [
    ModelInfo(id="gcp-1", name="Gemini 1.5 Pro", provider="gcp", provider_model_id="gemini-1.5-pro-002", capabilities=["text", "vision", "code", "function_calling"], context_window=2000000, pricing_tier="standard", input_price_per_1k=0.00125, output_price_per_1k=0.005),
    ModelInfo(id="gcp-2", name="Gemini 1.5 Flash", provider="gcp", provider_model_id="gemini-1.5-flash-002", capabilities=["text", "vision", "code"], context_window=1000000, pricing_tier="economy", input_price_per_1k=0.000075, output_price_per_1k=0.0003),
    ModelInfo(id="gcp-3", name="Gemini Ultra", provider="gcp", provider_model_id="gemini-ultra", capabilities=["text", "vision", "code", "reasoning"], context_window=128000, pricing_tier="premium", input_price_per_1k=0.007, output_price_per_1k=0.021),
    ModelInfo(id="gcp-4", name="PaLM 2 for Text", provider="gcp", provider_model_id="text-bison@002", capabilities=["text"], context_window=8192, pricing_tier="economy", input_price_per_1k=0.00025, output_price_per_1k=0.0005),
    ModelInfo(id="gcp-5", name="Codey for Code Generation", provider="gcp", provider_model_id="code-bison@002", capabilities=["code"], context_window=6144, pricing_tier="economy", input_price_per_1k=0.00025, output_price_per_1k=0.0005),
    ModelInfo(id="gcp-6", name="Imagen 3", provider="gcp", provider_model_id="imagen-3.0-generate-002", capabilities=["image_generation"], context_window=0, pricing_tier="standard", input_price_per_1k=0.04, output_price_per_1k=0.0),
    ModelInfo(id="gcp-7", name="text-embedding-005", provider="gcp", provider_model_id="text-embedding-005", capabilities=["embeddings"], context_window=2048, pricing_tier="economy", input_price_per_1k=0.000025, output_price_per_1k=0.0),
]

OPENAI_MODELS: List[ModelInfo] = [
    ModelInfo(id="openai-1", name="GPT-4o", provider="openai", provider_model_id="gpt-4o", capabilities=["text", "vision", "code", "function_calling"], context_window=128000, pricing_tier="standard", input_price_per_1k=0.0025, output_price_per_1k=0.01),
    ModelInfo(id="openai-2", name="GPT-4o Mini", provider="openai", provider_model_id="gpt-4o-mini", capabilities=["text", "vision", "code", "function_calling"], context_window=128000, pricing_tier="economy", input_price_per_1k=0.00015, output_price_per_1k=0.0006),
    ModelInfo(id="openai-3", name="o1", provider="openai", provider_model_id="o1", capabilities=["text", "reasoning", "code"], context_window=200000, pricing_tier="premium", input_price_per_1k=0.015, output_price_per_1k=0.06),
    ModelInfo(id="openai-4", name="o3 Mini", provider="openai", provider_model_id="o3-mini", capabilities=["text", "reasoning", "code"], context_window=128000, pricing_tier="standard", input_price_per_1k=0.0011, output_price_per_1k=0.0044),
    ModelInfo(id="openai-5", name="GPT-3.5 Turbo", provider="openai", provider_model_id="gpt-3.5-turbo", capabilities=["text", "code", "function_calling"], context_window=16385, pricing_tier="economy", input_price_per_1k=0.0005, output_price_per_1k=0.0015),
]

ANTHROPIC_MODELS: List[ModelInfo] = [
    ModelInfo(id="anthropic-1", name="Claude 3.5 Sonnet", provider="anthropic", provider_model_id="claude-3-5-sonnet-20241022", capabilities=["text", "vision", "code", "function_calling"], context_window=200000, pricing_tier="standard", input_price_per_1k=0.003, output_price_per_1k=0.015),
    ModelInfo(id="anthropic-2", name="Claude 3.5 Haiku", provider="anthropic", provider_model_id="claude-3-5-haiku-20241022", capabilities=["text", "vision", "code"], context_window=200000, pricing_tier="economy", input_price_per_1k=0.0008, output_price_per_1k=0.004),
    ModelInfo(id="anthropic-3", name="Claude 3 Opus", provider="anthropic", provider_model_id="claude-3-opus-20240229", capabilities=["text", "vision", "code", "function_calling"], context_window=200000, pricing_tier="premium", input_price_per_1k=0.015, output_price_per_1k=0.075),
    ModelInfo(id="anthropic-4", name="Claude 3 Sonnet", provider="anthropic", provider_model_id="claude-3-sonnet-20240229", capabilities=["text", "vision", "code"], context_window=200000, pricing_tier="standard", input_price_per_1k=0.003, output_price_per_1k=0.015),
    ModelInfo(id="anthropic-5", name="Claude 3 Haiku", provider="anthropic", provider_model_id="claude-3-haiku-20240307", capabilities=["text", "vision", "code"], context_window=200000, pricing_tier="economy", input_price_per_1k=0.00025, output_price_per_1k=0.00125),
]

MOCK_CATALOG = {
    "azure": AZURE_MODELS,
    "gcp": GCP_MODELS,
    "openai": OPENAI_MODELS,
    "anthropic": ANTHROPIC_MODELS,
}

PROVIDER_NAMES = {
    "aws": "AWS Bedrock",
    "azure": "Azure OpenAI",
    "gcp": "GCP Vertex AI",
    "openai": "OpenAI Direct",
    "anthropic": "Anthropic Direct",
}

PROVIDER_REGIONS = {
    "aws": [
        "us-east-1", "us-west-2", "eu-west-1", "eu-west-3", "eu-central-1",
        "ap-northeast-1", "ap-southeast-1", "ap-southeast-2", "ap-south-1",
        "ca-central-1", "sa-east-1",
    ],
    "azure": ["East US", "West US 2", "West Europe", "Southeast Asia"],
    "gcp": ["us-central1", "us-east1", "europe-west1", "asia-east1"],
    "openai": ["Global"],
    "anthropic": ["Global"],
}


def get_provider_display_name(provider_type: str) -> str:
    return PROVIDER_NAMES.get(provider_type, provider_type)


def validate_credentials(provider_type: str, credentials: dict) -> Tuple[bool, str]:
    """Validate credential format (quick local check)."""
    if provider_type == "aws":
        required = ["access_key_id", "secret_access_key", "region"]
        for field in required:
            if field not in credentials or not credentials[field]:
                return False, f"Missing required field: {field}"
        if len(credentials["access_key_id"]) < 16:
            return False, "Access Key ID is too short"
        if len(credentials["secret_access_key"]) < 20:
            return False, "Secret Access Key is too short"
        if credentials["region"] not in PROVIDER_REGIONS["aws"]:
            return False, f"Unsupported region: {credentials['region']}"
    elif provider_type == "azure":
        for field in ["tenant_id", "client_id", "client_secret", "subscription_id"]:
            if field not in credentials or not credentials[field]:
                return False, f"Missing required field: {field}"
    elif provider_type == "gcp":
        for field in ["project_id", "service_account_json"]:
            if field not in credentials or not credentials[field]:
                return False, f"Missing required field: {field}"
    elif provider_type == "openai":
        if "api_key" not in credentials or not credentials["api_key"]:
            return False, "Missing required field: api_key"
        if len(credentials["api_key"]) < 20:
            return False, "API key is too short"
    elif provider_type == "anthropic":
        if "api_key" not in credentials or not credentials["api_key"]:
            return False, "Missing required field: api_key"
        if len(credentials["api_key"]) < 20:
            return False, "API key is too short"
    else:
        return False, f"Unsupported provider: {provider_type}"
    return True, ""


def extract_region(provider_type: str, credentials: dict) -> str:
    if provider_type == "aws":
        return credentials.get("region", "us-east-1")
    elif provider_type == "azure":
        return "East US"
    elif provider_type == "gcp":
        return "us-central1"
    elif provider_type == "openai":
        return "Global"
    elif provider_type == "anthropic":
        return "Global"
    return ""


async def get_aws_provider(provider_id: str) -> AWSBedrockProvider:
    """Create an AWSBedrockProvider from Vault-stored credentials."""
    vault_path = f"providers/{provider_id}"
    secrets = await vault_client.get_secrets(vault_path)
    if not secrets:
        raise RuntimeError("No credentials found for this provider")
    return AWSBedrockProvider(
        access_key_id=secrets["access_key_id"],
        secret_access_key=secrets["secret_access_key"],
        region=secrets.get("region", "us-east-1"),
    )


async def get_azure_provider(provider_id: str) -> AzureFoundryProvider:
    """Create an AzureFoundryProvider from Vault-stored credentials."""
    vault_path = f"providers/{provider_id}"
    secrets = await vault_client.get_secrets(vault_path)
    if not secrets:
        raise RuntimeError("No credentials found for this provider")
    return AzureFoundryProvider(
        tenant_id=secrets["tenant_id"],
        client_id=secrets["client_id"],
        client_secret=secrets["client_secret"],
        subscription_id=secrets["subscription_id"],
        resource_group=secrets.get("resource_group", ""),
        endpoint=secrets.get("endpoint", ""),
    )


async def get_gcp_provider(provider_id: str) -> GCPVertexProvider:
    """Create a GCPVertexProvider from Vault-stored credentials."""
    vault_path = f"providers/{provider_id}"
    secrets = await vault_client.get_secrets(vault_path)
    if not secrets:
        raise RuntimeError("No credentials found for this provider")
    return GCPVertexProvider(
        project_id=secrets["project_id"],
        service_account_json=secrets["service_account_json"],
        region=secrets.get("region", "us-central1"),
    )


async def get_openai_provider(provider_id: str) -> OpenAIDirectProvider:
    """Create an OpenAIDirectProvider from Vault-stored credentials."""
    vault_path = f"providers/{provider_id}"
    secrets = await vault_client.get_secrets(vault_path)
    if not secrets:
        raise RuntimeError("No credentials found for this provider")
    return OpenAIDirectProvider(
        api_key=secrets["api_key"],
        organization_id=secrets.get("organization_id"),
    )


async def get_anthropic_provider(provider_id: str) -> AnthropicDirectProvider:
    """Create an AnthropicDirectProvider from Vault-stored credentials."""
    vault_path = f"providers/{provider_id}"
    secrets = await vault_client.get_secrets(vault_path)
    if not secrets:
        raise RuntimeError("No credentials found for this provider")
    return AnthropicDirectProvider(
        api_key=secrets["api_key"],
    )


async def store_credentials_in_vault(provider_id: str, credentials: dict) -> str:
    """Store credentials in Vault, return vault path."""
    vault_path = f"providers/{provider_id}"
    await vault_client.put_secrets(vault_path, credentials)
    return vault_path


async def get_models_for_provider(provider_type: str, provider_id: str = None) -> list:
    """Get models — real integrations for all providers when credentials exist."""

    def _convert(models, provider_key):
        return [
            ModelInfo(
                id=f"{provider_key}-{i}",
                name=m.model_name,
                provider=provider_key,
                provider_model_id=m.model_id,
                capabilities=m.capabilities,
                context_window=m.context_window,
                pricing_tier=_pricing_tier(m.input_price_per_1m_tokens),
                input_price_per_1k=m.input_price_per_1m_tokens / 1000,
                output_price_per_1k=m.output_price_per_1m_tokens / 1000,
                status=m.status.lower() if m.status else "available",
            )
            for i, m in enumerate(models, 1)
        ]

    if provider_id:
        try:
            if provider_type == "aws":
                provider = await get_aws_provider(provider_id)
                return _convert(await provider.list_models(), "aws")
            elif provider_type == "azure":
                provider = await get_azure_provider(provider_id)
                return _convert(await provider.list_models(), "azure")
            elif provider_type == "gcp":
                provider = await get_gcp_provider(provider_id)
                return _convert(await provider.list_models(), "gcp")
            elif provider_type == "openai":
                provider = await get_openai_provider(provider_id)
                return _convert(await provider.list_models(), "openai")
            elif provider_type == "anthropic":
                provider = await get_anthropic_provider(provider_id)
                return _convert(await provider.list_models(), "anthropic")
        except Exception as e:
            logger.error(f"Failed to fetch real {provider_type} models: {e}")
            return MOCK_CATALOG.get(provider_type, [])

    return MOCK_CATALOG.get(provider_type, [])


def _pricing_tier(input_price_per_1m: float) -> str:
    if input_price_per_1m >= 10:
        return "premium"
    elif input_price_per_1m >= 1:
        return "standard"
    return "economy"


async def mock_verify_connection(provider_type: str) -> Tuple[bool, float]:
    """Mock verify for Azure/GCP."""
    import asyncio
    await asyncio.sleep(random.uniform(0.5, 1.5))
    latency = random.uniform(45, 200)
    success = random.random() < 0.9
    return success, round(latency, 1)
