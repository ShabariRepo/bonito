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
from app.services.origami import messages as origami_messages
from app.schemas.origami_plan import PlanCard, PlanCardStatus, PlanChange
# Tools register themselves at import time
from app.services.origami import tools as _tools  # noqa: F401

logger = logging.getLogger(__name__)

# Gateway target. Default points at the local backend for dev; in prod
# this becomes https://api.getbonito.com. Override with BONITO_GATEWAY_URL.
DEFAULT_GATEWAY_URL = os.getenv("BONITO_GATEWAY_URL", "http://localhost:8001")

# Model name as the gateway exposes it. We default to claude-sonnet-4-6
# because it matches the canonical DB-synced model_id directly (no alias
# resolution required). The earlier default of claude-sonnet-4-5 relied
# on a short-alias that was missing in prod for orgs whose Anthropic
# catalog used the undelimited 8-digit date suffix (20250929) — see
# KNOWN-ISSUES #38 + the new -\d{8}$ alias rule in gateway.py.
# Override with ORIGAMI_MODEL env var to pin a specific model id.
ORIGAMI_MODEL = os.getenv("ORIGAMI_MODEL", "claude-sonnet-4-6")
# Output budget for the planning response. Multi-agent plans where each
# create_agent carries a multi-paragraph system_prompt routinely exceed
# 4K tokens once you account for JSON serialization overhead of tool_use
# blocks. Undersized budgets cause Claude to either truncate the longest
# tool calls (typically create_agent ones) or — observed in PROD on the
# deal-review 4-agent prompt — degrade entirely to text-mode "here's the
# plan" output with no tool_use blocks at all. 8192 is the current cap on
# Claude Sonnet output; we use the full budget on planning.
ORIGAMI_MAX_TOKENS = int(os.getenv("ORIGAMI_MAX_TOKENS", "8192"))
# Bumped 5 → 8 (2026-06-12) to give headroom for up to 3
# committed-without-invoke corrections PLUS plan-validation retries
# PLUS the actual plan emission, all within one turn. The model
# false-completes several times in a row on multi-step builds; the
# retry loop needs room to keep correcting until it actually invokes.
ORIGAMI_MAX_TOOL_ITERATIONS = 8
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

When the user asks "how do I call this agent from my app?", "show me a \
snippet for <agent>", "how do I integrate <agent>", or anything similar, \
use `show_integration_guide(agent_name="<name>")`. The tool returns the \
endpoint, auth pattern, and copy-paste snippets in curl / Python / TypeScript \
with the agent's UUID already wired in. After the tool returns, paste the \
recommended snippet into your reply (use the language they asked for, or \
default to curl if unspecified) and remind them where to mint the PAT.

When the user asks about Enterprise — "what do we get on Enterprise", \
"does this support SSO / VPC / SOC-2", "how does this work for an enterprise \
team", or any procurement / security-review framing — use \
`show_enterprise_options(category="<security|compliance|scale|governance|support|all>")`. \
The tool returns three honest buckets: available today, partial/gated, and \
roadmap. NEVER pitch roadmap items as deliverable on a specific date. If \
the user asks for something not on either list, route them to \
hello@trybonito.com instead of guessing.

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
mint a gateway key, create a project), use the appropriate write tool. The \
orchestrator will automatically PAUSE before executing — it builds a plan card \
from your tool calls and shows the user a Deploy / Edit / Cancel choice. Your \
job is to propose the right tools with the right params; the user confirms.

IMPORTANT: when the user asks for a single write action, DO call the \
appropriate tool. Don't second-guess, don't refuse, don't ask for \
clarification on simple requests. Examples:
  "mint me a gateway key called X"       → call mint_gateway_key(name="X")
  "create a project called X"            → call create_project(name="X")
  "spin up a KB named X"                 → call create_kb(name="X")
  "make an agent called X with prompt Y" → call create_agent(name="X", system_prompt="Y")

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
LLM does NOT need to know the values up-front.

REFERENCING EXISTING RESOURCES BY NAME: when the user names an existing \
KB or agent (not one created earlier in this same plan), you do NOT \
need to look up the UUID first. Pass the display name in `kb_name` or \
`agent_name` and the tool resolves it server-side:

  upload_to_kb(kb_name="foundations-investor-thesis", documents=[...])
  link_kb_to_agent(agent_name="foundations-intro-bot", kb_name="foundations-investor-thesis")

Use kb_id / agent_id when you already have the UUID (e.g. from a \
${step_N.field} reference earlier in the same plan). Use the *_name \
form whenever the user mentions a resource by name — it saves a round \
trip and there's no UUID for the LLM to hallucinate.

CRITICAL — DO NOT pass BOTH agent_id (or kb_id) AND a different *_name \
in the same call. If the names refer to different agents than the UUID, \
the tool will REFUSE the call with id_name_mismatch. When linking the \
SAME KB to multiple agents in one plan, prefer to pass ONLY agent_name \
for each link (e.g. link_kb_to_agent(kb_name="X", agent_name="agent-A"), \
link_kb_to_agent(kb_name="X", agent_name="agent-B"), etc.). Names are \
unambiguous in this case.

WIRING AGENTS TOGETHER: to set up handoff / escalation / data_feed / \
trigger connections BETWEEN agents, ALWAYS use the connect_agents tool. \
Never try to use update_agent for connections — update_agent only \
modifies properties of a single agent (name, prompt, model, etc.), not \
relationships.

═══════════════════════════════════════════════════════════════════
DEPENDENCY RULE — INVOKE create_* BEFORE INVOKING wire/link
═══════════════════════════════════════════════════════════════════

This is about which TOOL INVOCATIONS go in your tool_calls array, \
in what order. It is NOT about how to respond in text. Do not narrate \
this. Do not list these in markdown. Invoke them.

Every agent, KB, or project referenced by a connect_agents, \
link_kb_to_agent, or upload_to_kb invocation must be created by a \
create_agent / create_kb / create_project invocation earlier in the \
SAME tool_calls array (or already exist in the org). If neither, the \
platform's plan validator will reject the plan and ask you to re-emit \
with the missing creates. So in a multi-agent build request, invoke \
all the create_agent tools first, then the connect_agents tools, then \
the link_kb_to_agent tools — all in one tool_calls array on one \
response.

OUTPUT BUDGET: if you cannot fit all required create_agent \
invocations alongside the wire/link invocations within your output \
budget, invoke a SMALLER set of create_agents this turn (just the hub, \
for example) and tell the user the rest will need a follow-up. Never \
invoke a connect_agents or link_kb_to_agent that references an agent \
the same tool_calls array did not create.

═══════════════════════════════════════════════════════════════════
ABSOLUTE RULE — INVOKE TOOLS FOR EVERY BUILD REQUEST
═══════════════════════════════════════════════════════════════════

If the user uses ANY of these verbs — create, build, make, spin up, \
mint, deploy, set up, add, link, wire, connect, attach, update — you \
MUST invoke the corresponding tool(s) by calling them. The platform \
generates the plan card from your tool invocations. WITHOUT TOOL \
INVOCATIONS, NO PLAN CARD RENDERS AND THE USER HAS NOTHING TO DEPLOY.

Examples of the right pattern:

  User: "create a project called foo"
    → invoke create_project(name="foo")

  User: "build me a wheel with hub plus 3 spokes"
    → invoke create_agent for hub, create_agent x3 for spokes,
      connect_agents x3 for handoffs

  User: "mint a gateway key called bar"
    → invoke mint_gateway_key(name="bar")

NEVER describe what you "would do" in prose. NEVER write "Here's the \
plan", "Here's a plan to create that", "Let me set that up", \
"I'll get that started", "Setting that up now", or any similar \
commitment-without-action as a substitute for invoking tools. NEVER \
respond with a markdown numbered list of tool names. The user has no \
way to deploy text. They can only deploy invocations.

