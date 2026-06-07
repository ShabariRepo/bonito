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
from app.services.origami import plan_store
from app.schemas.origami_plan import PlanCard, PlanCardStatus, PlanChange
# Tools register themselves at import time
from app.services.origami import tools as _tools  # noqa: F401

logger = logging.getLogger(__name__)

# Gateway target. Default points at the local backend for dev; in prod
# this becomes https://api.getbonito.com. Override with BONITO_GATEWAY_URL.
DEFAULT_GATEWAY_URL = os.getenv("BONITO_GATEWAY_URL", "http://localhost:8001")

# Model name as the gateway exposes it. Sonnet 4.5 / 4.6 are routed
# through the customer's connected provider (Anthropic, Bedrock, Vertex).
# Override with ORIGAMI_MODEL env var for environments where the gateway
# requires a specific provider-prefixed model id (e.g. Bedrock-routed dev).
ORIGAMI_MODEL = os.getenv("ORIGAMI_MODEL", "claude-sonnet-4-5")
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


_MEMWRIGHT_SINGLETON = None


def _get_memwright():
    """Lazy-init a process-wide MemwrightService instance."""
    global _MEMWRIGHT_SINGLETON
    if _MEMWRIGHT_SINGLETON is None:
        from app.services.memwright_service import MemwrightService
        _MEMWRIGHT_SINGLETON = MemwrightService()
    return _MEMWRIGHT_SINGLETON


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


# Stable agent_id used to namespace Memwright memories for Origami sessions.
# Origami isn't a Bonobot, but Memwright stores under {org}/{agent_id}/{session}.
ORIGAMI_MEMWRIGHT_AGENT_ID = "origami-system"


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
tool. When they ask about usage or limits, use `view_usage`. To inspect recent \
activity / logs use `view_logs`. To see what models the org can route to use \
`list_available_models`. To check tier gating use `check_tier_access`.

CRITICAL — after EVERY read tool returns, write a short, conversational \
summary message that answers the user's original question using the data the \
tool returned. Do NOT just call the tool and stop. Examples:

  User: "what providers do I have?"
  → call list_org_state → respond: "You have Bedrock, Anthropic direct, and \
    Vertex connected. Bedrock and Vertex are both active; Anthropic is in \
    pending status. Want me to fix that?"

  User: "how am I doing on quota?"
  → call view_usage → respond: "You're at 30 of 5,000 Origami turns this \
    month — plenty of headroom. Gateway requests: 0 used of unlimited."

If the tool returned an error, explain what went wrong in plain English and \
suggest a next step. Never echo raw tool output (no JSON, no curly braces) — \
translate it.

When a user asks to BUILD something (create an agent, create a KB, link them, \
mint a gateway key), use the appropriate write tool. The orchestrator will \
automatically PAUSE before executing — it builds a plan card from your tool \
calls and shows the user a Deploy / Edit / Cancel choice. Your job is to \
propose the right tools with the right params; the user confirms.

Be specific in tool params. If a user says "build me a support bot for our \
Shopify store, KB from our help docs", you should call create_kb with \
`name="shopify-support-help"` first.

CHAINING TOOL OUTPUTS: when a later step needs a value produced by an \
earlier step (e.g. link_kb_to_agent needs the kb_id from create_kb and the \
agent_id from create_agent), use template references in the params:

  ${step_N.field}   reference the Nth step's result field (1-indexed,
                    in plan order — so step_1 is the first tool call)
  ${prev.field}     reference the most recent step that produced `field`

Example for a 4-step build (project, kb, agent, link):

  1. create_project(name="ouchgpt", description="...")
  2. create_kb(name="ouchgpt-docs")
  3. create_agent(name="ouch-bot", system_prompt="...", project_id=${step_1.project_id})
  4. link_kb_to_agent(agent_id=${step_3.agent_id}, kb_id=${step_2.kb_id})

