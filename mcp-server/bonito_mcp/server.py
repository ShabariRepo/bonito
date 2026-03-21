"""Bonito MCP Server – exposes the Bonito AI Platform REST API as MCP tools."""

from __future__ import annotations

import json
import sys
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP

from bonito_mcp.client import BonitoClient

# ── Lifespan: initialise / tear-down the HTTP client ─────────────────


@asynccontextmanager
async def lifespan(server: FastMCP):
    """Create a shared BonitoClient for the server's lifetime."""
    client = BonitoClient()
    try:
        yield {"client": client}
    finally:
        await client.close()


# ── Server instance ──────────────────────────────────────────────────

app = FastMCP(
    "Bonito",
    instructions=(
        "Bonito MCP Server – manage multi-provider AI infrastructure. "
        "Connect cloud AI providers, deploy agents, route requests through "
        "the unified gateway, and monitor costs."
    ),
    lifespan=lifespan,
)


def _client(ctx) -> BonitoClient:
    """Retrieve the BonitoClient from the lifespan context."""
    return ctx.request_context.lifespan_context["client"]


def _json(data: Any) -> str:
    """Pretty-print JSON for tool responses."""
    return json.dumps(data, indent=2, default=str)


# ═══════════════════════════════════════════════════════════════════════
# Provider Management
# ═══════════════════════════════════════════════════════════════════════


@app.tool()
async def list_providers(ctx) -> str:
    """List all connected AI providers (AWS Bedrock, Azure OpenAI, GCP Vertex, OpenAI, Anthropic, Groq)."""
    result = await _client(ctx).list_providers()
    return _json(result)


@app.tool()
async def connect_provider(
    provider_type: str,
    credentials: str,
    ctx=None,
) -> str:
    """Connect a new AI provider.

    Args:
        provider_type: Provider type – one of: aws_bedrock, azure_openai, gcp_vertex, openai, anthropic, groq
        credentials: JSON string with provider-specific credentials (e.g. API keys, region, project ID)
    """
    creds = json.loads(credentials) if isinstance(credentials, str) else credentials
    result = await _client(ctx).connect_provider(provider_type, creds)
    return _json(result)


@app.tool()
async def verify_provider(provider_id: str, ctx=None) -> str:
    """Verify connectivity and credentials for a connected provider.

    Args:
        provider_id: The provider ID to verify
    """
    result = await _client(ctx).verify_provider(provider_id)
    return _json(result)


# ═══════════════════════════════════════════════════════════════════════
# Model Management
# ═══════════════════════════════════════════════════════════════════════


@app.tool()
async def list_models(
    provider: str | None = None,
    capability: str | None = None,
    active: bool | None = None,
    ctx=None,
) -> str:
    """List available models across all providers with optional filters.

    Args:
        provider: Filter by provider (e.g. openai, anthropic, aws_bedrock)
        capability: Filter by capability (e.g. chat, embedding, image)
        active: Filter by activation status
    """
    result = await _client(ctx).list_models(provider=provider, capability=capability, active=active)
    return _json(result)


@app.tool()
async def sync_models(ctx) -> str:
    """Sync available models from all connected providers. Discovers newly available models."""
    result = await _client(ctx).sync_models()
    return _json(result)


@app.tool()
async def activate_model(model_id: str, ctx=None) -> str:
    """Activate a model to make it available through the gateway.

    Args:
        model_id: The model ID to activate
    """
    result = await _client(ctx).activate_model(model_id)
    return _json(result)


# ═══════════════════════════════════════════════════════════════════════
# Gateway
# ═══════════════════════════════════════════════════════════════════════


@app.tool()
async def chat_completion(
    model: str,
    messages: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
    ctx=None,
) -> str:
    """Send a chat completion request through the Bonito gateway (OpenAI-compatible).

    Args:
        model: Model identifier (e.g. gpt-4o, claude-sonnet-4-20250514, or a Bonito model alias)
        messages: JSON array of message objects, e.g. [{"role":"user","content":"Hello"}]
        temperature: Sampling temperature (0-2)
        max_tokens: Maximum tokens to generate
    """
    msgs = json.loads(messages) if isinstance(messages, str) else messages
    kwargs: dict[str, Any] = {}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    result = await _client(ctx).chat_completion(model, msgs, **kwargs)
    return _json(result)


@app.tool()
async def list_gateway_keys(ctx) -> str:
    """List all API keys for the Bonito gateway."""
    result = await _client(ctx).list_gateway_keys()
    return _json(result)


