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
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.origami.tools.base import (
    TOOL_REGISTRY,
    sanitize_params,
)
from app.services.origami import metering
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

# Sonnet 4.5 / 4.6 published pricing — used for our internal cost estimate when
# the gateway doesn't echo a cost in the response. Source: Anthropic pricing
# page. Update if pricing shifts.
SONNET_INPUT_COST_PER_M = 3.00   # USD per 1M input tokens
SONNET_OUTPUT_COST_PER_M = 15.00  # USD per 1M output tokens


def _estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    """Rough cost estimate for an Origami turn (Sonnet-class pricing)."""
    return (
        (input_tokens / 1_000_000) * SONNET_INPUT_COST_PER_M
        + (output_tokens / 1_000_000) * SONNET_OUTPUT_COST_PER_M
    )


async def _get_user_tier(db: AsyncSession, org_id: uuid.UUID) -> str:
    """Live-read the user's tier. Defaults to 'free' on any failure."""
    try:
        from app.services.feature_gate import feature_gate
        subscription = await feature_gate.get_organization_subscription(db, str(org_id))
        tier_enum = subscription["tier"]
        return tier_enum.value if hasattr(tier_enum, "value") else str(tier_enum)
    except Exception:
        return "free"


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
    customer_org_id: Optional[uuid.UUID] = None,
    customer_user_id: Optional[uuid.UUID] = None,
) -> dict[str, Any]:
    """Non-streaming chat completion via Bonito's own gateway.

    POSTs to {BONITO_GATEWAY_URL}/v1/chat/completions exactly the way an
    external customer would. The bn- key used is intentionally a SYSTEM
    key (cat.shabari), so the LLM cost lands on cat.shabari as Bonito's
    COGS. Customer billing happens at the turn level via
    origami_turn_log, not gateway_requests.

    The OpenAI-standard `user` field carries the customer's identity so
    cat.shabari's gateway dashboard can break down Origami COGS by which
    customer triggered each call (lands in gateway_requests.team_id).
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

    # Tag the request with customer identity so cat.shabari's gateway
    # logs can be filtered to "Origami COGS attributed to customer X".
    if customer_org_id:
        if customer_user_id:
            body["user"] = f"origami:org:{customer_org_id}:user:{customer_user_id}"
        else:
            body["user"] = f"origami:org:{customer_org_id}"

    async with httpx.AsyncClient(timeout=ORIGAMI_HTTP_TIMEOUT) as client:
        resp = await client.post(
            url,
            json=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                # Marks the request as Origami-originated. cat.shabari's
                # gateway can group these and the analytics dashboard
                # can show "Origami COGS this month".
                "X-Bonito-Origami-Customer-Org": str(customer_org_id or ""),
                "X-Bonito-Origami-Customer-User": str(customer_user_id or ""),
                "X-Bonito-Source": "origami",
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

    METERING: every turn writes one OrigamiTurnLog row at the end with the
    user's REAL org_id, summed cost across all internal LLM calls, tokens,
    and tool-call count. This is what the Usage page reads and what tier
    quota enforcement counts against.
    """
    org_id = user.org_id
    session_id = uuid.uuid4()
    started_at_ms = int(time.time() * 1000)

    # Live tier + quota check BEFORE any LLM call
    tier = await _get_user_tier(db, org_id)
    quota = await metering.check_quota(db, org_id, tier)

    if quota["hard_cap"]:
        # Free tier over cap — block hard, prompt upgrade
        yield OrigamiEvent("error", {
            "code": "quota_exceeded_hard_cap",
            "message": (
                f"You've used all {quota['cap']} Origami turns on the Free plan "
                f"this month. Upgrade to keep building."
            ),
            "quota": quota,
        })
        await metering.record_origami_turn(
            db=db,
            org_id=org_id,
            user_id=user.id,
            og_token_id=None,
            session_id=session_id,
            conversation_id=conversation_id,
            user_message_preview=message,
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            tool_calls_count=0,
            model_used=None,
            status="over_quota",
            finish_reason="quota_hard_cap",
            tier_at_time=tier,
            duration_ms=0,
        )
        return

    yield OrigamiEvent("turn_started", {
        "conversation_id": conversation_id,
        "session_id": str(session_id),
        "tier": tier,
        "quota": quota,
    })

    messages: list[dict[str, Any]] = [
        {"role": "user", "content": message},
    ]

    tools_for_model = [
        _tool_to_openai_schema(cls) for cls in TOOL_REGISTRY.values()
    ]

    # Accumulators for the turn-level metering row
    total_input_tokens = 0
    total_output_tokens = 0
    total_tool_calls = 0
    final_status = "success"
    final_finish_reason: Optional[str] = None
    last_model_used: Optional[str] = None

    for iteration in range(ORIGAMI_MAX_TOOL_ITERATIONS):
        try:
            response = await _call_gateway(
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=tools_for_model,
                customer_org_id=org_id,
                customer_user_id=user.id,
            )
        except Exception as e:
            logger.exception("Origami gateway call failed (iteration %d)", iteration)
            final_status = "failed"
            final_finish_reason = "gateway_call_failed"
            yield OrigamiEvent("error", {
                "code": "gateway_call_failed",
                "message": str(e),
                "iteration": iteration,
            })
            await _record_turn(
                db=db,
                user=user,
                org_id=org_id,
                session_id=session_id,
                conversation_id=conversation_id,
                message=message,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                tool_calls_count=total_tool_calls,
                model_used=last_model_used,
                status=final_status,
                finish_reason=final_finish_reason,
                tier=tier,
                started_at_ms=started_at_ms,
            )
            return

        # OpenAI-format response (Bonito gateway emits this shape)
        choice = (response.get("choices") or [{}])[0]
        msg = choice.get("message", {})
        content = msg.get("content") or ""
        tool_calls = msg.get("tool_calls") or []
        finish_reason = choice.get("finish_reason")

        # Accumulate token usage if the gateway echoed it
        usage = response.get("usage") or {}
        total_input_tokens += int(usage.get("prompt_tokens") or 0)
        total_output_tokens += int(usage.get("completion_tokens") or 0)
        last_model_used = response.get("model") or ORIGAMI_MODEL

        if content:
            yield OrigamiEvent("message_complete", {"text": content})

        if not tool_calls:
            final_finish_reason = finish_reason
            yield OrigamiEvent("done", {
                "finish_reason": finish_reason,
                "iteration": iteration,
            })
            await _record_turn(
                db=db,
                user=user,
                org_id=org_id,
                session_id=session_id,
                conversation_id=conversation_id,
                message=message,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                tool_calls_count=total_tool_calls,
                model_used=last_model_used,
                status=final_status,
                finish_reason=final_finish_reason,
                tier=tier,
                started_at_ms=started_at_ms,
            )
            return

        # Build assistant turn that includes the tool calls (needed for next message validity)
        assistant_turn: dict[str, Any] = {
            "role": "assistant",
            "content": content or None,
            "tool_calls": tool_calls,
        }
        messages.append(assistant_turn)

        total_tool_calls += len(tool_calls)
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
                await metering.record_origami_audit(
                    db=db,
                    org_id=org_id,
                    user_id=user.id,
                    og_token_id=None,
                    session_id=session_id,
                    plan_card_id=None,
                    intent_summary=message,
                    tool_name=tool_name,
                    tool_params=params,
                    tier_at_time=tier,
                    confirmation="auto",
                    status="success",
                )
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
                await metering.record_origami_audit(
                    db=db,
                    org_id=org_id,
                    user_id=user.id,
                    og_token_id=None,
                    session_id=session_id,
                    plan_card_id=None,
                    intent_summary=message,
                    tool_name=tool_name,
                    tool_params=params,
                    tier_at_time=tier,
                    confirmation="auto",
                    status="failed",
                    error=str(e),
                )

    final_status = "failed"
    final_finish_reason = "max_iterations"
    yield OrigamiEvent("error", {
        "code": "max_iterations",
        "message": f"Tool loop exceeded {ORIGAMI_MAX_TOOL_ITERATIONS} iterations",
    })
    await _record_turn(
        db=db,
        user=user,
        org_id=org_id,
        session_id=session_id,
        conversation_id=conversation_id,
        message=message,
        input_tokens=total_input_tokens,
        output_tokens=total_output_tokens,
        tool_calls_count=total_tool_calls,
        model_used=last_model_used,
        status=final_status,
        finish_reason=final_finish_reason,
        tier=tier,
        started_at_ms=started_at_ms,
    )


async def _record_turn(
    *,
    db: AsyncSession,
    user: User,
    org_id: uuid.UUID,
    session_id: uuid.UUID,
    conversation_id: Optional[str],
    message: str,
    input_tokens: int,
    output_tokens: int,
    tool_calls_count: int,
    model_used: Optional[str],
    status: str,
    finish_reason: Optional[str],
    tier: str,
    started_at_ms: int,
) -> None:
    """Write the per-turn metering row. Best-effort, swallows errors."""
    duration_ms = int(time.time() * 1000) - started_at_ms
    cost_usd = _estimate_cost_usd(input_tokens, output_tokens)
    await metering.record_origami_turn(
        db=db,
        org_id=org_id,
        user_id=user.id,
        og_token_id=None,
        session_id=session_id,
        conversation_id=conversation_id,
        user_message_preview=message,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        tool_calls_count=tool_calls_count,
        model_used=model_used,
        status=status,
        finish_reason=finish_reason,
        tier_at_time=tier,
        duration_ms=duration_ms,
    )


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