The orchestrator substitutes the real UUIDs when each step runs — the \
LLM does NOT need to know the values up-front."""


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


def _build_gateway_body(
    *,
    system: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    customer_org_id: Optional[uuid.UUID],
    customer_user_id: Optional[uuid.UUID],
    stream: bool,
) -> dict[str, Any]:
    """Common request body builder for streaming + non-streaming gateway calls."""
    full_messages = [{"role": "system", "content": system}] + messages
    body: dict[str, Any] = {
        "model": ORIGAMI_MODEL,
        "max_tokens": ORIGAMI_MAX_TOKENS,
        "messages": full_messages,
    }
    if tools:
        body["tools"] = tools
    if stream:
        body["stream"] = True
        # Ask the upstream to send a final chunk with token usage so we can
        # meter the turn. Supported by OpenAI; LiteLLM passes through.
        body["stream_options"] = {"include_usage": True}
    if customer_org_id:
        if customer_user_id:
            body["user"] = f"origami:org:{customer_org_id}:user:{customer_user_id}"
        else:
            body["user"] = f"origami:org:{customer_org_id}"
    return body


def _gateway_headers(
    api_key: str,
    customer_org_id: Optional[uuid.UUID],
    customer_user_id: Optional[uuid.UUID],
) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Bonito-Origami-Customer-Org": str(customer_org_id or ""),
        "X-Bonito-Origami-Customer-User": str(customer_user_id or ""),
        "X-Bonito-Source": "origami",
    }


async def _call_gateway(
    *,
    system: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    customer_org_id: Optional[uuid.UUID] = None,
    customer_user_id: Optional[uuid.UUID] = None,
) -> dict[str, Any]:
    """Non-streaming chat completion via Bonito's own gateway.

    Kept for callers that want a single complete response dict. The
    orchestrator uses `_stream_gateway` instead so it can emit per-token
    events as they arrive.
    """
    api_key = _get_gateway_key()
    url = f"{DEFAULT_GATEWAY_URL.rstrip('/')}/v1/chat/completions"
    body = _build_gateway_body(
        system=system, messages=messages, tools=tools,
        customer_org_id=customer_org_id, customer_user_id=customer_user_id,
        stream=False,
    )
    async with httpx.AsyncClient(timeout=ORIGAMI_HTTP_TIMEOUT) as client:
        resp = await client.post(
            url, json=body,
            headers=_gateway_headers(api_key, customer_org_id, customer_user_id),
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Gateway returned {resp.status_code}: {resp.text[:500]}")
        return resp.json()


async def _stream_gateway(
    *,
    system: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    customer_org_id: Optional[uuid.UUID] = None,
    customer_user_id: Optional[uuid.UUID] = None,
) -> AsyncIterator[dict[str, Any]]:
    """Stream chat completion chunks from Bonito's gateway.

    Yields parsed OpenAI-format SSE chunks one at a time. Each chunk has
    `choices[0].delta` with incremental `content` (text token), and/or
    `tool_calls` (tool-call args streamed in pieces, keyed by index).

    The final chunk(s) carry `finish_reason` and (when supported) `usage`
    for the turn's token totals.

    Pure HTTP — no SDK, just httpx parsing SSE lines.
    """
    api_key = _get_gateway_key()
    url = f"{DEFAULT_GATEWAY_URL.rstrip('/')}/v1/chat/completions"
    body = _build_gateway_body(
        system=system, messages=messages, tools=tools,
        customer_org_id=customer_org_id, customer_user_id=customer_user_id,
        stream=True,
    )
    headers = _gateway_headers(api_key, customer_org_id, customer_user_id)

    async with httpx.AsyncClient(timeout=ORIGAMI_HTTP_TIMEOUT) as client:
        async with client.stream("POST", url, json=body, headers=headers) as resp:
            if resp.status_code >= 400:
                err = await resp.aread()
                raise RuntimeError(
                    f"Gateway returned {resp.status_code}: {err.decode('utf-8', errors='replace')[:500]}"
                )

            async for raw_line in resp.aiter_lines():
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith(":"):  # SSE comment / keep-alive
                    continue
                if not line.startswith("data: "):
                    continue
                data = line[len("data: "):].strip()
                if data == "[DONE]":
                    return
                try:
                    yield json.loads(data)
                except json.JSONDecodeError:
                    logger.warning("Origami: dropped malformed SSE chunk: %r", data[:200])
                    continue


# ────────────────────────── Orchestrator entry point ──────────────────────────


async def run_origami_turn(
    *,
    user: User,
    message: str,
    conversation_id: Optional[str],
    project_id: Optional[uuid.UUID] = None,
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
            project_id=project_id,
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

    # ── Memwright recall ──
    # If we have a conversation_id and the model has a non-zero budget
    # (Sonnet+ class), pull relevant context from prior turns. Memwright
    # gates Haiku / Flash / Mini to zero budget so they don't hallucinate
    # on dredged memory — that gating is built in.
    memory_context = ""
    if conversation_id:
        try:
            from app.services.memwright_service import MemwrightService
            mw = _get_memwright()
            memory_context = await mw.recall(
                session_id=conversation_id,
                agent_id=ORIGAMI_MEMWRIGHT_AGENT_ID,
                org_id=str(org_id),
                message=message,
                model_id=ORIGAMI_MODEL,
            )
        except Exception:
            logger.exception("Memwright recall failed (non-fatal)")
            memory_context = ""

    user_content = message
    if memory_context:
        user_content = f"{memory_context}\n\nUser message: {message}"

    messages: list[dict[str, Any]] = [
        {"role": "user", "content": user_content},
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
    # Track every tool that successfully ran so we can synthesize a fallback
    # summary if the model goes silent after tool_use (Bedrock+Opus quirk).
    results: list[dict[str, Any]] = []

    for iteration in range(ORIGAMI_MAX_TOOL_ITERATIONS):
        # ── Streaming accumulators ─────────────────────────
        # As chunks arrive from the gateway we accumulate text + tool calls
        # locally. Per-token text fires `message_token` events immediately.
        # Tool calls only fire once their JSON args have fully assembled.
        accumulated_content = ""
        accumulated_tool_calls: dict[int, dict[str, Any]] = {}
        finish_reason: Optional[str] = None
        chunk_usage: dict[str, Any] = {}

        try:
            async for chunk in _stream_gateway(
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=tools_for_model,
                customer_org_id=org_id,
                customer_user_id=user.id,
            ):
                # Track which model the gateway routed to (only on first chunk
                # that includes it). Useful for the metering row.
                model_from_chunk = chunk.get("model")
                if model_from_chunk:
                    last_model_used = model_from_chunk

                # The final chunk before [DONE] may carry usage stats
                if chunk.get("usage"):
                    chunk_usage = chunk["usage"]

                choices = chunk.get("choices") or []
                if not choices:
                    continue
                choice = choices[0]
                delta = choice.get("delta") or {}
                if choice.get("finish_reason"):
                    finish_reason = choice["finish_reason"]

                # Text content streaming
                content_piece = delta.get("content")
                if content_piece:
                    accumulated_content += content_piece
                    yield OrigamiEvent("message_token", {"token": content_piece})

                # Tool-call streaming — each delta.tool_calls entry has an
                # `index` that ties partial chunks together
                tc_deltas = delta.get("tool_calls") or []
                for tc_delta in tc_deltas:
                    idx = tc_delta.get("index", 0)
                    if idx not in accumulated_tool_calls:
                        accumulated_tool_calls[idx] = {
                            "id": "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        }
                    if "id" in tc_delta and tc_delta["id"]:
                        accumulated_tool_calls[idx]["id"] = tc_delta["id"]
                    fn_delta = tc_delta.get("function") or {}
                    if "name" in fn_delta and fn_delta["name"]:
                        accumulated_tool_calls[idx]["function"]["name"] = fn_delta["name"]
                    if "arguments" in fn_delta and fn_delta["arguments"] is not None:
                        accumulated_tool_calls[idx]["function"]["arguments"] += fn_delta["arguments"]
        except Exception as e:
            logger.exception("Origami gateway stream failed (iteration %d)", iteration)
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
                project_id=project_id,
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

        # Stream is done. Convert accumulated_tool_calls back to ordered list.
        tool_calls = [accumulated_tool_calls[i] for i in sorted(accumulated_tool_calls)]
        content = accumulated_content

        # Fallback: some providers (Bedrock-routed Anthropic, sometimes Vertex)
        # don't normalize tool calls into structured tool_calls[]. They embed
        # them in the content as <tool_call>{...}</tool_call>, <function>...,
        # or <invoke name="..."><parameter ...>...</parameter></invoke>.
        # Parse those out so tools work regardless of routing.
        stripped_inline = False
        if not tool_calls and content:
            inline = _extract_inline_tool_calls(content)
            if inline:
                tool_calls = inline
                # Strip the inline tool-call syntax from the visible message —
                # it's noise the user shouldn't see. Run all three patterns;
                # whichever the model used gets removed.
                stripped = _TOOL_CALL_JSON_RE.sub("", content)
                stripped = _INVOKE_BLOCK_RE.sub("", stripped)
                stripped = _PARAMETERIZED_FUNCTION_RE.sub("", stripped)
                stripped = stripped.strip()
                accumulated_content = stripped
                content = stripped
                stripped_inline = True

        # Accumulate token usage from the final usage chunk. Some upstreams
        # (notably Bedrock via LiteLLM) don't honor stream_options.include_usage
        # consistently — when the gateway doesn't echo a usage chunk, fall back
        # to a word-count-based estimate so the metering row isn't $0.
        prompt_tokens = int(chunk_usage.get("prompt_tokens") or 0)
        completion_tokens = int(chunk_usage.get("completion_tokens") or 0)

        if prompt_tokens == 0:
            # Rough estimate: 1.3 tokens per word across system + tools + history
            sys_words = len(SYSTEM_PROMPT.split())
            history_words = sum(
                len(str(m.get("content") or "").split()) for m in messages
            )
            tool_schema_words = sum(
                len(json.dumps(t).split()) for t in tools_for_model
            )
            prompt_tokens = int((sys_words + history_words + tool_schema_words) * 1.3)
        if completion_tokens == 0 and accumulated_content:
            completion_tokens = int(len(accumulated_content.split()) * 1.3)

        total_input_tokens += prompt_tokens
        total_output_tokens += completion_tokens
        if not last_model_used:
            last_model_used = ORIGAMI_MODEL

        # Emit a `message_complete` so the frontend can reconcile the
        # streamed tokens with the final (possibly stripped) text. ALWAYS
        # emit — if we stripped inline tool-call markup and the content is
        # now empty, the frontend needs to know so it can remove the stale
        # streaming bubble showing raw <tool_call> markup. Without this,
        # the user sees the raw tags.
        yield OrigamiEvent("message_complete", {
            "text": content,
            "stripped_inline_tool_calls": stripped_inline,
        })

        if not tool_calls:
            # Synthesize a friendly summary if the model went silent after a
            # tool ran, OR if the content we got back looks like nothing but
            # tool-call markup that couldn't be parsed (Bedrock + Opus
            # picks inconsistent formats — even when one iteration's call
            # was extracted, the follow-up sometimes hallucinates a different
            # markup format that bypasses the parser).
            looks_like_markup = bool(content) and (
                "<function>" in content or
                "<tool_call>" in content or
                "<invoke" in content or
                "<parameter" in content
            )
            if (not content or looks_like_markup) and total_tool_calls > 0 and results:
                content = _synthesize_tool_summary(results)
                accumulated_content = content
                yield OrigamiEvent("message_complete", {
                    "text": content,
                    "synthesized": True,
                })
            final_finish_reason = finish_reason
            yield OrigamiEvent("done", {
                "finish_reason": finish_reason,
                "iteration": iteration,
            })
            # Store the turn in Memwright so future turns can recall context.
            # No-op for zero-budget models (Haiku/Flash); never blocks.
            if conversation_id and accumulated_content:
                try:
                    mw = _get_memwright()
                    await mw.store(
                        session_id=conversation_id,
                        agent_id=ORIGAMI_MEMWRIGHT_AGENT_ID,
                        org_id=str(org_id),
                        user_msg=message,
                        assistant_msg=accumulated_content,
                        model_id=ORIGAMI_MODEL,
                        tags=["origami"],
                    )
                except Exception:
                    logger.exception("Memwright store failed (non-fatal)")
            await _record_turn(
                db=db,
                user=user,
                org_id=org_id,
                project_id=project_id,
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

        # ── Plan-card gate ────────────────────────────────────────────
        # If any of the requested tools is_write=True, we don't execute
        # any of them. Instead we bundle ALL requested tool calls (writes
        # AND any reads in the same response) into a single PlanCard,
        # emit `plan_ready`, and stop. User clicks Deploy → execute_plan
        # endpoint runs them. Read-only batches execute inline as before.
        has_write_tool = any(
            (TOOL_REGISTRY.get(tc.get("function", {}).get("name", "")) and
             TOOL_REGISTRY[tc["function"]["name"]].is_write)
            for tc in tool_calls
        )

        if has_write_tool:
            plan_changes: list[PlanChange] = []
            for tc in tool_calls:
                fn = tc.get("function", {})
                tname = fn.get("name", "")
                try:
                    p = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    p = {}
                p = sanitize_params(p)
                tcls = TOOL_REGISTRY.get(tname)
                plan_changes.append(PlanChange(
                    action=tname,
                    params=p,
                    is_write=bool(tcls and tcls.is_write),
                    summary=(tcls.description if tcls else None),
                ))

            plan = PlanCard(
                id=uuid.uuid4(),
                session_id=session_id,
                intent=message[:500] if message else "(no intent recorded)",
                changes=plan_changes,
                status=PlanCardStatus.AWAITING_CONFIRMATION,
            )
            await plan_store.save_plan(
                plan=plan,
                user_id=user.id,
                org_id=org_id,
                project_id=project_id,
                conversation_id=conversation_id,
                user_message=message,
            )

            yield OrigamiEvent("plan_ready", {
                "plan_card": plan.model_dump(mode="json"),
            })
            yield OrigamiEvent("awaiting_confirmation", {
                "plan_card_id": str(plan.id),
            })

            # Record the turn now — the LLM's planning work is over.
            # When execute_plan runs, it logs its OWN turn for the
            # downstream tool dispatch.
            final_finish_reason = "plan_ready"
            await _record_turn(
                db=db, user=user, org_id=org_id, project_id=project_id,
                session_id=session_id, conversation_id=conversation_id,
                message=message, input_tokens=total_input_tokens,
                output_tokens=total_output_tokens, tool_calls_count=total_tool_calls,
                model_used=last_model_used, status="success",
                finish_reason=final_finish_reason, tier=tier,
                started_at_ms=started_at_ms,
            )
            return

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
                results.append({"tool": tool_name, "result": result})
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
                    project_id=project_id,
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
                    project_id=project_id,
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

        # After processing this batch of read tools, inject an explicit nudge
        # so the next LLM iteration actually writes a follow-up summary.
        # Some Bedrock-routed Anthropic models otherwise just stop after
        # tool_use, OR worse, call the same tool again. We tell it firmly:
        # NO MORE TOOLS, write plain text, you have the data you need.
        if tool_calls:
            messages.append({
                "role": "user",
                "content": (
                    "STOP. Do NOT call any more tools. Do NOT emit "
                    "<tool_call>, <function>, or <invoke> tags. You already "
                    "have the answer in the tool result above. Write a "
                    "short, plain-text conversational reply (1-3 sentences) "
                    "that translates the tool result into a direct answer "
                    "to my original question. Just text. No XML, no JSON."
                ),
            })

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
        project_id=project_id,
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


async def execute_plan(
    *,
    user: User,
    plan_card_id: str,
    db: AsyncSession,
) -> AsyncIterator[OrigamiEvent]:
    """Execute a previously-saved plan card. Runs each change in order, emits
    tool_started / tool_completed / tool_failed per change, plus an
    execution_done event with the result preview.

    Caller (the FastAPI route) wraps each event into SSE. Same security
    invariants as run_origami_turn: org_id is read from the auth context
    (the user passed in), NEVER from the plan's stored payload.
    """
    entry = await plan_store.get_plan(plan_card_id)
    if not entry:
        yield OrigamiEvent("error", {
            "code": "plan_not_found",
            "message": "Plan card not found or expired. Ask Origami again — plans live 10 minutes.",
        })
        return

    plan, ctx = entry

    # Ownership check: only the user who created the plan can execute it
    if ctx["user_id"] != user.id:
        yield OrigamiEvent("error", {
            "code": "plan_owner_mismatch",
            "message": "Plan was created by a different user.",
        })
        return
    if ctx["org_id"] != user.org_id:
        yield OrigamiEvent("error", {
            "code": "plan_org_mismatch",
            "message": "Plan belongs to a different organization.",
        })
        return

    await plan_store.update_status(plan_card_id, PlanCardStatus.EXECUTING)
    yield OrigamiEvent("execution_started", {
        "plan_card_id": plan_card_id,
        "total_steps": len(plan.changes),
    })

    started_at_ms = int(time.time() * 1000)
    session_id = uuid.uuid4()
    project_id = ctx.get("project_id")
    conversation_id = ctx.get("conversation_id")

    tier = await _get_user_tier(db, user.org_id)
    results: list[dict[str, Any]] = []
    # step_results holds the per-step return dict so that template refs in
    # downstream steps (e.g. link_kb_to_agent(agent_id=${step_3.agent_id})
    # ) can read the just-created ids.
    step_results: list[dict[str, Any]] = []
    failed_count = 0

    for step_idx, change in enumerate(plan.changes):
        tool_cls = TOOL_REGISTRY.get(change.action)
        if not tool_cls:
            yield OrigamiEvent("tool_failed", {
                "tool_name": change.action,
                "step": step_idx,
                "error": "unknown_tool",
            })
            failed_count += 1
            # Placeholder so step_results indices stay aligned with change indices
            step_results.append({})
            continue

        yield OrigamiEvent("tool_started", {
            "tool_name": change.action,
            "step": step_idx,
            "total": len(plan.changes),
        })

        try:
            instance = tool_cls()
            params = sanitize_params(change.params or {})
            # Resolve ${step_N.field} / ${prev.field} references from earlier
            # tool results before sending params downstream.
            params = _resolve_template_params(params, step_results)
            # Heuristic: if a link tool still has unset ids, infer from the
            # most recent matching create result.
            params = _heuristic_fill_link_params(change.action, params, step_results)
            result = await instance.execute(
                org_id=user.org_id,  # ← STILL from auth, even on replay
                user=user,
                params=params,
                db=db,
            )
            results.append({"action": change.action, "result": result})
            # Record this step's result so later steps can reference its fields
            step_results.append(result if isinstance(result, dict) else {})

            # Tools that signal a structured failure (success=False)
            # should be counted as failures even though no exception fired.
            tool_succeeded = result.get("success", True) if isinstance(result, dict) else True
            if not tool_succeeded:
                yield OrigamiEvent("tool_failed", {
                    "tool_name": change.action,
                    "step": step_idx,
                    "error": (result.get("message") or result.get("error") or "unspecified") if isinstance(result, dict) else "unknown",
                    "code": result.get("error") if isinstance(result, dict) else None,
                })
                failed_count += 1
                await metering.record_origami_audit(
                    db=db, org_id=user.org_id, user_id=user.id,
                    og_token_id=None, project_id=project_id,
                    session_id=session_id,
                    plan_card_id=uuid.UUID(plan_card_id),
                    intent_summary=plan.intent, tool_name=change.action,
                    tool_params=params, tier_at_time=tier,
                    confirmation="user_clicked", status="failed",
                    error=str(result.get("message") or result.get("error"))[:1000] if isinstance(result, dict) else None,
                )
                continue

            yield OrigamiEvent("tool_completed", {
                "tool_name": change.action,
                "step": step_idx,
                "result_summary": _summarize_result(result),
            })
            await metering.record_origami_audit(
                db=db, org_id=user.org_id, user_id=user.id,
                og_token_id=None, project_id=project_id,
                session_id=session_id,
                plan_card_id=uuid.UUID(plan_card_id),
                intent_summary=plan.intent, tool_name=change.action,
                tool_params=params, tier_at_time=tier,
                confirmation="user_clicked", status="success",
            )
        except Exception as e:
            logger.exception("execute_plan: tool %s failed", change.action)
            yield OrigamiEvent("tool_failed", {
                "tool_name": change.action,
                "step": step_idx,
                "error": str(e),
            })
            failed_count += 1
            # Keep step_results aligned with change indices even on exception
            step_results.append({})
            await metering.record_origami_audit(
                db=db, org_id=user.org_id, user_id=user.id,
                og_token_id=None, project_id=project_id,
                session_id=session_id,
                plan_card_id=uuid.UUID(plan_card_id),
                intent_summary=plan.intent, tool_name=change.action,
                tool_params=change.params, tier_at_time=tier,
                confirmation="user_clicked", status="failed",
                error=str(e),
            )

    overall_status = "failed" if failed_count == len(plan.changes) else (
        "partial" if failed_count > 0 else "success"
    )
    await plan_store.update_status(
        plan_card_id,
        PlanCardStatus.FAILED if overall_status == "failed" else PlanCardStatus.DONE,
    )

    yield OrigamiEvent("execution_done", {
        "plan_card_id": plan_card_id,
        "status": overall_status,
        "failed_count": failed_count,
        "succeeded_count": len(plan.changes) - failed_count,
        "results": results,
    })

    # Metering row for the execution turn itself (no LLM call → token=0,
    # cost=0; tool_calls_count = number of changes that ran)
    await _record_turn(
        db=db, user=user, org_id=user.org_id, project_id=project_id,
        session_id=session_id, conversation_id=conversation_id,
        message=f"[plan execute] {plan.intent[:200]}",
        input_tokens=0, output_tokens=0,
        tool_calls_count=len(plan.changes) - failed_count,
        model_used=None, status=overall_status,
        finish_reason="plan_executed",
        tier=tier, started_at_ms=started_at_ms,
    )

    # Clean up the plan now that it's been run
    await plan_store.delete_plan(plan_card_id)


async def _record_turn(
    *,
    db: AsyncSession,
    user: User,
    org_id: uuid.UUID,
    project_id: Optional[uuid.UUID],
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
        project_id=project_id,
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


import re

# Match an inline tool call wrapped in any of the common tags. We capture
# everything between the open and close tag (non-greedy), then parse JSON
# in code. Using `\{.*?\}` here would stop at the first `}`, which breaks
# JSON with nested objects like {"name": "x", "parameters": {...}}.
_TOOL_CALL_JSON_RE = re.compile(
    r"<(tool_call|function|function_call|tool_use)>\s*(.*?)\s*</\1>",
    re.DOTALL,
)
_INVOKE_BLOCK_RE = re.compile(
    r'<invoke\s+name="([^"]+)">\s*(.*?)\s*</invoke>', re.DOTALL
)
_PARAM_RE = re.compile(
    r'<parameter\s+name="([^"]+)">\s*(.*?)\s*</parameter>', re.DOTALL
)
# Some Bedrock-routed models emit
#   <function>
#     <parameter name="name">list_org_state</parameter>
#     <parameter name="arguments">{}</parameter>
#   </function>
# i.e. the function tag has NO attribute and the function name + json args
# are encoded as child <parameter> elements. Catch this separately because
# the inner content isn't valid JSON or call syntax.
_PARAMETERIZED_FUNCTION_RE = re.compile(
    r"<function>\s*(.*?)\s*</function>", re.DOTALL,
)


# ────────────────────────── Template references ──────────────────────────


_STEP_REF_RE = re.compile(r"\$\{step_(\d+)\.([a-zA-Z_][a-zA-Z0-9_]*)\}")
_PREV_REF_RE = re.compile(r"\$\{prev\.([a-zA-Z_][a-zA-Z0-9_]*)\}")


def _resolve_one(value: Any, step_results: list[dict[str, Any]]) -> Any:
    """Resolve a single ${step_N.field} or ${prev.field} in a param value.

    step_results is the list of tool results in execution order (indices
    are 1-based when referenced as `step_1`, `step_2`, ... in templates).

    Strings that contain a template ref but aren't ONLY that ref are
    string-interpolated. A bare `${step_2.agent_id}` is replaced with the
    raw value (preserves type — UUID string stays as is).
    """
    if not isinstance(value, str):
        return value

    # Exact-match path — replace with raw typed value
    m = _STEP_REF_RE.fullmatch(value.strip())
    if m:
        idx = int(m.group(1)) - 1
        field = m.group(2)
        if 0 <= idx < len(step_results):
            return step_results[idx].get(field, value)
        return value
    m = _PREV_REF_RE.fullmatch(value.strip())
    if m:
        field = m.group(1)
        for sr in reversed(step_results):
            if isinstance(sr, dict) and field in sr:
                return sr[field]
        return value

    # Interpolation path — embed each ref into the string
    def _sub_step(match):
        idx = int(match.group(1)) - 1
        field = match.group(2)
        if 0 <= idx < len(step_results):
            return str(step_results[idx].get(field, match.group(0)))
        return match.group(0)

    def _sub_prev(match):
        field = match.group(1)
        for sr in reversed(step_results):
            if isinstance(sr, dict) and field in sr:
                return str(sr[field])
        return match.group(0)

    return _PREV_REF_RE.sub(_sub_prev, _STEP_REF_RE.sub(_sub_step, value))


def _resolve_template_params(
    params: dict[str, Any],
    step_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Walk params and resolve template refs. Lists are recursed one level."""
    resolved: dict[str, Any] = {}
    for k, v in params.items():
        if isinstance(v, list):
            resolved[k] = [_resolve_one(item, step_results) for item in v]
        elif isinstance(v, dict):
            resolved[k] = {ik: _resolve_one(iv, step_results) for ik, iv in v.items()}
        else:
            resolved[k] = _resolve_one(v, step_results)
    return resolved