ANSWERS TO CLARIFYING QUESTIONS COUNT AS BUILD INSTRUCTIONS. If the \
context block in your input shows a previous assistant reply that \
asked "what should we call it?" / "what's it for?" / similar, and \
the user's current message provides that detail ("call it X", \
"it's for Y"), that IS the instruction to invoke. Do NOT respond \
with "Here's a plan to create that" — emit create_project(name="X", \
description="Y") or the matching tool. The clarifying question + \
the user's answer together ARE the build verb.

After you have invoked the tool(s), you may add ONE sentence of \
context if useful (e.g. "I've routed the spokes off the hub — let me \
know if you'd prefer escalation edges instead"). Do NOT enumerate the \
plan in prose after the tool calls — the plan card already shows it. \
Do NOT use the phrase "hit Deploy when ready" — the button appears \
automatically when you invoke a write tool. """


# ───────────────────────── Tool name aliases ────────────────────────
#
# Models routinely call write tools by what feels like a natural verb
# rather than the registered name. Map common aliases back to the real
# tool name BEFORE TOOL_REGISTRY lookups so the dispatcher, plan-card
# builder, and execute_plan all agree.
TOOL_NAME_ALIASES: dict[str, str] = {
    "create_connection": "connect_agents",
    "create_agent_connection": "connect_agents",
    "connect_agent": "connect_agents",
    "wire_agents": "connect_agents",
    "handoff": "connect_agents",
}


def _resolve_tool_name(name: str | None) -> str:
    """Map an LLM-emitted tool name through the alias table."""
    n = (name or "").strip()
    return TOOL_NAME_ALIASES.get(n, n)


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


# ──────────────────── Plan dependency validator ────────────────────
#
# Built to catch the failure mode where the planner emits connect_agents /
# link_kb_to_agent / upload_to_kb tool calls that reference agents or KBs
# by NAME that no create_agent / create_kb call in the same response
# makes. This happens silently in PROD with complex prompts (multi-agent
# wheels with multi-paragraph system_prompts) because the model has to
# fit the entire plan in a single response within ORIGAMI_MAX_TOKENS,
# and the longer create_agent calls get truncated while the shorter
# connect/link calls make it through. The result is a plan that looks
# complete but every wire/link step fails with "agent X not found" or
# "kb K not found" at execution time.
#
# This validator runs BEFORE the plan is saved + emitted. If it finds
# dangling references, the orchestrator injects synthetic tool_result
# messages plus a user-message with the validation errors and lets the
# model retry inside the remaining MAX_TOOL_ITERATIONS budget. The model
# typically corrects itself in one extra iteration.


async def _validate_plan_dependencies(
    plan_changes: list[PlanChange],
    *,
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[str]:
    """Return list of human-readable error strings; [] means valid.

    For each connect_agents / link_kb_to_agent / upload_to_kb step that
    references a resource BY NAME (not by UUID), the name must either
    be created earlier in this plan OR already exist in the org. If
    neither, append an error.
    """
    created_agents: set[str] = set()
    created_kbs: set[str] = set()
    for c in plan_changes:
        action = _resolve_tool_name(c.action)
        params = c.params or {}
        if action == "create_agent":
            name = (params.get("name") or "").strip()
            if name:
                created_agents.add(name)
        elif action == "create_kb":
            name = (params.get("name") or "").strip()
            if name:
                created_kbs.add(name)

    errors: list[str] = []

    for idx, c in enumerate(plan_changes):
        action = _resolve_tool_name(c.action)
        params = c.params or {}
        if action == "connect_agents":
            # Both source and target need to resolve. Accept either
            # source_agent_* / from_agent_* and target_agent_* /
            # to_agent_*.
            for role, id_keys, name_keys in (
                (
                    "source",
                    ("source_agent_id", "from_agent_id"),
                    ("source_agent_name", "from_agent_name"),
                ),
                (
                    "target",
                    ("target_agent_id", "to_agent_id"),
                    ("target_agent_name", "to_agent_name"),
                ),
            ):
                if any(params.get(k) for k in id_keys):
                    continue  # UUID supplied
                name = ""
                for k in name_keys:
                    v = (params.get(k) or "").strip()
                    if v:
                        name = v
                        break
                if not name:
                    continue
                if name in created_agents:
                    continue
                if await _agent_exists_in_org(db, org_id=org_id, name=name):
                    continue
                errors.append(
                    f"step {idx + 1} ({c.action}): {role} agent '{name}' is "
                    f"neither created earlier in this plan nor exists in the "
                    f"org. Emit create_agent(name='{name}', ...) before this "
                    f"connect_agents call."
                )

        elif action == "link_kb_to_agent":
            if not params.get("agent_id"):
                agent_name = (params.get("agent_name") or "").strip()
                if agent_name and agent_name not in created_agents:
                    if not await _agent_exists_in_org(db, org_id=org_id, name=agent_name):
                        errors.append(
                            f"step {idx + 1} ({c.action}): agent "
                            f"'{agent_name}' is neither created earlier in "
                            f"this plan nor exists in the org. Emit "
                            f"create_agent(name='{agent_name}', ...) first."
                        )
            if not params.get("kb_id"):
                kb_name = (params.get("kb_name") or "").strip()
                if kb_name and kb_name not in created_kbs:
                    if not await _kb_exists_in_org(db, org_id=org_id, name=kb_name):
                        errors.append(
                            f"step {idx + 1} ({c.action}): kb '{kb_name}' is "
                            f"neither created earlier in this plan nor "
                            f"exists in the org. Emit "
                            f"create_kb(name='{kb_name}', ...) first."
                        )

        elif action == "upload_to_kb":
            if not params.get("kb_id"):
                kb_name = (params.get("kb_name") or "").strip()
                if kb_name and kb_name not in created_kbs:
                    if not await _kb_exists_in_org(db, org_id=org_id, name=kb_name):
                        errors.append(
                            f"step {idx + 1} ({c.action}): kb '{kb_name}' is "
                            f"neither created earlier in this plan nor "
                            f"exists in the org."
                        )

    # Dedup
    seen: set[str] = set()
    deduped: list[str] = []
    for e in errors:
        if e in seen:
            continue
        seen.add(e)
        deduped.append(e)
    return deduped


async def _agent_exists_in_org(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    name: str,
) -> bool:
    from sqlalchemy import select
    from app.models.agent import Agent

    row = await db.execute(
        select(Agent.id)
        .where(Agent.org_id == org_id, Agent.name == name)
        .limit(1)
    )
    return row.scalar_one_or_none() is not None


async def _kb_exists_in_org(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    name: str,
) -> bool:
    from sqlalchemy import select
    from app.models.knowledge_base import KnowledgeBase

    row = await db.execute(
        select(KnowledgeBase.id)
        .where(KnowledgeBase.org_id == org_id, KnowledgeBase.name == name)
        .limit(1)
    )
    return row.scalar_one_or_none() is not None


# ────────────────────────── Orchestrator entry point ──────────────────────────


async def run_origami_turn(
    *,
    user: User,
    message: str,
    conversation_id: Optional[str],
    project_id: Optional[uuid.UUID] = None,
    db: AsyncSession,
    system_prompt: Optional[str] = None,
    extra_context: Optional[str] = None,
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

    OPTIONAL PARAMS:
        system_prompt — override the default Origami system prompt. Used by
            Bonito Studio to swap in a BDR-flavored prompt while reusing the
            same orchestrator + tool registry. Defaults to SYSTEM_PROMPT.
        extra_context — prepended to user_content ahead of platform_context
            and memwright. Used by Bonito Studio to inject the org snapshot
            (providers / agents / KBs / usage) so the first turn opens with
            something specific. Plain text; the model treats it as context.
    """
    active_system_prompt = system_prompt or SYSTEM_PROMPT
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

    # Persist the user message so the history view can find it. Use a
    # synthetic conversation_id if the client didn't provide one — that
    # way every turn still appears in history under SOME conversation.
    effective_conversation_id = conversation_id or str(uuid.uuid4())
    await origami_messages.record_user_message(
        db=db,
        org_id=org_id,
        user_id=user.id,
        project_id=project_id,
        conversation_id=effective_conversation_id,
        session_id=session_id,
        content=message,
    )

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

    # Pull relevant chunks from the PLATFORM-SHARED bonito-knowledge KB so
    # the model can answer "how does Bonito work" questions without
    # guessing. One corpus serves every org (it's just platform docs).
    # Empty string if the platform KB hasn't been seeded yet — fail open.
    platform_context = ""
    try:
        from app.services.origami import bonito_knowledge as bk
        bk_chunks = await bk.retrieve_context_for_query(
            db=db, query=message, top_k=3, min_score=0.4
        )
        platform_context = bk.format_context_for_prompt(bk_chunks)
    except Exception:
        logger.exception("bonito-knowledge retrieval failed (non-fatal)")
        platform_context = ""

    user_content = message
    if memory_context:
        user_content = f"{memory_context}\n\nUser message: {message}"
    if platform_context:
        user_content = f"{platform_context}\n\n{user_content}"
    if extra_context:
        # Studio injects the org snapshot here so the model can ground its
        # first reply in actual provider/agent/KB counts and recent usage.
        user_content = f"{extra_context}\n\n{user_content}"

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
    # Track whether ANY iteration in this turn has already emitted user-
    # visible text. Used to suppress the silent-prompt fallback on iter 2+
    # when iter 1 already gave the user something — otherwise we'd render
    # two bubbles (real reply + "I didn't quite catch that") for the same turn.
    emitted_visible_text = False
    # How many times we've injected a "you committed but didn't invoke"
    # correction this turn. The model sometimes false-completes 2-3 times
    # in a row, so a single retry isn't enough — allow several, capped to
    # leave iteration budget for the actual build + any plan-validation
    # retry that follows.
    committed_retry_count = 0
    # Accumulate write tool_calls ACROSS iterations into one plan. The
    # model uses the standard tool-use protocol: it emits a batch of tool
    # calls with finish_reason="tool_calls" and waits for results before
    # emitting the rest (e.g. create_project + create_kb + create_agent,
    # then expects results before emitting link_kb_to_agent). Origami's
    # plan-card flow doesn't execute inline, so we inject SYNTHETIC
    # results and keep looping to collect the remaining calls — building
    # ONE complete plan from all batches. Without this the trailing tool
    # calls (link/connect/the last agents) silently vanish from the plan.
    accumulated_plan_changes: list[PlanChange] = []
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
                system=active_system_prompt,
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

        # Step 1: ALWAYS strip <thinking> blocks from the content first.
        # The model uses these for chain-of-thought reasoning but the user
        # should never see them. Also strip BEFORE the tool-call parser
        # runs because the model sometimes hides tool-call markup inside
        # thinking blocks too (which would confuse the parser AND surface
        # internal reasoning to the user).
        had_thinking = False
        if content and _THINKING_RE.search(content):
            had_thinking = True
            content = _THINKING_RE.sub("", content).strip()
            accumulated_content = content

        # Step 2: fallback parse for upstreams that don't normalize tool
        # calls into structured tool_calls[]. They embed them in the
        # content as <tool_call>{...}</tool_call>, <function>...,
        # or <invoke name="..."><parameter ...>...</parameter></invoke>.
        stripped_inline = False
        if not tool_calls and content:
            inline = _extract_inline_tool_calls(content)
            if inline:
                tool_calls = inline

        # ALWAYS strip every known tool-call leak shape from visible
        # content. Some models emit XML wrappers (<function_calls>),
        # some emit bare JSON ({"name": "create_X", ...}), some emit
        # code-fenced JSON (```json {...}```), some emit Python-style
        # function-call syntax (invoke_agent("studio-x")). The unified
        # sanitizer catches all of them; the regexes are whitelist-
        # gated against real platform tool names so they can't
        # false-strip arbitrary JSON the user might discuss.
        if content:
            stripped = _sanitize_tool_call_leaks(content)
            if stripped != content:
                accumulated_content = stripped
                content = stripped
                stripped_inline = True

        # Step 3: log if we caught the model doing things behind the scenes.
        # Helps diagnose why a prompt produced no visible response.
        if had_thinking or stripped_inline:
            logger.debug(
                "Origami iteration %d: thinking=%s, inline_tool_call=%s, "
                "tool_calls_after_parse=%d, content_len_after=%d",
                iteration, had_thinking, stripped_inline,
                len(tool_calls), len(content),
            )

        # Accumulate token usage from the final usage chunk. Some upstreams
        # (notably Bedrock via LiteLLM) don't honor stream_options.include_usage
        # consistently — when the gateway doesn't echo a usage chunk, fall back
        # to a word-count-based estimate so the metering row isn't $0.
        prompt_tokens = int(chunk_usage.get("prompt_tokens") or 0)
        completion_tokens = int(chunk_usage.get("completion_tokens") or 0)

        if prompt_tokens == 0:
            # Rough estimate: 1.3 tokens per word across system + tools + history
            sys_words = len(active_system_prompt.split())
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
        if content:
            emitted_visible_text = True

        if not tool_calls:
            # ── FINALIZE ACCUMULATED MULTI-BATCH PLAN ──────────────
            # If we've been collecting write tool calls across batches
            # and the model just emitted a text wrap-up (no new tools),
            # the build is complete — finalize the plan from everything
            # accumulated. Without this, a multi-batch build's text
            # "all done!" wrap-up would fall through to the retry/
            # fallback path and the plan would never render.
            if accumulated_plan_changes:
                plan_changes = accumulated_plan_changes
                validation_errors = await _validate_plan_dependencies(
                    plan_changes, db=db, org_id=org_id,
                )
                if validation_errors:
                    logger.warning(
                        "Origami multi-batch plan has dependency warnings "
                        "(%d) at finalize. Emitting anyway. errors=%s",
                        len(validation_errors), validation_errors[:5],
                    )
                    yield OrigamiEvent("plan_warning", {
                        "code": "dependency_errors",
                        "errors": validation_errors,
                        "message": (
                            "Some plan steps reference resources not created "
                            "in this plan. The affected steps may fail on "
                            "deploy."
                        ),
                    })
                plan = PlanCard(
                    id=uuid.uuid4(),
                    session_id=session_id,
                    intent=message[:500] if message else "(no intent recorded)",
                    changes=plan_changes,
                    status=PlanCardStatus.AWAITING_CONFIRMATION,
                )
                await plan_store.save_plan(
                    plan=plan, user_id=user.id, org_id=org_id,
                    project_id=project_id, conversation_id=conversation_id,
                    user_message=message,
                )
                plan_dict = plan.model_dump(mode="json")
                yield OrigamiEvent("plan_ready", {"plan_card": plan_dict})
                yield OrigamiEvent("awaiting_confirmation", {
                    "plan_card_id": str(plan.id),
                })
                await origami_messages.record_plan_message(
                    db=db, org_id=org_id, user_id=user.id,
                    project_id=project_id,
                    conversation_id=effective_conversation_id,
                    session_id=session_id, plan_card=plan_dict,
                )
                await _record_turn(
                    db=db, user=user, org_id=org_id, project_id=project_id,
                    session_id=session_id, conversation_id=conversation_id,
                    message=message, input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                    tool_calls_count=total_tool_calls,
                    model_used=last_model_used, status="success",
                    finish_reason="plan_ready", tier=tier,
                    started_at_ms=started_at_ms,
                )
                return

            # ── COMMITTED-WITHOUT-INVOKE RETRY ─────────────────────
            # The dominant Claude multi-step failure: the model emits
            # "On it — creating the KB, the agent, then wiring them
            # together" with no actual tool calls. Measured 80% failure
            # rate on multi-step builds (test 2026-06-12). Prompt-list
            # whack-a-mole doesn't fix it; the model finds new commit-
            # without-invoke phrasings faster than we can list them.
            # Code-level fix: when the user asked to build AND the
            # response sounds committal AND we have iteration budget,
            # inject a synthetic correction message and re-run. The
            # model corrects itself on the next iteration most of the
            # time. Gated on iteration == 0 so this can only fire once
            # per turn (no infinite loops).
            iterations_left = ORIGAMI_MAX_TOOL_ITERATIONS - 1 - iteration
            # Retry condition: user wanted to build AND the response isn't
            # a clarifying question. There's no third valid state — the
            # model either built (tool_calls non-empty, handled below)
            # OR asked a question (correct, no retry) OR dead-chatted
            # (this branch). Inverting the gate from "looks committal"
            # to "isn't a question" catches every false-completion shape
            # without needing a phrase list. The phrase + TS-leak helpers
            # remain for diagnostic logging.
            is_q = _is_clarifying_question(accumulated_content)
            claims_done = _claims_false_completion(accumulated_content)
            # Retry when the user wanted a build and the model didn't
            # invoke, UNLESS it asked a genuine clarifying question with
            # NO false completion claim. A reply that both claims
            # completion AND asks a follow-up ("Project is ready — want
            # me to add agents?") is a lie + an offer; the resource was
            # never created, so we retry despite the trailing question.
            # Allow up to MAX_COMMITTED_RETRIES corrections because the
            # model sometimes false-completes several times in a row.
            MAX_COMMITTED_RETRIES = 3
            if (
                committed_retry_count < MAX_COMMITTED_RETRIES
                and iterations_left > 0
                and _user_wants_build(message)
                and (claims_done or not is_q)
            ):
                committed_retry_count += 1
                logger.warning(
                    "Origami committed-without-invoke retry #%d "
                    "(iter=%d, user=%s): content=%r message=%r",
                    committed_retry_count,
                    iteration,
                    str(user.id),
                    accumulated_content[:120],
                    message[:120],
                )
                # Inject the model's prior reply + a correction prompt.
                # Escalate the firmness on repeat failures.
                if committed_retry_count == 1:
                    correction = (
                        "You committed to building but emitted no tool "
                        "calls — the plan card won't render and the user "
                        "has nothing to deploy. Emit the tool calls NOW "
                        "as structured tool_calls. Per the dependency "
                        "rule, all create_* invocations come first, then "
                        "connect_agents / link_kb_to_agent / upload_to_kb "
                        "invocations referencing them with "
                        "${step_N.field} template refs. Use the "
                        "structured tool_calls field — do NOT write the "
                        "calls as ```json``` blocks or function-call "
                        "syntax in the visible reply."
                    )
                else:
                    correction = (
                        "STOP. You STILL haven't emitted any tool calls. "
                        "Do not write ANY prose this turn. Your ENTIRE "
                        "response must be structured tool_calls and nothing "
                        "else. Emit one tool call per resource the user "
                        f"asked for in: '{message[:200]}'. create_* first, "
                        "then connect/link. No 'I'll', no 'done', no "
                        "explanation — just the tool calls."
                    )
                # Inject the original user request again so the model
                # re-anchors on what to build (not just on the scolding).
                messages.append(
                    {"role": "assistant", "content": accumulated_content}
                )
                messages.append({"role": "user", "content": correction})
                continue  # Re-enter loop with the correction

            # Synthesize a friendly summary if the model went silent after a
            # tool ran, OR if the content we got back looks like nothing but
            # tool-call markup that couldn't be parsed (Bedrock + Opus
            # picks inconsistent formats — even when one iteration's call
            # was extracted, the follow-up sometimes hallucinates a different
            # markup format that bypasses the parser).
            was_synthesized = False
            looks_like_markup = bool(content) and (
                "<function>" in content or
                "<tool_call>" in content or
                "<invoke" in content or
                "<parameter" in content or
                "<thinking" in content
            )
            if (not content or looks_like_markup) and total_tool_calls > 0 and results:
                content = _synthesize_tool_summary(results)
                accumulated_content = content
                was_synthesized = True
                yield OrigamiEvent("message_complete", {
                    "text": content,
                    "synthesized": True,
                })
            elif not content and not emitted_visible_text:
                # The model went silent and we have no tool results to
                # summarize AND no earlier iteration in this turn already
                # emitted text — emit a friendly fallback so the user isn't
                # staring at an empty chat. This happens occasionally with
                # Bedrock-routed Claude models on certain prompts; the
                # debug log captures the raw response for diagnosis.
                #
                # The emitted_visible_text guard is what prevents the
                # double-bubble bug where iter 1 said "Here's the plan..."
                # and iter 2 went silent → user saw a real reply followed
                # by "I didn't quite catch that".
                logger.warning(
                    "Origami silent response — user=%s, iteration=%d, "
                    "last_finish_reason=%s. Emitting fallback.",
                    str(user.id), iteration, finish_reason,
                )
                content = (
                    "I didn't quite catch that — could you rephrase? "
                    "I can help you create projects, knowledge bases, agents, "
                    "or gateway keys, attach KBs to agents, upload documents, "
                    "or look up your org state, usage, and tier access."
                )
                accumulated_content = content
                was_synthesized = True
                yield OrigamiEvent("message_complete", {
                    "text": content,
                    "synthesized": True,
                    "fallback": True,
                })
            # Persist the final assistant message (model or synthesized)
            if content:
                await origami_messages.record_assistant_message(
                    db=db,
                    org_id=org_id,
                    user_id=user.id,
                    project_id=project_id,
                    conversation_id=effective_conversation_id,
                    session_id=session_id,
                    content=content,
                    model_used=last_model_used,
                    synthesized=was_synthesized,
                )
            final_finish_reason = finish_reason
            yield OrigamiEvent("done", {
                "finish_reason": finish_reason,
                "iteration": iteration,
            })
            # Store the turn in Memwright so future turns can recall context.
            # No-op for zero-budget models (Haiku/Flash); never blocks.
            # IMPORTANT: sanitize assistant_msg before storing so Memwright
            # never holds tool-call leak shapes that would feed back to the
            # model on recall and re-pollute future turns. The live strip
            # above catches most leaks before display; this is the last line
            # of defense for memory contamination (Studio bug 2026-06-12).
            if conversation_id and accumulated_content:
                try:
                    mw = _get_memwright()
                    sanitized_memory = _sanitize_tool_call_leaks(accumulated_content)
                    if sanitized_memory:
                        await mw.store(
                            session_id=conversation_id,
                            agent_id=ORIGAMI_MEMWRIGHT_AGENT_ID,
                            org_id=str(org_id),
                            user_msg=message,
                            assistant_msg=sanitized_memory,
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
            (TOOL_REGISTRY.get(_resolve_tool_name(tc.get("function", {}).get("name", ""))) and
             TOOL_REGISTRY[_resolve_tool_name(tc["function"]["name"])].is_write)
            for tc in tool_calls
        )

        if has_write_tool:
            current_changes: list[PlanChange] = []
            for tc in tool_calls:
                fn = tc.get("function", {})
                raw_name = fn.get("name", "")
                tname = _resolve_tool_name(raw_name)
                tcls = TOOL_REGISTRY.get(tname)
                # DEFENSIVE: skip tool calls whose resolved name isn't a
                # real tool. The model occasionally emits a malformed
                # call whose `name` is a RESOURCE NAME instead of a tool
                # (e.g. name="code-reviewer-12729"). If we let that become
                # a plan step, it (a) fails at execute time as unknown_tool
                # and (b) — worse — shifts every later step's index by one,
                # which breaks ${step_N.field} template refs downstream.
                # Dropping it keeps the plan clean and the indices aligned.
                if tcls is None:
                    logger.warning(
                        "Origami: dropping non-tool plan change name=%r "
                        "(resolved=%r) — not in TOOL_REGISTRY. Likely a "
                        "resource name the model mislabeled as a tool.",
                        raw_name, tname,
                    )
                    continue
                try:
                    p = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    p = {}
                p = sanitize_params(p)
                current_changes.append(PlanChange(
                    action=tname,
                    params=p,
                    is_write=bool(tcls.is_write),
                    summary=tcls.description,
                ))

            # Accumulate this batch into the running plan. The model emits
            # tool calls in batches and waits for results; we collect them
            # all into one plan instead of finalizing on the first batch.
            # Dedup against what's already accumulated — the model
            # sometimes re-emits a call it already made when it continues.
            def _change_key(c: PlanChange) -> tuple:
                name = (c.params or {}).get("name")
                return (c.action, name) if name else (c.action, json.dumps(c.params, sort_keys=True))
            seen_keys = {_change_key(c) for c in accumulated_plan_changes}
            for c in current_changes:
                k = _change_key(c)
                if k not in seen_keys:
                    accumulated_plan_changes.append(c)
                    seen_keys.add(k)

            # ── CONTINUE-COLLECTING gate ──────────────────────────────
            # finish_reason == "tool_calls" means the model emitted tool
            # calls and EXPECTS results before continuing — it may have
            # more calls to make (e.g. link_kb_to_agent after the agent).
            # Inject synthetic success results for THIS batch and loop so
            # the model can emit the rest. Cap by iteration budget. When
            # the model is truly done it emits finish_reason != tool_calls
            # (a plain text wrap-up) and we fall through to finalize.
            iters_left_collect = ORIGAMI_MAX_TOOL_ITERATIONS - 1 - iteration
            if finish_reason == "tool_calls" and iters_left_collect > 0:
                # Synthetic result per tool_call: success with a placeholder
                # id keyed by step so downstream ${step_N.field} refs the
                # model writes still make sense. Real ids are assigned at
                # execute time; planning only needs the shape.
                for off, tc in enumerate(tool_calls):
                    step_no = len(accumulated_plan_changes) - len(tool_calls) + off + 1
                    fname = _resolve_tool_name(tc.get("function", {}).get("name", ""))
                    placeholder = {
                        "success": True,
                        "status": "queued_in_plan",
                        "note": (
                            "Queued in the plan card — will execute on deploy. "
                            "Reference my outputs with template refs like "
                            f"${{step_{step_no}.project_id}} / "
                            f"${{step_{step_no}.kb_id}} / "
                            f"${{step_{step_no}.agent_id}}."
                        ),
                    }
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id", ""),
                        "content": json.dumps(placeholder),
                    })
                # Nudge the model to emit any REMAINING build steps (or to
                # finish if there are none).
                messages.append({
                    "role": "user",
                    "content": (
                        "Those are queued in the plan. If the original "
                        "request needs MORE steps (e.g. link_kb_to_agent, "
                        "connect_agents, additional agents), emit them now "
                        "as tool calls using ${step_N.field} refs to the "
                        "resources above. If the plan is complete, just say "
                        "so briefly — do not repeat tool calls already made."
                    ),
                })
                continue  # collect the next batch

            # Model is done emitting tool calls — finalize from the FULL
            # accumulated set (all batches), not just this iteration's.
            plan_changes = accumulated_plan_changes

            # ── Validate plan dependencies BEFORE emitting plan_ready.
            #
            # Catches the failure mode where the model emitted
            # connect_agents / link_kb_to_agent calls that reference
            # agents/KBs by name without emitting the corresponding
            # create_agent / create_kb calls (typically because the
            # output budget got tight and the longer create_agent calls
            # were dropped). When that happens, inject synthetic
            # tool_result messages plus a user-message describing the
            # errors and let the model retry within the remaining
            # iteration budget. The model corrects itself most of the
            # time on the very next iteration.
            validation_errors = await _validate_plan_dependencies(
                plan_changes, db=db, org_id=org_id,
            )
            iterations_left = ORIGAMI_MAX_TOOL_ITERATIONS - 1 - iteration
            if validation_errors and iterations_left > 0:
                logger.info(
                    "Origami plan validation failed (iteration %d, %d errors); "
                    "injecting feedback for model retry. errors=%s",
                    iteration, len(validation_errors), validation_errors[:3],
                )
                yield OrigamiEvent("plan_revision", {
                    "iteration": iteration,
                    "errors": validation_errors,
                    "iterations_left": iterations_left,
                })
                # Inject one tool_result per tool_call so the conversation
                # state stays valid for the next iteration.
                for tc in tool_calls:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id", ""),
                        "content": json.dumps({
                            "status": "deferred",
                            "reason": "plan_validation_pending",
                        }),
                    })
                # The model is being asked to RE-EMIT the full plan, so
                # clear the accumulator — the next batch replaces it
                # rather than appending (avoids double-counting).
                accumulated_plan_changes = []
                messages.append({
                    "role": "user",
                    "content": (
                        "Your plan has dependency errors — it references "
                        "agents or KBs by name that no create_* call in the "
                        "same response makes:\n\n"
                        + "\n".join(f"  • {e}" for e in validation_errors)
                        + "\n\nRe-emit the FULL plan including the missing "
                        "create_agent / create_kb calls. Per the dependency "
                        "rules, ALL create_* calls must come BEFORE any "
                        "connect_agents / link_kb_to_agent calls in the same "
                        "response. If fitting them all would force you to "
                        "truncate, emit a smaller plan covering fewer agents "
                        "and tell me what's left for a follow-up."
                    ),
                })
                # Continue the iteration loop; model gets the feedback.
                continue

            if validation_errors:
                # Out of iteration budget — log and emit a warning event
                # but still surface the plan so the user sees the attempt.
                logger.warning(
                    "Origami plan validation failed on final iteration "
                    "(%d errors, no retries left). Emitting plan with "
                    "warnings. errors=%s",
                    len(validation_errors), validation_errors[:5],
                )
                yield OrigamiEvent("plan_warning", {
                    "code": "dependency_errors",
                    "errors": validation_errors,
                    "message": (
                        "This plan references agents or KBs that aren't "
                        "created in the same plan. Deploy will fail on "
                        "the affected steps. Ask me to re-emit the plan "
                        "with explicit create_agent / create_kb calls."
                    ),
                })

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

            plan_dict = plan.model_dump(mode="json")
            yield OrigamiEvent("plan_ready", {
                "plan_card": plan_dict,
            })
            yield OrigamiEvent("awaiting_confirmation", {
                "plan_card_id": str(plan.id),
            })
            # Persist the plan so it shows up in history
            await origami_messages.record_plan_message(
                db=db,
                org_id=org_id,
                user_id=user.id,
                project_id=project_id,
                conversation_id=effective_conversation_id,
                session_id=session_id,
                plan_card=plan_dict,
            )

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
            tool_name = _resolve_tool_name(fn.get("name", ""))
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
        # Resolve aliases at execute-time too, in case the plan was
        # built under an older orchestrator that didn't normalize.
        resolved_action = _resolve_tool_name(change.action)
        tool_cls = TOOL_REGISTRY.get(resolved_action)
        if not tool_cls:
            yield OrigamiEvent("tool_failed", {
                "tool_name": change.action,
                "step": step_idx,
                "error": "unknown_tool",
            })
            # Write a failed audit row so post-hoc audits show the gap
            # (previously unknown tools were invisible from origami_audit_log).
            try:
                await metering.record_origami_audit(
                    db=db, org_id=user.org_id, user_id=user.id,
                    og_token_id=None, project_id=project_id,
                    session_id=session_id,
                    plan_card_id=uuid.UUID(plan_card_id),
                    intent_summary=plan.intent, tool_name=change.action,
                    tool_params=change.params, tier_at_time=tier,
                    confirmation="user_clicked", status="failed",
                    error=f"unknown_tool: '{change.action}' not in registry (after alias resolution)",
                )
            except Exception:
                logger.exception("execute_plan: failed to audit unknown_tool")
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
            # Heuristic: if a coupled-id tool still has unset / unresolved
            # ids, infer them from the most recent matching create result.
            # Covers link_kb_to_agent (agent_id/kb_id) AND create_agent
            # (project_id) — both are the common chained-build failure
            # where the model's ${step_N} ref didn't resolve cleanly.
            params = _heuristic_fill_link_params(change.action, params, step_results)
            params = _heuristic_fill_project_id(change.action, params, step_results)
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
                # ── AUTO-RETRY with smart param repair ──────────────────
                # Try to infer corrected params and re-run once before
                # giving up. Solves the common model errors (missing
                # source_agent_name, bare-name agent_id, etc).
                repair = _repair_failed_step(
                    resolved_action, params, result, plan.changes, step_idx, step_results,
                )
                if repair is not None:
                    repaired_params, repair_note = repair
                    yield OrigamiEvent("tool_retried", {
                        "tool_name": change.action,
                        "step": step_idx,
                        "repair": repair_note,
                    })
                    try:
                        result = await instance.execute(
                            org_id=user.org_id, user=user,
                            params=repaired_params, db=db,
                        )
                        # Update step_results with the new outcome
                        step_results[-1] = result if isinstance(result, dict) else {}
                        results[-1] = {"action": change.action, "result": result}
                        params = repaired_params
                        tool_succeeded = result.get("success", True) if isinstance(result, dict) else True
                    except Exception as retry_e:
                        logger.exception("execute_plan: retry of %s also failed", change.action)
                        tool_succeeded = False

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
                # Retry succeeded — fall through to the tool_completed path below

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
    # `function_calls` is Anthropic's outer wrapper — the body holds one or
    # more <invoke> blocks (matched separately by _INVOKE_BLOCK_RE for
    # extraction). Including the wrapper here strips the leftover
    # `<function_calls>…</function_calls>` tags from the visible text so
    # they don't render in the chat bubble (Studio bug 2026-06-12).
    r"<(tool_call|tool_calls|function|function_call|function_calls|tool_use)>\s*(.*?)\s*</\1>",
    re.DOTALL,
)
_INVOKE_BLOCK_RE = re.compile(
    r'<invoke\s+name="([^"]+)">\s*(.*?)\s*</invoke>', re.DOTALL
)
_PARAM_RE = re.compile(
    r'<parameter\s+name="([^"]+)">\s*(.*?)\s*</parameter>', re.DOTALL
)

