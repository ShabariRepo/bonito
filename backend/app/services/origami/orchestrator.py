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

When a user asks to BUILD something (create an agent, create a KB, link them, \
mint a gateway key), use the appropriate write tool. The orchestrator will \
automatically PAUSE before executing — it builds a plan card from your tool \
calls and shows the user a Deploy / Edit / Cancel choice. Your job is to \
propose the right tools with the right params; the user confirms.

Be specific in tool params. If a user says "build me a support bot for our \
Shopify store, KB from our help docs", you should call create_kb with \
`name="shopify-support-help"` first."""


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
        # them in the content as <tool_call>{...}</tool_call> or
        # <invoke name="..."><parameter ...>...</parameter></invoke>.
        # Parse those out so write tools work regardless of routing.
        if not tool_calls and content:
            inline = _extract_inline_tool_calls(content)
            if inline:
                tool_calls = inline
                # Strip the inline tool-call syntax from what we emit as the
                # assistant's visible message — it's noise for the user.
                stripped = _TOOL_CALL_JSON_RE.sub("", content).strip()
                stripped = _INVOKE_BLOCK_RE.sub("", stripped).strip()
                accumulated_content = stripped
                content = stripped

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

        # Emit a `message_complete` carrying the full accumulated text for
        # any downstream consumer (audit log, conversation history) that
        # wants the whole message rather than reassembling tokens.
        if content:
            yield OrigamiEvent("message_complete", {"text": content})

        if not tool_calls:
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
            plan_store.save_plan(
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
    entry = plan_store.get_plan(plan_card_id)
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

    plan_store.update_status(plan_card_id, PlanCardStatus.EXECUTING)
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
            continue

        yield OrigamiEvent("tool_started", {
            "tool_name": change.action,
            "step": step_idx,
            "total": len(plan.changes),
        })

        try:
            instance = tool_cls()
            params = sanitize_params(change.params or {})
            result = await instance.execute(
                org_id=user.org_id,  # ← STILL from auth, even on replay
                user=user,
                params=params,
                db=db,
            )
            results.append({"action": change.action, "result": result})
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
    plan_store.update_status(
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
    plan_store.delete_plan(plan_card_id)


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

_TOOL_CALL_JSON_RE = re.compile(
    r"<(?:tool_call|function|function_call|tool_use)>\s*(\{.*?\})\s*</(?:tool_call|function|function_call|tool_use)>",
    re.DOTALL,
)
_INVOKE_BLOCK_RE = re.compile(
    r'<invoke\s+name="([^"]+)">\s*(.*?)\s*</invoke>', re.DOTALL
)
_PARAM_RE = re.compile(
    r'<parameter\s+name="([^"]+)">\s*(.*?)\s*</parameter>', re.DOTALL
)


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
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        name = payload.get("name")
        params = payload.get("parameters") or payload.get("arguments") or payload.get("input") or {}
        if not name or not isinstance(params, dict):
            continue
        calls.append({
            "id": f"inline-{len(calls)}",
            "type": "function",
            "function": {"name": name, "arguments": json.dumps(params)},
        })

    for match in _INVOKE_BLOCK_RE.finditer(text):
        name = match.group(1)
        body = match.group(2) or ""
        params: dict[str, Any] = {}
        for p_match in _PARAM_RE.finditer(body):
            key, raw = p_match.group(1), (p_match.group(2) or "").strip()
            # Try to coerce numbers / bools where natural
            if raw.lower() in {"true", "false"}:
                params[key] = raw.lower() == "true"
            else:
                try:
                    params[key] = int(raw)
                except ValueError:
                    try:
                        params[key] = float(raw)
                    except ValueError:
                        params[key] = raw
        if name:
            calls.append({
                "id": f"inline-{len(calls)}",
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(params)},
            })

    return calls


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