@app.tool()
async def create_gateway_key(name: str | None = None, ctx=None) -> str:
    """Create a new gateway API key.

    Args:
        name: Optional friendly name for the key
    """
    result = await _client(ctx).create_gateway_key(name=name)
    return _json(result)


@app.tool()
async def gateway_usage(period: str | None = None, ctx=None) -> str:
    """Get gateway usage statistics.

    Args:
        period: Time period – e.g. 24h, 7d, 30d
    """
    result = await _client(ctx).gateway_usage(period=period)
    return _json(result)


# ═══════════════════════════════════════════════════════════════════════
# Agent Management
# ═══════════════════════════════════════════════════════════════════════


@app.tool()
async def list_agents(project_id: str, ctx=None) -> str:
    """List all agents in a project.

    Args:
        project_id: The project ID
    """
    result = await _client(ctx).list_agents(project_id)
    return _json(result)


@app.tool()
async def create_agent(
    project_id: str,
    name: str,
    model: str,
    system_prompt: str | None = None,
    agent_type: str = "bonbon",
    ctx=None,
) -> str:
    """Create a new agent (BonBon or Bonobot).

    Args:
        project_id: The project ID to create the agent in
        name: Agent name
        model: Model to use (e.g. gpt-4o, claude-sonnet-4-20250514)
        system_prompt: Optional system prompt for the agent
        agent_type: Agent type – bonbon (single model) or bonobot (multi-model orchestrator)
    """
    config: dict[str, Any] = {
        "name": name,
        "model": model,
        "type": agent_type,
    }
    if system_prompt:
        config["system_prompt"] = system_prompt
    result = await _client(ctx).create_agent(project_id, config)
    return _json(result)


@app.tool()
async def execute_agent(agent_id: str, message: str, ctx=None) -> str:
    """Execute an agent with a message.

    Args:
        agent_id: The agent ID to execute
        message: The message to send to the agent
    """
    result = await _client(ctx).execute_agent(agent_id, message)
    return _json(result)


@app.tool()
async def get_agent(agent_id: str, ctx=None) -> str:
    """Get details of a specific agent.

    Args:
        agent_id: The agent ID
    """
    result = await _client(ctx).get_agent(agent_id)
    return _json(result)


# ═══════════════════════════════════════════════════════════════════════
# Knowledge Bases
# ═══════════════════════════════════════════════════════════════════════


@app.tool()
async def list_knowledge_bases(ctx) -> str:
    """List all knowledge bases."""
    result = await _client(ctx).list_knowledge_bases()
    return _json(result)


@app.tool()
async def create_knowledge_base(name: str, description: str | None = None, ctx=None) -> str:
    """Create a new knowledge base.

    Args:
        name: Name for the knowledge base
        description: Optional description
    """
    result = await _client(ctx).create_knowledge_base(name, description=description)
    return _json(result)


# ═══════════════════════════════════════════════════════════════════════
# Cost & Observability
# ═══════════════════════════════════════════════════════════════════════


@app.tool()
async def get_costs(provider_id: str, period: str | None = None, ctx=None) -> str:
    """Get cost breakdown for a specific provider.

    Args:
        provider_id: The provider ID
        period: Time period – e.g. 24h, 7d, 30d
    """
    result = await _client(ctx).get_costs(provider_id, period=period)
    return _json(result)


@app.tool()
async def get_gateway_logs(
    limit: int | None = None,
    offset: int | None = None,
    model: str | None = None,
    ctx=None,
) -> str:
    """Get gateway request logs for observability.

    Args:
        limit: Maximum number of log entries to return
        offset: Offset for pagination
        model: Filter logs by model name
    """
    result = await _client(ctx).get_gateway_logs(limit=limit, offset=offset, model=model)
    return _json(result)


# ═══════════════════════════════════════════════════════════════════════
# CLI entry point
# ═══════════════════════════════════════════════════════════════════════


def main() -> None:
    """Run the Bonito MCP server."""
    import argparse

    parser = argparse.ArgumentParser(description="Bonito MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport type (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for SSE transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for SSE transport (default: 8080)",
    )
    args = parser.parse_args()

    if args.transport == "sse":
        app.settings.host = args.host
        app.settings.port = args.port
        app.run(transport="sse")
    else:
        app.run(transport="stdio")


if __name__ == "__main__":
    main()