# Known platform tool names — used to build sanitizer regexes that only
# strip text matching a real tool, not arbitrary JSON the user might be
# discussing. Keep this list aligned with TOOL_REGISTRY + the wheel's
# invoke_agent. Adding a new platform tool? Add its name here too.
_PLATFORM_TOOL_NAMES = (
    "create_project|create_kb|create_agent|create_connection|connect_agents|"
    "link_kb_to_agent|upload_to_kb|update_agent|update_kb|mint_gateway_key|"
    "delete_project|view_usage|view_logs|list_org_state|list_available_models|"
    "list_deleted_projects|check_tier_access|configure_autoscaling|"
    "delegate_provider_connection|restore_project|show_enterprise_options|"
    "show_integration_guide|invoke_agent"
)
# Bare JSON tool-call leak — `{"name": "create_X", "parameters": {...}}` or
# `{"tool": "create_X", "params": {...}}`. Restricted to platform tool names
# so it can't false-match unrelated JSON. Also accepts list-wrapped form
# `[{"name": "X", ...}]` since Claude sometimes wraps in a list.
_BARE_JSON_TOOL_CALL_RE = re.compile(
    rf"""
    (?:\[\s*)?                                     # optional leading [
    \{{                                             # opening brace
    \s*"(?:name|tool|function_name)"\s*:\s*
    "(?:{_PLATFORM_TOOL_NAMES})"                    # tool name (whitelisted)
    \s*,?\s*                                        # optional comma
    "(?:parameters|params|arguments|input)"\s*:\s*
    \{{[^{{}}]*\}}                                  # params object (no nesting)
    \s*\}}                                          # closing brace
    (?:\s*\])?                                      # optional trailing ]
    """,
    re.VERBOSE | re.DOTALL,
)
# Code-fenced version of the same — `\`\`\`json {...} \`\`\``. Same
# whitelist so we don't strip arbitrary JSON snippets the user pastes.
_CODE_FENCED_TOOL_CALL_RE = re.compile(
    rf"""
    ```(?:json)?\s*
    (?:\[\s*)?\{{
    \s*"(?:name|tool|function_name)"\s*:\s*
    "(?:{_PLATFORM_TOOL_NAMES})"
    .*?
    \}}(?:\s*\])?\s*
    ```
    """,
    re.VERBOSE | re.DOTALL,
)
# Python-style function-call syntax — `invoke_agent("...")`, also handles
# any platform tool name to be safe: `create_project(name="X")`. The
# wheel's _FUNC_CALL_AGENT_RE is narrower (only invoke_agent + studio-x).
# This wider one catches every platform-tool-as-function-call leak.
_TOOL_FUNCTION_CALL_RE = re.compile(
    rf"\b(?:{_PLATFORM_TOOL_NAMES})\s*\([^)]*\)",
)
# TypeScript / JavaScript code-block leak. The model sometimes role-plays
# as a developer and emits something like:
#   ```typescript
#   import { createKb, createAgent, linkKbToAgent } from '@bonito/sdk';
#   await createKb({ name: 'x' });
#   ```
# instead of structured tool_calls. camelCase variants of platform tool
# names are the tell. We don't gate on the platform-name whitelist here
# because the regex is anchored to a code-fence — false positives on
# random TS snippets the user pasted are extremely unlikely.
_TS_TOOL_NAMES_CAMEL = (
    "createProject|createKb|createAgent|connectAgents|linkKbToAgent|"
    "uploadToKb|updateAgent|updateKb|mintGatewayKey|deleteProject|"
    "viewUsage|viewLogs|listOrgState|listAvailableModels|invokeAgent"
)
_TS_CODE_BLOCK_LEAK_RE = re.compile(
    rf"```(?:typescript|ts|javascript|js|tsx|jsx)?\s*"
    rf".*?(?:{_TS_TOOL_NAMES_CAMEL}|{_PLATFORM_TOOL_NAMES}).*?```",
    re.DOTALL | re.IGNORECASE,
)
# Standalone TS import line (without code fence) — the model sometimes
# emits just the import statement as plain text.
_TS_IMPORT_LEAK_RE = re.compile(
    rf"import\s*\{{[^}}]*(?:{_TS_TOOL_NAMES_CAMEL}|{_PLATFORM_TOOL_NAMES})"
    rf"[^}}]*\}}\s*from\s*['\"][^'\"]+['\"];?",
    re.IGNORECASE,
)


