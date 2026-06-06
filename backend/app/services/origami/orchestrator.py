"""Origami orchestrator — the chat-and-tool-call loop.

Phase 1 skeleton: non-streaming Anthropic call, tool dispatch loop, SSE-style
event emission. Emits OrigamiEvent objects that the route layer converts to
SSE wire format.

TODO before Phase 1 ships:
- Route LLM calls through Bonito gateway (https://api.getbonito.com/v1/chat/completions)
  instead of direct Anthropic SDK. Currently uses ORIGAMI_ANTHROPIC_KEY env var
  for skeleton testing. The dogfood story requires gateway routing.
- Switch to streaming once skeleton is proven (emit message_token events).
- Wire bonito-knowledge KB retrieval for RAG context injection.
- Add Memwright session memory for cross-turn context.
- Cache control on static prompt parts (system prompt, tool schemas).
- Audit log writes per tool call (Phase 1 migration 046).
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.origami.tools.base import (
    TOOL_REGISTRY,
    OrigamiTool,
    sanitize_params,
)
# Tools register themselves at import time
from app.services.origami import tools as _tools  # noqa: F401

logger = logging.getLogger(__name__)

ORIGAMI_MODEL = "claude-sonnet-4-6"
ORIGAMI_MAX_TOKENS = 2048
ORIGAMI_MAX_TOOL_ITERATIONS = 5  # safety against infinite tool loops


# ────────────────────────── Event types ──────────────────────────


@dataclass
class OrigamiEvent:
    """Discrete event the orchestrator emits during a turn."""

    type: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_sse(self) -> str:
        """Convert to SSE wire format."""
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


# ────────────────────────── LLM client ──────────────────────────


async def _call_anthropic(
    *,
    system: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> dict[str, Any]:
    """Single (non-streaming) call to Claude.

    TODO: replace with httpx call to https://api.getbonito.com/v1/chat/completions
    using a system-org bn- key once that org is provisioned. For the skeleton
    we hit Anthropic directly via the SDK so we can test the loop.
    """
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError(
            "anthropic SDK not installed. Add to requirements: pip install anthropic"
        ) from e

    api_key = os.getenv("ORIGAMI_ANTHROPIC_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Set ORIGAMI_ANTHROPIC_KEY (or ANTHROPIC_API_KEY) env var. "
            "Phase 1.5 will route through Bonito gateway instead."
        )

    client = anthropic.AsyncAnthropic(api_key=api_key)

    kwargs: dict[str, Any] = {
        "model": ORIGAMI_MODEL,
        "max_tokens": ORIGAMI_MAX_TOKENS,
        "system": system,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools

    response = await client.messages.create(**kwargs)
    return response.model_dump()


# ────────────────────────── Orchestrator entry point ──────────────────────────


async def run_origami_turn(
    *,
    user: User,
    message: str,
    conversation_id: Optional[str],
    db: AsyncSession,
) -> AsyncIterator[OrigamiEvent]:
    """Run one Origami turn: LLM call → tool dispatch loop → final response.

    Yields OrigamiEvent objects. Caller (FastAPI route) converts to SSE.

    SECURITY: org_id is read from user.org_id (which comes from JWT auth).
    org_id is injected into every tool execute() call from this server-side
    value, never from the model's tool_use params. The framework's
    sanitize_params strips org_id from incoming params as a defense-in-depth.
    """
    org_id = user.org_id

    yield OrigamiEvent("turn_started", {"conversation_id": conversation_id})

    # Build initial messages (skeleton: no history yet — wire conversation
    # store + Memwright in next iteration)
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": message},
    ]

    tools_for_model = [
        cls.to_anthropic_schema() for cls in TOOL_REGISTRY.values()
    ]

    for iteration in range(ORIGAMI_MAX_TOOL_ITERATIONS):
        try:
            response = await _call_anthropic(
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=tools_for_model,
            )
        except Exception as e:
            logger.exception("Origami LLM call failed (iteration %d)", iteration)
            yield OrigamiEvent("error", {
                "code": "llm_call_failed",
                "message": str(e),
                "iteration": iteration,
            })
            return

        # Anthropic returns content as a list of blocks
        content_blocks = response.get("content", [])
        stop_reason = response.get("stop_reason")

        # Detect tool_use blocks
        tool_uses = [b for b in content_blocks if b.get("type") == "tool_use"]
        text_blocks = [b for b in content_blocks if b.get("type") == "text"]

        # Emit any text response immediately
        for tb in text_blocks:
            text = tb.get("text") or ""
            if text:
                yield OrigamiEvent("message_complete", {"text": text})

        # If no tool calls, we're done with this turn
        if not tool_uses:
            yield OrigamiEvent("done", {
                "stop_reason": stop_reason,
                "iteration": iteration,
            })
            return

        # Run each requested tool
        tool_results = []
        for tu in tool_uses:
            tool_name = tu.get("name", "")
            tool_use_id = tu.get("id", "")
            raw_params = tu.get("input") or {}
            params = sanitize_params(raw_params)  # ← strips org_id if model snuck it in

            tool_cls = TOOL_REGISTRY.get(tool_name)
            if not tool_cls:
                yield OrigamiEvent("tool_failed", {
                    "tool_name": tool_name,
                    "error": "unknown_tool",
                })
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "is_error": True,
                    "content": f"Tool '{tool_name}' is not registered.",
                })
                continue

            yield OrigamiEvent("tool_started", {
                "tool_name": tool_name,
                "tool_use_id": tool_use_id,
            })

            try:
                tool_instance = tool_cls()
                result = await tool_instance.execute(
                    org_id=org_id,  # ← FROM SERVER, never from model
                    user=user,
                    params=params,
                    db=db,
                )
                yield OrigamiEvent("tool_completed", {
                    "tool_name": tool_name,
                    "tool_use_id": tool_use_id,
                    "result_summary": _summarize_result(result),
                })
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": json.dumps(result),
                })
            except Exception as e:
                logger.exception("Tool %s failed", tool_name)
                yield OrigamiEvent("tool_failed", {
                    "tool_name": tool_name,
                    "tool_use_id": tool_use_id,
                    "error": str(e),
                })
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "is_error": True,
                    "content": f"Tool error: {e}",
                })

        # Append the assistant's tool_use turn and the user tool_result turn
        messages.append({"role": "assistant", "content": content_blocks})
        messages.append({"role": "user", "content": tool_results})
        # Loop continues — model gets to see tool results

    # If we hit max iterations
    yield OrigamiEvent("error", {
        "code": "max_iterations",
        "message": f"Tool loop exceeded {ORIGAMI_MAX_TOOL_ITERATIONS} iterations",
    })


def _summarize_result(result: dict[str, Any]) -> dict[str, Any]:
    """Return a compact summary of a tool result for SSE events.

    Avoids streaming the full payload to the client (it'll be in the next
    LLM call's input). Just enough for the activity log to render.
    """
    if "counts" in result:  # list_org_state shape
        return {"counts": result["counts"], "tier": result.get("tier")}
    if "gateway_requests" in result:  # view_usage shape
        return {
            "tier": result.get("tier"),
            "percent_used": result["gateway_requests"].get("percent_used"),
        }
    # Fallback: just the keys, no values
    return {"keys": list(result.keys())[:10]}
