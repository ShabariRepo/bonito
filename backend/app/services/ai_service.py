"""AI service — real LLM-powered chat and command parsing.

Routes queries to connected cloud providers. Falls back to intent
parsing when no provider is available.
"""

import json
import logging
import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud_provider import CloudProvider
from app.services.provider_service import (
    get_aws_provider,
    get_azure_provider,
    get_gcp_provider,
)

logger = logging.getLogger(__name__)

# System prompt for the AI assistant
SYSTEM_PROMPT = """You are Bonito AI, the intelligent assistant for the Bonito multi-cloud AI control plane.

You help enterprise teams manage their AI workloads across AWS Bedrock, Azure AI Foundry, and Google Vertex AI.

Your capabilities:
- Deploy and manage models across cloud providers
- Query cost data and spending trends
- Search and compare models across providers
- Create governance policies and compliance rules
- Manage team access and roles

When responding:
- Be concise and actionable
- Use markdown formatting for clarity
- When suggesting actions, be specific about which provider and model
- Include cost estimates when relevant
- If you need more info, ask one clear question

You have access to the user's connected providers and their real model catalogs."""


async def chat_with_llm(
    message: str,
    db: AsyncSession,
    conversation_history: list[dict] = None,
) -> dict:
    """Send a message to a real LLM via a connected provider.
    
    Priority: AWS (Claude) > Azure (GPT) > GCP (Gemini)
    Falls back to intent parsing if no provider available.
    """
    # Get connected providers
    result = await db.execute(
        select(CloudProvider).where(CloudProvider.status == "active")
    )
    providers = result.scalars().all()

    if not providers:
        return _fallback_parse(message)

    # Sort by preference: aws first (Claude), then azure (GPT), then gcp (Gemini)
    priority = {"aws": 0, "azure": 1, "gcp": 2}
    providers_sorted = sorted(providers, key=lambda p: priority.get(p.provider_type, 99))

    # Try each provider
    for provider in providers_sorted:
        try:
            response = await _invoke_provider(provider, message, conversation_history)
            if response:
                return {
                    "intent": "ai_response",
                    "confidence": 1.0,
                    "message": response["text"],
                    "provider": provider.provider_type,
                    "model": response.get("model", ""),
                    "tokens": {
                        "input": response.get("input_tokens", 0),
                        "output": response.get("output_tokens", 0),
                    },
                    "cost": response.get("cost", 0.0),
                    "latency_ms": response.get("latency_ms", 0),
                    # Parse any actions from the response
                    "actions": _extract_actions(response["text"]),
                }
        except Exception as e:
            logger.warning(f"Provider {provider.provider_type} failed: {e}")
            continue

    # All providers failed
    return _fallback_parse(message)


