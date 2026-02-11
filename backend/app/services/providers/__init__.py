"""Cloud provider integrations."""

from app.services.providers.base import CloudProvider

__all__ = ["CloudProvider"]


def get_aws_bedrock_provider_class():
    from app.services.providers.aws_bedrock import AWSBedrockProvider
    return AWSBedrockProvider


def get_azure_foundry_provider_class():
    from app.services.providers.azure_foundry import AzureFoundryProvider
    return AzureFoundryProvider


def get_gcp_vertex_provider_class():
    from app.services.providers.gcp_vertex import GCPVertexProvider
    return GCPVertexProvider


def get_openai_direct_provider_class():
    from app.services.providers.openai_direct import OpenAIDirectProvider
    return OpenAIDirectProvider


def get_anthropic_direct_provider_class():
    from app.services.providers.anthropic_direct import AnthropicDirectProvider
    return AnthropicDirectProvider