# Pattern detection for the "model committed to action but didn't
# invoke any tool" failure mode. Lowercased substring match for speed;
# both detectors run independently and the orchestrator only retries
# when BOTH fire (user wanted a build AND response sounds committal).

_BUILD_VERBS_USER = (
    "create",
    "build",
    "make",
    "spin up",
    "spin-up",
    "mint",
    "deploy",
    "wire",
    "link",
    "connect",
    "set up",
    "set-up",
    "add a",
    "upload",
    "attach",
)

_COMMITTAL_BUILD_PHRASES = (
    # Acknowledgment heads
    "on it",
    "i'll create",
    "i'll spin up",
    "i'll set up",
    "i'll mint",
    "i'll build",
    "i'll wire",
    "i'll link",
    "let me create",
    "let me spin",
    "let me set",
    "let me mint",
    "let me build",
    "let me wire",
    "let me link",
    # Future-tense build descriptions
    "creating the",
    "spinning up the",
    "wiring them",
    "linking the",
    "building the",
    "setting up the",
    "minting the",
    "wiring them together",
)


def _user_wants_build(message: str) -> bool:
    if not message:
        return False
    m = message.lower()
    return any(v in m for v in _BUILD_VERBS_USER)


def _looks_committal_to_build(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    # Conventional commitment phrases ("On it", "I'll create", …)
    if any(p in t for p in _COMMITTAL_BUILD_PHRASES):
        return True
    # OR the model role-played a developer and emitted TS/JS code that
    # references platform tools. Same outcome: response committed but
    # didn't actually invoke. Retry should fire.
    if _TS_CODE_BLOCK_LEAK_RE.search(text):
        return True
    if _TS_IMPORT_LEAK_RE.search(text):
        return True
    return False


def _is_clarifying_question(text: str) -> bool:
    """Roughly: did the model end its reply with a clarifying question?

    Used as the inverse gate for the committed-without-invoking retry.
    When the user asked to build something and the model didn't emit
    any tool calls, the response is EITHER (a) a clarifying question
    (correct behavior, no retry) OR (b) a dead chat masquerading as
    completion ("On it", "Done — X is created", code blocks, anything
    else). Any non-question reply triggers the retry.
    """
    if not text:
        return False
    stripped = text.strip()
    if not stripped:
        return False
    # Standard question mark anywhere in the last quarter of the reply
    tail = stripped[-max(len(stripped) // 4, 80):]
    if "?" in tail:
        return True
    # Conversational confirmations that aren't punctuated as questions
    tail_lower = tail.lower()
    confirm_tails = (
        " right?", " correct?", " yes?", " instead?",
        "let me know", "tell me", "share with me",
        "which would you", "what should", "what's the",
    )
    return any(c in tail_lower for c in confirm_tails)


# Phrases that CLAIM a resource was created/wired. If the model says one
# of these but emitted no tool call, the claim is a lie — the resource
# doesn't exist. These override the is-a-clarifying-question gate, because
# the model loves to false-complete AND tack on a follow-up question
# ("Project is ready — want me to add agents?") which would otherwise
# look like a legit clarifying turn.
_FALSE_COMPLETION_CLAIMS = (
    "is ready", "are ready", "is created", "are created", "is live",
    "are live", "is set up", "are set up", "is wired", "are wired",
    "is minted", "is deployed", "are deployed", "is up and", "all set",
    "ready to go", "good to go", "all wired", "created and", "minted and",
    "wired up", "is done", "are done", "queued up", "is queued",
    "set up and", "spun up", "now live", "has been created",
    "have been created", "i've created", "i've set up", "i've spun up",
    "i've minted", "i've wired", "i've built",
)


def _claims_false_completion(text: str) -> bool:
    """True if the reply claims a build completed. In the no-tool-calls
    branch this claim is always false — retry to actually do the work."""
    if not text:
        return False
    t = text.lower()
    return any(c in t for c in _FALSE_COMPLETION_CLAIMS)


def _sanitize_tool_call_leaks(text: str) -> str:
    """Strip ALL known tool-call leak shapes from text.

    Used in two places:
      1. The live visible-text strip in run_origami_turn — so users don't
         see leaked tool-call markup in chat bubbles.
      2. Right before `mw.store()` — so Memwright never stores polluted
         content that would feed back to the model on next-turn recall
         and reinforce the leak (Studio contamination bug 2026-06-12).

    Patterns covered:
      - XML wrappers: <tool_call>, <function_calls>, <invoke>, <function>
      - Bare JSON: {"name": "create_X", "parameters": {...}}
                   {"tool": "create_X", "params": {...}}
                   [{"name": "..."}, ...]
      - Code-fenced JSON: ```json {"name": "create_X", ...} ```
      - Function-call syntax: invoke_agent("studio-x"),
        create_project(name="X")

    All whitelisted against the real platform tool names so we don't
    strip arbitrary JSON or function-call-looking text the user might
    legitimately discuss.
    """
    if not text:
        return text
    text = _TS_CODE_BLOCK_LEAK_RE.sub("", text)
    text = _CODE_FENCED_TOOL_CALL_RE.sub("", text)
    text = _TOOL_CALL_JSON_RE.sub("", text)
    text = _INVOKE_BLOCK_RE.sub("", text)
    text = _PARAMETERIZED_FUNCTION_RE.sub("", text)
    text = _BARE_JSON_TOOL_CALL_RE.sub("", text)
    text = _TS_IMPORT_LEAK_RE.sub("", text)
    text = _TOOL_FUNCTION_CALL_RE.sub("", text)
    return text.strip()

# Claude's chain-of-thought block. The model uses these to reason out loud
# but they're internal — the user should never see them. Stripped before
# AND after tool-call parsing because the model sometimes hides tool-call
# markup inside thinking blocks too (which would confuse the parser).
_THINKING_RE = re.compile(
    r"<thinking>.*?</thinking>", re.DOTALL | re.IGNORECASE,
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


def _heuristic_fill_project_id(
    tool_name: str,
    params: dict[str, Any],
    step_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Fill create_agent.project_id from a create_project step in the plan.

    The common chained-build failure: create_agent has
    project_id="${step_1.project_id}" but the ref didn't resolve (model
    miscounted, or the field stayed a literal template / display name).
    If project_id isn't a valid UUID, scan step_results for the most
    recent create_project result and use its project_id. create_agent's
    own tool also handles name-resolution + fallback, but filling the
    real UUID here is cleaner and keeps the audit log accurate.
    """
    if tool_name != "create_agent":
        return params
    pid = params.get("project_id")

    def _is_uuid(v: Any) -> bool:
        if not isinstance(v, str):
            return False
        try:
            uuid.UUID(v.strip())
            return True
        except ValueError:
            return False

    if _is_uuid(pid):
        return params  # already a real UUID — leave it
    # Unresolved template, name, or missing — find the project we just made.
    for sr in reversed(step_results):
        if isinstance(sr, dict) and sr.get("project_id"):
            out = dict(params)
            out["project_id"] = sr["project_id"]
            return out
    return params


def _repair_failed_step(
    action: str,
    params: dict[str, Any],
    result: dict[str, Any],
    plan_changes: list[Any],
    step_idx: int,
    step_results: list[dict[str, Any]],
) -> Optional[tuple[dict[str, Any], str]]:
    """Attempt to repair a failed tool call so it can be auto-retried.

    Returns (repaired_params, repair_note) if a fix is possible, None if not.
    The repair_note is a short human-readable string streamed to the UI
    so the user can see "auto-corrected: inferred source from create_agent
    step 4".

    Repair patterns supported:
    - connect_agents missing source_agent_name: infer from the first
      create_agent step in the plan (typically the hub).
    - update_agent agent_id not a UUID and no agent_name: try agent_id
      as agent_name.
    - Any tool where agent_id is a bare display name string: convert to
      agent_name.
    """
    if not isinstance(result, dict):
        return None
    error_code = result.get("error", "")
    error_msg = result.get("message", "")

    # ── connect_agents — missing source_agent_name ────────────────────
    if action == "connect_agents" and "source" in error_code:
        # Find the first create_agent invocation in the plan (likely the hub)
        hub_name = None
        for c in plan_changes:
            if c.action == "create_agent":
                hub_name = c.params.get("name")
                if hub_name:
                    break
        if hub_name:
            repaired = dict(params)
            repaired["source_agent_name"] = hub_name
            return repaired, f"inferred source_agent_name='{hub_name}' from plan's first create_agent"

    # ── update_agent / link_kb_to_agent — agent_id is a bare name ────
    if action in {"update_agent", "link_kb_to_agent"} and error_code in {"invalid_agent_id", "agent_not_found"}:
        agent_id_raw = params.get("agent_id")
        if isinstance(agent_id_raw, str) and not _looks_uuid(agent_id_raw) and not params.get("agent_name"):
            repaired = dict(params)
            repaired.pop("agent_id", None)
            repaired["agent_name"] = agent_id_raw
            return repaired, f"reinterpreted '{agent_id_raw}' as agent_name (not a UUID)"

    # ── upload_to_kb — kb_id is a bare name ──────────────────────────
    if action == "upload_to_kb" and error_code in {"invalid_kb_id", "kb_not_found"}:
        kb_id_raw = params.get("kb_id")
        if isinstance(kb_id_raw, str) and not _looks_uuid(kb_id_raw) and not params.get("kb_name"):
            repaired = dict(params)
            repaired.pop("kb_id", None)
            repaired["kb_name"] = kb_id_raw
            return repaired, f"reinterpreted '{kb_id_raw}' as kb_name"

    return None


def _looks_uuid(s: Any) -> bool:
    if not isinstance(s, str):
        return False
    try:
        uuid.UUID(s)
        return True
    except (ValueError, AttributeError):
        return False


_TEMPLATE_REF_RE = __import__("re").compile(r"\$\{([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)+)\}")


def _try_parse_function_call_syntax(text: str) -> Optional[tuple[str, dict[str, Any]]]:
    """Parse `name(arg=value, arg=value)` style calls inside tool-call tags.

    Bedrock's Anthropic models sometimes pick this instead of JSON, so we
    parse it as a fallback. Uses Python's ast module to safely evaluate
    just the kwargs (no execution).

    Preprocessing: Origami's own template syntax ``${step_N.field}`` is
    not valid Python and previously made ast.parse() throw SyntaxError —
    silently no-op'ing the entire fallback. We rewrite those references
    to quoted strings so the parse succeeds, and ``_resolve_template_params``
    downstream resolves them at execute time exactly the same way as if
    the model had emitted real tool_use blocks. Without this, when the
    model degrades to text-mode tool calls (which it does for complex
    plans even with raised max_tokens), the fallback fails and the user
    gets prose with no plan card.
    """
    import ast

    text = text.strip()
    if "(" not in text or not text.endswith(")"):
        return None
    open_paren = text.find("(")
    name = text[:open_paren].strip()
    if not name or not name.replace("_", "").isalnum():
        return None
    # Rewrite ${step_N.field} -> "${step_N.field}" so the expression
    # becomes a valid Python call literal. The string survives ast.parse
    # and the downstream template resolver re-detects the ${...} pattern
    # before execution.
    safe_text = _TEMPLATE_REF_RE.sub(r'"${\1}"', text)
    try:
        tree = ast.parse(safe_text, mode="eval")
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

    # Last-resort #1: bare function-call syntax on their own lines, no
    # angle-bracket wrappers at all. Bedrock-routed Claude does this
    # occasionally — emits `create_project(name="x", ...)\ncreate_agent(...)`
    # as plain text instead of tool_use blocks. See KNOWN-ISSUES #38.
    if not calls:
        for line in text.splitlines():
            line = line.strip()
            if not line or "(" not in line or not line.endswith(")"):
                continue
            open_paren = line.find("(")
            candidate_name = line[:open_paren].strip()
            if not candidate_name or candidate_name not in TOOL_REGISTRY:
                continue
            fc = _try_parse_function_call_syntax(line)
            if fc is None:
                continue
            name, params = fc
            calls.append({
                "id": f"inline-{len(calls)}",
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(params)},
            })

    # Last-resort #2: bare JSON-shaped tool calls, also no angle-bracket
    # wrappers. Observed in prod: model emits
    #   {"tool": "create_project", "params": {"name": "x"}}
    # inside a ```json``` codeblock or plain text. Scan every balanced JSON
    # object in the text; if it has a known tool name + extractable params,
    # treat as a tool call. Same TOOL_REGISTRY gate keeps it tight.
    if not calls:
        _NAME_KEYS_BARE = ("tool", "name", "function_name", "function", "tool_name")
        _ARGS_KEYS_BARE = ("params", "parameters", "arguments", "input", "args")
        for blob in _iter_balanced_json_objects(text):
            try:
                obj = json.loads(blob)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            name: Optional[str] = None
            for k in _NAME_KEYS_BARE:
                v = obj.get(k)
                if isinstance(v, str) and v in TOOL_REGISTRY:
                    name = v
                    break
            if not name:
                continue
            params: dict[str, Any] = {}
            for k in _ARGS_KEYS_BARE:
                v = obj.get(k)
                if isinstance(v, dict):
                    params = v
                    break
                if isinstance(v, str):
                    try:
                        parsed = json.loads(v)
                        if isinstance(parsed, dict):
                            params = parsed
                            break
                    except json.JSONDecodeError:
                        continue
            calls.append({
                "id": f"inline-{len(calls)}",
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(params)},
            })

    return calls


def _iter_balanced_json_objects(text: str):
    """Yield every balanced { ... } substring in text in order.

    Same scanner pattern as _extract_first_json_object, but keeps walking
    after each match instead of returning the first.
    """
    i = 0
    n = len(text)
    while i < n:
        if text[i] != "{":
            i += 1
            continue
        depth = 0
        in_str = False
        escape = False
        start = i
        while i < n:
            ch = text[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        yield text[start:i + 1]
                        i += 1
                        break
            i += 1


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
        elif tool == "show_integration_guide":
            agent_name = r.get("agent_name", "your agent")
            endpoint = r.get("endpoint", "")
            snippets = r.get("snippets") or {}
            langs = ", ".join(snippets.keys()) if snippets else "curl/python/typescript"
            rate = r.get("rate_limit_rpm")
            parts.append(
                f"To call `{agent_name}` from your app, POST to {endpoint} "
                f"with a `bp-` PAT in the Authorization header. Snippets "
                f"ready in {langs}. Rate limit: {rate} RPM. Mint a PAT under "
                f"Settings → Personal Access Tokens, then paste the snippet."
            )
        elif tool == "show_enterprise_options":
            avail = r.get("available_today") or []
            partial_list = r.get("partial_or_gated") or []
            road = r.get("roadmap") or []
            current = r.get("current_tier", "")
            parts.append(
                f"On {current} today, Enterprise unlocks {len(avail)} shipped "
                f"capabilities (SSO, RBAC, audit export, 99.9% SLA, agent HPA, "
                f"overflow queue, governance, RAG). {len(partial_list)} feature"
                f"{'s' if len(partial_list) != 1 else ''} partial/gated, "
                f"{len(road)} on the roadmap (VPC Gateway Agent, SOC-2 Type II, "
                f"smart routing). Procurement / security review: hello@trybonito.com."
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
    """Compact summary of a tool result for SSE events.

    Most tool results don't need to be transmitted in full over the SSE
    channel — the frontend only needs a quick visual confirmation that
    "create_agent succeeded". For those, we return only the key names.

    But a handful of tools produce values that are INTENDED to be shown
    to the user once (gateway-key raw value, next-step instructions
    with concrete URLs, prefix identifiers). Those fields are passed
    through verbatim so the user can copy them. They're listed in
    ``_USER_VISIBLE_FIELDS``.

    Background: a prior bug had mint_gateway_key succeeding server-side
    while the raw ``bn-`` key never appeared in the chat because the
    summarizer only echoed the result's key NAMES. The key was minted,
    the row was in the DB, but the user couldn't use it — they'd have
    to revoke and re-mint.
    """
    if not isinstance(result, dict):
        return {}

    if "counts" in result:
        return {"counts": result["counts"], "tier": result.get("tier")}
    if "gateway_requests" in result:
        return {
            "tier": result.get("tier"),
            "percent_used": result["gateway_requests"].get("percent_used"),
        }

    summary: dict[str, Any] = {"keys": list(result.keys())[:10]}
    for field in _USER_VISIBLE_FIELDS:
        if field in result and result[field] is not None:
            summary[field] = result[field]
    return summary


# Fields that, when present in a tool result, are intended to be shown
# to the user verbatim in the chat surface. The summarizer copies them
# through so the frontend can render them with appropriate UI affordances
# (copy buttons, "shown once" warnings, etc.). Anything not in this list
# is dropped from the SSE summary as a default-deny security posture.
_USER_VISIBLE_FIELDS = (
    # mint_gateway_key — the raw bn- value is shown ONCE at creation
    "raw_key",
    "raw_key_warning",
    "key_prefix",
    # create_project, create_kb, create_agent — names + ids the user
    # may want to reference in follow-up turns
    "project_id",
    "project_name",
    "kb_id",
    "kb_name",
    "agent_id",
    "agent_name",
    "name",
    # connection_id from connect_agents (so users can reference for unlinks)
    "connection_id",
    "source_agent_name",
    "target_agent_name",
    "connection_type",
    # Generic next-step instructions emitted by most write tools — these
    # are short prose with URLs / curl commands meant for the user
    "next_step",
    # Tier-related context surfaced by show_enterprise_options etc.
    "tier",
    # Idempotency hint — tells the user "this already existed, here's the id"
    "already_exists",
)