async def _invoke_provider(
    provider: CloudProvider,
    message: str,
    history: list[dict] = None,
) -> Optional[dict]:
    """Invoke a specific provider's model."""
    provider_id = str(provider.id)

    if provider.provider_type == "aws":
        aws = await get_aws_provider(provider_id)
        # Prefer Claude 3.5 Sonnet, fallback to any available Claude
        models = await aws.list_models()
        model_id = _pick_best_model(models, ["anthropic.claude-3-5-sonnet", "anthropic.claude-3-sonnet", "anthropic.claude-3-haiku"])
        if not model_id:
            return None

        prompt = _build_prompt(message, history)
        result = await aws.invoke_model(model_id=model_id, prompt=prompt, max_tokens=2048, temperature=0.3)
        return {
            "text": result.response_text,
            "model": model_id,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "cost": result.estimated_cost,
            "latency_ms": result.latency_ms,
        }

    elif provider.provider_type == "azure":
        azure = await get_azure_provider(provider_id)
        models = await azure.list_models()
        model_id = _pick_best_model(models, ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"])
        if not model_id:
            return None

        prompt = _build_prompt(message, history)
        result = await azure.invoke_model(model_id=model_id, prompt=prompt, max_tokens=2048, temperature=0.3)
        return {
            "text": result.response_text,
            "model": model_id,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "cost": result.estimated_cost,
            "latency_ms": result.latency_ms,
        }

    elif provider.provider_type == "gcp":
        gcp = await get_gcp_provider(provider_id)
        models = await gcp.list_models()
        model_id = _pick_best_model(models, ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"])
        if not model_id:
            return None

        prompt = _build_prompt(message, history)
        result = await gcp.invoke_model(model_id=model_id, prompt=prompt, max_tokens=2048, temperature=0.3)
        return {
            "text": result.response_text,
            "model": model_id,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "cost": result.estimated_cost,
            "latency_ms": result.latency_ms,
        }

    return None


def _pick_best_model(models, preferences: list[str]) -> Optional[str]:
    """Pick the best available model from preferences."""
    model_ids = {m.model_id for m in models}
    # Exact match first
    for pref in preferences:
        for mid in model_ids:
            if pref in mid:
                return mid
    # Any text model as fallback
    for m in models:
        if "text" in (m.capabilities if hasattr(m, 'capabilities') else []):
            return m.model_id
    return models[0].model_id if models else None


def _build_prompt(message: str, history: list[dict] = None) -> str:
    """Build prompt with system context and conversation history."""
    parts = [SYSTEM_PROMPT, ""]
    if history:
        for h in history[-10:]:  # Last 10 messages
            role = h.get("role", "user")
            parts.append(f"{role.capitalize()}: {h['content']}")
        parts.append("")
    parts.append(f"User: {message}")
    parts.append("Assistant:")
    return "\n".join(parts)


def _extract_actions(text: str) -> list[dict]:
    """Extract actionable items from AI response."""
    actions = []
    # Look for navigation hints
    if re.search(r"(cost|spend|budget)", text.lower()):
        actions.append({"type": "navigate", "path": "/costs"})
    if re.search(r"(deploy|provision)", text.lower()):
        actions.append({"type": "navigate", "path": "/providers"})
    if re.search(r"(model|compare)", text.lower()):
        actions.append({"type": "navigate", "path": "/models"})
    if re.search(r"(policy|compliance|governance)", text.lower()):
        actions.append({"type": "navigate", "path": "/compliance"})
    return actions


# ── Fallback intent parser (no LLM available) ─────────────────


def parse_intent(message: str) -> dict:
    """Fallback intent parser when no LLM provider is connected."""
    return _fallback_parse(message)


def _fallback_parse(message: str) -> dict:
    msg = message.lower().strip()

    if re.search(r"deploy\s+(.+?)\s+on\s+(\w+)", msg):
        m = re.search(r"deploy\s+(.+?)\s+on\s+(\w+)", msg)
        return {
            "intent": "deploy",
            "confidence": 0.92,
            "message": f"I'll help you deploy **{m.group(1).strip()}** on **{m.group(2).strip().upper()}**.",
            "action": {"type": "deployment", "model": m.group(1).strip(), "provider": m.group(2).strip()},
            "follow_up": "Connect a cloud provider first to enable real deployments.",
        }

    if any(w in msg for w in ["spend", "cost", "budget", "expensive", "bill"]):
        return {
            "intent": "cost_query",
            "confidence": 0.95,
            "message": "Connect a cloud provider to see real cost data.",
            "action": {"type": "navigate", "path": "/costs"},
        }

    if any(w in msg for w in ["show", "find", "list", "search"]) and "model" in msg:
        return {
            "intent": "model_search",
            "confidence": 0.88,
            "message": "Connect a cloud provider to browse real model catalogs.",
            "action": {"type": "navigate", "path": "/models"},
        }

    return {
        "intent": "general",
        "confidence": 0.5,
        "message": "I can help you manage AI workloads across clouds. Connect a provider to get started!",
        "suggestions": [
            "Deploy a model (e.g., 'deploy claude 3.5 on aws')",
            "Check costs (e.g., 'how much did we spend last month')",
            "Search models (e.g., 'show me all gpt models')",
        ],
    }
