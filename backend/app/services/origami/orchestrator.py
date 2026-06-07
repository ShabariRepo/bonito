"""Origami orchestrator — the chat-and-tool-call loop.

Phase 1 skeleton. Origami is a CUSTOMER of Bonito's own gateway — it POSTs
to `/v1/chat/completions` with a `bn-` system key, just like any external
customer would. No anthropic SDK, no LiteLLM in this code path (LiteLLM
runs inside the gateway itself, which is exactly the dogfood story we want).

Dependencies in this module: stdlib + httpx (already in backend requirements).

TODO before Phase 1 ships:
- Mint a permanent system-org `bn-` key via Vault, replace ORIGAMI_GATEWAY_KEY
  env var (Phase 1.5).
- Add streaming via `stream=True` (emit message_token events).
- Wire bonito-knowledge KB retrieval for RAG context injection.
- Add Memwright session memory for cross-turn context.
- Cache control on static prompt parts (system prompt, tool schemas).
- Audit log writes per tool call (migration 046).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.origami.tools.base import (
    TOOL_REGISTRY,
    sanitize_params,
)
# Tools register themselves at import time
from app.services.origami import tools as _tools  # noqa: F401

logger = logging.getLogger(__name__)

# Gateway target. Default points at the local backend for dev; in prod
# this becomes https://api.getbonito.com. Override with BONITO_GATEWAY_URL.
DEFAULT_GATEWAY_URL = os.getenv("BONITO_GATEWAY_URL", "http://localhost:8001")

# Model name as the gateway exposes it. Sonnet 4.5 / 4.6 are routed
# through the customer's connected provider (Anthropic, Bedrock, Vertex).
ORIGAMI_MODEL = "claude-sonnet-4-5"
ORIGAMI_MAX_TOKENS = 2048
ORIGAMI_MAX_TOOL_ITERATIONS = 5
ORIGAMI_HTTP_TIMEOUT = 60.0  # seconds


# ────────────────────────── Event types ──────────────────────────


@dataclass
class OrigamiEvent:
    """Discrete event the orchestrator emits during a turn."""

    type: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_sse(self) -> str:
        data = json.dumps({"type": self.type, **self.payload})
        return f"data: {data}\n\n"


# ────────────────────────── System prompt ──────────────────────────


SYSTEM_PROMPT = """You are Origami, the in-app conversational interface for Bonito — \
an enterprise AI operations platform.

Your job is to help users plan and deploy AI agents, knowledge bases, and \
related infrastructure on Bonito. You are NOT a general coding assistant; you \
work strictly within the Bonito platform.

Style:
- Direct and concise. No fluff.
- Friendly but not chirpy. Treat the user as a peer who is building real \
infrastructure.
- Default to short responses (2-4 sentences). Longer only when explaining a \
multi-step plan.
- Never reveal internal Bonito implementation details unless directly relevant.

When you need information about the user's organization, use the `list_org_state` \
tool. When they ask about usage or limits, use `view_usage`.