def _heuristic_fill_link_params(
    tool_name: str,
    params: dict[str, Any],
    step_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Fallback for chained writes when the model didn't use template syntax.

    If link_kb_to_agent is called with empty / invalid agent_id or kb_id
    AND there's exactly one create_agent / create_kb result in step_results,
    fill it in. Same idea for any other id-coupled tool we add later.
    """
    if tool_name != "link_kb_to_agent":
        return params

    out = dict(params)

    def _looks_unset(v: Any) -> bool:
        if not isinstance(v, str):
            return True
        s = v.strip()
        if not s or s.lower() in {"null", "none", "todo", "id", "uuid"}:
            return True
        try:
            uuid.UUID(s)
            return False
        except ValueError:
            return True

    if _looks_unset(out.get("agent_id")):
        for sr in reversed(step_results):
            if isinstance(sr, dict) and sr.get("agent_id"):
                out["agent_id"] = sr["agent_id"]
                break
    if _looks_unset(out.get("kb_id")):
        for sr in reversed(step_results):
            if isinstance(sr, dict) and sr.get("kb_id"):
                out["kb_id"] = sr["kb_id"]
                break
    return out


def _try_parse_function_call_syntax(text: str) -> Optional[tuple[str, dict[str, Any]]]:
    """Parse `name(arg=value, arg=value)` style calls inside tool-call tags.

    Bedrock's Anthropic models sometimes pick this instead of JSON, so we
    parse it as a fallback. Uses Python's ast module to safely evaluate
    just the kwargs (no execution).
    """
    import ast

    text = text.strip()
    if "(" not in text or not text.endswith(")"):
        return None
    open_paren = text.find("(")
    name = text[:open_paren].strip()
    if not name or not name.replace("_", "").isalnum():
        return None
    # Parse the whole `name(args)` expression directly — it's already a valid
    # Python call expression. Don't wrap.
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError:
        return None
    if not isinstance(tree.body, ast.Call):
        return None
    call: ast.Call = tree.body
    params: dict[str, Any] = {}
    for kw in call.keywords:
        if kw.arg is None:
            continue
        try:
            params[kw.arg] = ast.literal_eval(kw.value)
        except (ValueError, SyntaxError):
            try:
                params[kw.arg] = ast.unparse(kw.value)
            except Exception:
                continue
    # If only positional args (e.g. create_kb("name")) we can't reliably map
    # them, so we bail. Origami's tools require named args anyway.
    if not params and call.args:
        return None
    return name, params


def _extract_first_json_object(text: str) -> Optional[dict[str, Any]]:
    """Pull the first balanced { ... } object out of text and json.loads it.

    Useful when a model wraps the JSON in backticks, prefixes with commentary,
    or trails a stray comma — we still want the structured payload.
    """
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start:i + 1]
                try:
                    obj = json.loads(candidate)
                    return obj if isinstance(obj, dict) else None
                except json.JSONDecodeError:
                    return None
    return None


def _extract_inline_tool_calls(text: str) -> list[dict[str, Any]]:
    """Parse tool calls embedded in message text.

    Different upstreams normalize tool calls differently. OpenAI direct
    returns structured tool_calls[]. Anthropic via Bedrock (and some other
    LiteLLM paths) embeds them in the message content as either:

        <tool_call>{"name": "...", "parameters": {...}}</tool_call>

    or

        <invoke name="...">
          <parameter name="...">value</parameter>
          ...
        </invoke>

    Origami catches both so write tools work regardless of upstream
    routing. Returns OpenAI-shaped tool_calls list (id/type/function).
    """
    if not text:
        return []

    calls: list[dict[str, Any]] = []

    for match in _TOOL_CALL_JSON_RE.finditer(text):
        raw_inner = (match.group(2) or "").strip()
        if not raw_inner:
            continue

        name: Optional[str] = None
        params: dict[str, Any] = {}

        # First: parameterized-children format. Anthropic via Bedrock
        # sometimes wraps tool calls as
        #   <function><parameter name="name">X</parameter>
        #             <parameter name="arguments">{...}</parameter></function>
        # The inner content is XML-ish, NOT json. The model is also
        # inconsistent about WHICH parameter names it uses — sometimes
        # "name"/"arguments", sometimes "tool_name"/"params", sometimes
        # "function_name"/"input". Try every common synonym.
        _NAME_KEYS = ("name", "tool_name", "function_name", "function", "tool")
        _ARGS_KEYS = ("arguments", "params", "parameters", "input", "args")
        if "<parameter" in raw_inner:
            sub = _params_from_parameter_tags(raw_inner)
            fn_name = None
            for k in _NAME_KEYS:
                v = sub.pop(k, None)
                if isinstance(v, str) and v:
                    fn_name = v
                    break
            args_raw = None
            for k in _ARGS_KEYS:
                v = sub.pop(k, None)
                if v is not None:
                    args_raw = v
                    break
            if isinstance(fn_name, str) and fn_name:
                name = fn_name
                if isinstance(args_raw, dict):
                    params = args_raw
                elif isinstance(args_raw, str):
                    try:
                        parsed = json.loads(args_raw) if args_raw.strip() else {}
                        params = parsed if isinstance(parsed, dict) else {}
                    except json.JSONDecodeError:
                        params = {}
                # Anything else left in `sub` is treated as direct kwargs
                # for the tool. Useful when the model uses a different
                # parameter structure entirely.
                if not params and sub:
                    params = sub

        # Otherwise try strict JSON
        if not name:
            payload = None
            try:
                parsed = json.loads(raw_inner)
                if isinstance(parsed, dict):
                    payload = parsed
            except json.JSONDecodeError:
                pass
            if payload is None:
                payload = _extract_first_json_object(raw_inner)
            if isinstance(payload, dict):
                name = payload.get("name")
                params = payload.get("parameters") or payload.get("arguments") or payload.get("input") or {}
                if not isinstance(params, dict):
                    params = {}

        # Last-resort: function-call syntax `name(arg=value, ...)`. Bedrock's
        # Anthropic models pick this sometimes instead of JSON.
        if not name:
            fc = _try_parse_function_call_syntax(raw_inner)
            if fc is None:
                continue
            name, params = fc

        if not name:
            continue
        calls.append({
            "id": f"inline-{len(calls)}",
            "type": "function",
            "function": {"name": name, "arguments": json.dumps(params)},
        })

    for match in _INVOKE_BLOCK_RE.finditer(text):
        name = match.group(1)
        body = match.group(2) or ""
        params = _params_from_parameter_tags(body)
        if name:
            calls.append({
                "id": f"inline-{len(calls)}",
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(params)},
            })

    return calls


def _params_from_parameter_tags(body: str) -> dict[str, Any]:
    """Pull <parameter name="X">value</parameter> pairs into a dict, with
    light type coercion (true/false → bool, int / float when natural)."""
    out: dict[str, Any] = {}
    for p_match in _PARAM_RE.finditer(body):
        key, raw = p_match.group(1), (p_match.group(2) or "").strip()
        if raw.lower() in {"true", "false"}:
            out[key] = raw.lower() == "true"
            continue
        try:
            out[key] = int(raw)
            continue
        except ValueError:
            pass
        try:
            out[key] = float(raw)
            continue
        except ValueError:
            pass
        out[key] = raw
    return out


def _synthesize_tool_summary(results: list[dict[str, Any]]) -> str:
    """Build a friendly fallback summary from raw tool results.

    Used when the model returns no follow-up text after running a tool —
    a known Bedrock+Opus quirk where stop_reason="tool_use" sometimes
    leaves the chat empty. We translate the structured tool output into
    a 1-2 sentence answer so the user isn't staring at a blank message.
    """
    if not results:
        return "I ran the tools but got no results back."
    parts: list[str] = []
    for entry in results:
        tool = entry.get("tool", "")
        r = entry.get("result", {}) or {}
        if not isinstance(r, dict):
            continue

        if tool == "list_org_state":
            counts = r.get("counts") or {}
            tier = r.get("tier", "free")
            provs = r.get("providers") or []
            active = sum(1 for p in provs if isinstance(p, dict) and p.get("active"))
            total = len(provs)
            parts.append(
                f"You have {total} provider{'s' if total != 1 else ''} connected "
                f"({active} active), {counts.get('agents', 0)} agent"
                f"{'s' if counts.get('agents', 0) != 1 else ''}, "
                f"{counts.get('kbs', 0)} knowledge base"
                f"{'s' if counts.get('kbs', 0) != 1 else ''}, "
                f"and {counts.get('projects', 0)} project"
                f"{'s' if counts.get('projects', 0) != 1 else ''} on the {tier} tier."
            )
        elif tool == "view_usage":
            tier = r.get("tier", "")
            gw = r.get("gateway_requests") or {}
            used = gw.get("used", 0)
            limit = gw.get("limit", "unlimited")
            parts.append(
                f"On the {tier} tier you've used {used} of {limit} gateway "
                f"requests this period ({gw.get('percent_used', 0)}%)."
            )
        elif tool == "list_available_models":
            providers = r.get("providers") or []
            summary = r.get("summary") or {}
            total_models = summary.get("total_models", sum(len(p.get("models") or []) for p in providers))
            ptypes = [p.get("provider_type") for p in providers if p.get("provider_type")]
            if ptypes:
                parts.append(
                    f"You have {total_models} models available across "
                    f"{len(ptypes)} provider{'s' if len(ptypes) != 1 else ''} "
                    f"({', '.join(ptypes)})."
                )
            else:
                parts.append("No models are routable yet — connect a provider first.")
        elif tool == "view_logs":
            gw = r.get("gateway_requests") or {}
            sess = r.get("agent_sessions") or {}
            parts.append(
                f"Recent activity: {gw.get('shown', 0)} gateway requests "
                f"({gw.get('success', 0)} success, {gw.get('errors', 0)} errors), "
                f"{sess.get('shown', 0)} agent sessions."
            )
        elif tool == "check_tier_access":
            tier = r.get("tier", "")
            allowed = r.get("allowed_features") or []
            gated = r.get("gated_features") or []
            parts.append(
                f"On {tier}, you have {len(allowed)} features available and "
                f"{len(gated)} gated. Use the tier-access tool again with a "
                f"specific feature name for the upgrade path."
            )
        else:
            # Unknown tool — fall back to a generic acknowledgement
            if r.get("success") is True:
                parts.append(f"Ran `{tool}` successfully.")
            elif r.get("success") is False:
                msg = r.get("message") or r.get("error") or "failed"
                parts.append(f"`{tool}` failed: {msg}")
            else:
                parts.append(f"Ran `{tool}`.")
    if not parts:
        return "I ran the tools — check the Activity log on the right for details."
    return " ".join(parts)


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