For now (Phase 1 skeleton), you can ONLY answer questions and use the read-only \
tools above. You cannot yet create resources, mutate state, or deploy anything. \
If a user asks for a build, acknowledge it and tell them the plan-card / Deploy \
flow is coming in Phase 2."""


# ────────────────────────── Gateway client ──────────────────────────


def _tool_to_openai_schema(tool_cls) -> dict[str, Any]:
    """Convert an OrigamiTool subclass to OpenAI-style function tool schema."""
    return {
        "type": "function",
        "function": {
            "name": tool_cls.name,
            "description": tool_cls.description,
            "parameters": tool_cls.input_schema,
        },
    }


def _get_gateway_key() -> str:
    """Return the bn- system key Origami uses to call its own gateway.

    Phase 1: read from ORIGAMI_GATEWAY_KEY env var.
    Phase 1.5: mint a permanent system-org bn- via Vault, read from there.
    """
    key = os.getenv("ORIGAMI_GATEWAY_KEY")
    if not key:
        raise RuntimeError(
            "ORIGAMI_GATEWAY_KEY env var not set. "
            "Origami needs a bn- system key to call its own gateway. "
            "Generate one from any active Bonito org for dev; production "
            "uses a system-org key from Vault (TODO Phase 1.5)."
        )
    if not key.startswith("bn-"):
        raise RuntimeError("ORIGAMI_GATEWAY_KEY must start with 'bn-'.")
    return key


async def _call_gateway(
    *,
    system: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> dict[str, Any]:
    """Non-streaming chat completion via Bonito's own gateway.

    POSTs to {BONITO_GATEWAY_URL}/v1/chat/completions exactly the way an
    external customer would. The gateway routes to the connected provider
    (Anthropic direct, Bedrock, Vertex, etc.) based on org config.
    """
    api_key = _get_gateway_key()
    url = f"{DEFAULT_GATEWAY_URL.rstrip('/')}/v1/chat/completions"

    full_messages = [{"role": "system", "content": system}] + messages

    body: dict[str, Any] = {
        "model": ORIGAMI_MODEL,
        "max_tokens": ORIGAMI_MAX_TOKENS,
        "messages": full_messages,
    }
    if tools:
        body["tools"] = tools

    async with httpx.AsyncClient(timeout=ORIGAMI_HTTP_TIMEOUT) as client:
        resp = await client.post(
            url,
            json=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        if resp.status_code >= 400:
            raise RuntimeError(
                f"Gateway returned {resp.status_code}: {resp.text[:500]}"
            )
        return resp.json()


# ────────────────────────── Orchestrator entry point ──────────────────────────


async def run_origami_turn(
    *,
    user: User,
    message: str,
    conversation_id: Optional[str],
    db: AsyncSession,
) -> AsyncIterator[OrigamiEvent]:
    """Run one Origami turn: gateway call → tool dispatch loop → final response.

    Yields OrigamiEvent objects. Caller (FastAPI route) converts to SSE.

    SECURITY: org_id is read from user.org_id (from JWT auth). org_id is
    injected into every tool execute() call from this server-side value,
    never from the model's tool_call arguments.
    """
    org_id = user.org_id

    yield OrigamiEvent("turn_started", {"conversation_id": conversation_id})

    messages: list[dict[str, Any]] = [
        {"role": "user", "content": message},
    ]

    tools_for_model = [
        _tool_to_openai_schema(cls) for cls in TOOL_REGISTRY.values()
    ]

    for iteration in range(ORIGAMI_MAX_TOOL_ITERATIONS):
        try:
            response = await _call_gateway(
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=tools_for_model,
            )
        except Exception as e:
            logger.exception("Origami gateway call failed (iteration %d)", iteration)
            yield OrigamiEvent("error", {
                "code": "gateway_call_failed",
                "message": str(e),
                "iteration": iteration,
            })
            return

        # OpenAI-format response (Bonito gateway emits this shape)
        choice = (response.get("choices") or [{}])[0]
        msg = choice.get("message", {})
        content = msg.get("content") or ""
        tool_calls = msg.get("tool_calls") or []
        finish_reason = choice.get("finish_reason")

        if content:
            yield OrigamiEvent("message_complete", {"text": content})

        if not tool_calls:
            yield OrigamiEvent("done", {
                "finish_reason": finish_reason,
                "iteration": iteration,
            })
            return

        # Build assistant turn that includes the tool calls (needed for next message validity)
        assistant_turn: dict[str, Any] = {
            "role": "assistant",
            "content": content or None,
            "tool_calls": tool_calls,
        }
        messages.append(assistant_turn)

        for tc in tool_calls:
            tc_id = tc.get("id", "")
            fn = tc.get("function", {})
            tool_name = fn.get("name", "")
            raw_args_str = fn.get("arguments") or "{}"

            try:
                raw_params = json.loads(raw_args_str)
            except json.JSONDecodeError:
                raw_params = {}

            params = sanitize_params(raw_params)  # ← strips org_id

            tool_cls = TOOL_REGISTRY.get(tool_name)
            if not tool_cls:
                yield OrigamiEvent("tool_failed", {
                    "tool_name": tool_name,
                    "tool_call_id": tc_id,
                    "error": "unknown_tool",
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": json.dumps({"error": f"Tool '{tool_name}' not registered."}),
                })
                continue

            yield OrigamiEvent("tool_started", {
                "tool_name": tool_name,
                "tool_call_id": tc_id,
            })

            try:
                tool_instance = tool_cls()
                result = await tool_instance.execute(
                    org_id=org_id,
                    user=user,
                    params=params,
                    db=db,
                )
                yield OrigamiEvent("tool_completed", {
                    "tool_name": tool_name,
                    "tool_call_id": tc_id,
                    "result_summary": _summarize_result(result),
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": json.dumps(result),
                })
            except Exception as e:
                logger.exception("Tool %s failed", tool_name)
                yield OrigamiEvent("tool_failed", {
                    "tool_name": tool_name,
                    "tool_call_id": tc_id,
                    "error": str(e),
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": json.dumps({"error": str(e)}),
                })

    yield OrigamiEvent("error", {
        "code": "max_iterations",
        "message": f"Tool loop exceeded {ORIGAMI_MAX_TOOL_ITERATIONS} iterations",
    })


def _summarize_result(result: dict[str, Any]) -> dict[str, Any]:
    """Compact summary of a tool result for SSE events."""
    if "counts" in result:
        return {"counts": result["counts"], "tier": result.get("tier")}
    if "gateway_requests" in result:
        return {
            "tier": result.get("tier"),
            "percent_used": result["gateway_requests"].get("percent_used"),
        }
    return {"keys": list(result.keys())[:10]}
