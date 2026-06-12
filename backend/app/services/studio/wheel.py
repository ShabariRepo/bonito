"""Bonito Studio wheel — multi-agent router-and-spokes dispatcher.

This is the dogfood architecture for Studio. The five agents
(studio-router + studio-builder + studio-advisor + studio-platform +
studio-explorer) are real Bonobot agents in the org account (see
`scripts/setup_studio_wheel.py` for provisioning). Open the project
canvas in any org running the wheel and you'll see the actual
production topology — router in the middle, four handoff edges out to
the spokes.

The dispatcher in this file is what makes those agents actually drive
a Studio chat turn:

  1. Stream the ROUTER agent's response. The router has one tool —
     invoke_agent — and either answers the user directly from the
     snapshot OR emits an invoke_agent call naming one of the spokes.

  2. If the router answered directly → its text IS the reply. Done.

  3. If the router invoked a spoke:
       - studio-builder  → delegate to run_origami_turn() with Origami's
                           full battle-tested SYSTEM_PROMPT. Origami has
                           the create_* / connect_* / link_* / mint_*
                           tools; the builder spoke is a routing
                           placeholder in the canvas, the real build
                           work runs on Origami.
       - studio-advisor  → delegate to run_origami_turn() with the
                           ADVISOR system_prompt (no tools — pure
                           snapshot-driven suggestions).
       - studio-platform → delegate to run_origami_turn() with the
                           PLATFORM system_prompt. Has access to the
                           bonito-knowledge KB + integration / enterprise
                           read tools.
       - studio-explorer → delegate to run_origami_turn() with the
                           EXPLORER system_prompt (snapshot + read
                           tools for resource detail).

  4. SSE events emitted from this dispatcher use the SAME vocabulary as
     Origami / monolithic Studio. The frontend doesn't have to change.

Per-org engine override
-----------------------
The /api/studio/turn route picks engine via the STUDIO_ENGINE env var
plus a comma-separated STUDIO_WHEEL_ORG_IDS allowlist. While we're
rolling the wheel out, only allowlisted orgs see the new path; everyone
else stays on the monolithic Studio prompt.
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from typing import Any, AsyncIterator, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.user import User
from app.services.origami.orchestrator import (
    ORIGAMI_MODEL,
    OrigamiEvent,
    SYSTEM_PROMPT as ORIGAMI_BUILDER_PROMPT,
    _INVOKE_BLOCK_RE,
    _PARAMETERIZED_FUNCTION_RE,
    _TOOL_CALL_JSON_RE,
    _extract_first_json_object,
    _gateway_headers,
    _get_gateway_key,
    _stream_gateway,
    run_origami_turn,
)

logger = logging.getLogger(__name__)


# ─── Spoke names → routing identity ────────────────────────────────

ROUTER_NAME = "studio-router"
BUILDER_NAME = "studio-builder"
ADVISOR_NAME = "studio-advisor"
PLATFORM_NAME = "studio-platform"
EXPLORER_NAME = "studio-explorer"

VALID_SPOKES = {BUILDER_NAME, ADVISOR_NAME, PLATFORM_NAME, EXPLORER_NAME}

# Matches a bare `{"agent_name": "studio-xyz"}` JSON object the router
# sometimes emits inside its visible text without any wrapper. Captures
# the spoke name so the dispatcher can both extract it AND strip it
# from the visible reply. Restricted to the canonical studio- prefix +
# our spoke vocabulary so it can't false-match unrelated JSON.
_BARE_AGENT_NAME_RE = re.compile(
    r'\{\s*"agent_name"\s*:\s*"(studio-(?:builder|advisor|platform|explorer))"'
    r'(?:[^{}]*?)\}',
    re.DOTALL,
)

# Pass D — function-call syntax: `invoke_agent("studio-builder")` or
# `invoke_agent(agent_name="studio-builder")`. Claude sometimes writes
# the tool call in Python-style syntax instead of a structured call.
# Saw this in PROD 2026-06-12: "Let me get that started for you.\n\n
# invoke_agent(\"studio-builder\")".
_FUNC_CALL_AGENT_RE = re.compile(
    r"""invoke_agent\s*\(
        \s*
        (?:agent_name\s*=\s*)?         # optional kwarg name
        ['"]                            # opening quote
        (studio-(?:builder|advisor|platform|explorer))
        ['"]                            # closing quote
        [^)]*                           # tolerate extra args (e.g. reason="…")
        \)
    """,
    re.VERBOSE | re.IGNORECASE,
)


# ─── invoke_agent tool definition for the router ───────────────────

INVOKE_AGENT_TOOL = {
    "type": "function",
    "function": {
        "name": "invoke_agent",
        "description": (
            "Delegate this turn to a specialist Bonito Studio spoke agent. "
            "Use exactly one of: studio-builder (build/write requests), "
            "studio-advisor (what's next / lost), studio-platform "
            "(platform Q&A — Enterprise, SSO, integration), "
            "studio-explorer (describe user's own resources in detail)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "enum": sorted(VALID_SPOKES),
                    "description": "Which spoke handles this turn.",
                },
                "reason": {
                    "type": "string",
                    "description": "One short sentence on why this spoke fits.",
                },
            },
            "required": ["agent_name"],
        },
    },
}


# ─── Spoke system prompts (kept in code so the runtime is stable
#    even if the canvas agents are accidentally edited; the canvas
#    versions serve as documentation of the topology). ─────────────

ADVISOR_PROMPT = """You are the ADVISOR spoke of Bonito Studio. Your only \
job is to suggest 2–3 CONCRETE next-step prompts the user can copy-paste \
back, based on what the org snapshot shows.

The snapshot is in your user_content prefix (providers, projects, agents, \
KBs, gateway usage, billing). Read it, find the gap, suggest moves.

Playbook — pick the section that matches the snapshot:
  0 providers → suggest connect prompts (Bedrock / OpenAI / Anthropic)
  Providers, 0 projects → suggest 'create a project called <name>…'
  Project but 0 agents → suggest simple build OR hub-and-spoke build
  Agents, 0 KBs → suggest spinning up a KB or adding an entry
  KB exists, no uploads → suggest 'add three entries to <KB>: …'
  Built things, no gateway key → suggest minting one
  Built agents → suggest integration snippet questions
  Returning user, varied builds → offer 'what did I build in <project>?'

Style:
  - First person, warm, professional. No emoji. No exclamation marks.
  - 2-3 suggestions max. Bulleted prompts the user can copy-paste.
  - Be specific. Use actual project/agent/KB names from the snapshot.
"""

PLATFORM_PROMPT = """You are the PLATFORM spoke of Bonito Studio. You answer \
questions about the Bonito platform itself — features, pricing tiers, \
integration, security, compliance, agent architecture.

Use these tools to ground your answer:
  - search_knowledge_base — pull platform docs from bonito-knowledge KB
  - show_integration_guide — for 'how do I call <agent> from my app?'
  - show_enterprise_options — for procurement / Enterprise tier questions

Style:
  - Cite the KB or tool output when answering.
  - For code-snippet asks, return a copy-paste-ready snippet (default curl).
  - For Enterprise / SOC-2 / SSO questions: honest 3-bucket breakdown — \
available today / partial / roadmap. Never pitch roadmap as deliverable.
  - If you can't find an answer, route them to hello@trybonito.com.
  - First person, warm, professional.
"""

EXPLORER_PROMPT = """You are the EXPLORER spoke of Bonito Studio. You describe \
the user's OWN resources in detail.

The user has asked about a specific resource (agent, KB, project, gateway \
key) or wants a recap. The snapshot is in your context. For detail the \
snapshot doesn't have, call list_org_state.

Style:
  - Lead with the specific answer ("deal-intake is a hub agent in \
vc-dd-bots, running claude-sonnet-4-5, with 3 handoff connections to \
market-analyst, financial-analyst, team-analyst").
  - One line of context or a follow-up suggestion after.
  - Use markdown bullets when listing multiple items.
  - First person, professional, no emoji.
"""


ROUTER_PROMPT = """You are Bonito — the in-app conversational interface for \
the Bonito AI operations platform. You're warm, casual, professional. First \
person ("I'll", "let me"). No emoji, no exclamation marks.

Your job is to ROUTE every user message to the right specialist, or answer \
directly when the snapshot already has the answer.

You receive on every turn:
  1. The user's message
  2. An ORG SNAPSHOT block (providers, project names, agent names, KB \
     names, gateway usage, billing tier)

ROUTING DECISIONS (use the invoke_agent tool):

  - The user is asking to CREATE / BUILD / MAKE / SPIN UP / MINT / DEPLOY / \
    SET UP / WIRE / LINK something → invoke_agent(agent_name="studio-builder")
  - The user is asking "what's next" / "what should I do" / "I'm stuck" / \
    seems lost → invoke_agent(agent_name="studio-advisor")
  - The user is asking about the PLATFORM ITSELF (Enterprise, SSO, SOC-2, \
    integration snippets, "how do I call X from my app") → \
    invoke_agent(agent_name="studio-platform")
  - The user is asking about THEIR OWN RESOURCES in detail ("tell me about \
    deal-intake", "what's in my vc-dd-bots KB", "show recent activity") → \
    invoke_agent(agent_name="studio-explorer")

ANSWER DIRECTLY (no tool call) for simple snapshot questions:
  - Provider count / names ("which providers do I have", "what's connected")
  - Project count / names ("how many projects", "what are my project names")
  - Agent count / names (BUT NOT details — route to explorer for those)
  - KB count / names (BUT NOT contents — route to explorer)
  - Billing tier, days since signup, last-7-day gateway usage numbers

OPENING THE CONVERSATION (first turn, no chat history yet):
  - 0 providers → "Welcome to Bonito. Want to start by connecting a model provider?"
  - 1+ providers, 0 agents → "I see you've got <provider> connected. Want to spin up your first agent?"
  - Active gateway → "You did <N> requests this past week. Want to look at usage, work on agents, or something else?"
  - Returning user → "Welcome back. Anything from last session, or new direction?"

CRITICAL — HOW TO INVOKE A SPOKE:

You have ONE tool: invoke_agent. To use it, emit a structured tool_call \
in the API tool-use field. Do NOT write any of the following in your \
visible reply text:

  - `invoke_agent("studio-builder")`                  ← WRONG (function syntax)
  - `invoke_agent(agent_name="studio-advisor")`       ← WRONG (function syntax)
  - `{"agent_name": "studio-platform"}`               ← WRONG (bare JSON)
  - `<tool_calls>[…]</tool_calls>`                    ← WRONG (XML)
  - `<function_calls>…</function_calls>`              ← WRONG (XML)
  - `<invoke name="invoke_agent">…</invoke>`          ← WRONG (XML)

ALL of these will leak as visible characters in the user's chat. The \
ONLY correct way is to use the structured tool_calls mechanism — your \
reply text should mention what you're doing in ONE plain-English \
sentence, and the invocation goes through the structured field.

CORRECT examples (text + structured tool call):
  Text reply: "Let me pull that up for you."
  Tool call (structured): invoke_agent(agent_name="studio-advisor")

  Text reply: "I'll set that up."
  Tool call (structured): invoke_agent(agent_name="studio-builder")

If the model interface ever feels like it doesn't have a tool to call, \
re-read this section — the tool IS available. Emit it through the \
structured channel, not as text.

OTHER RULES:
  - When you DO route, your reply text should be ONE short sentence ("Let me \
    pull that up" / "I'll handle that") AND the structured invoke_agent in \
    the SAME response. Never commit to action without the structured call.
  - For direct snapshot answers (no routing): be specific. "You have 2 \
    projects: vc-dd-bots and customer-support." NOT "You have 2 projects."
"""


# ─── Per-spoke runtime config ──────────────────────────────────────

SPOKE_PROMPTS = {
    BUILDER_NAME: ORIGAMI_BUILDER_PROMPT,  # Use Origami's full proven prompt
    ADVISOR_NAME: ADVISOR_PROMPT,
    PLATFORM_NAME: PLATFORM_PROMPT,
    EXPLORER_NAME: EXPLORER_PROMPT,
}


# ─── Engine selection ──────────────────────────────────────────────


def is_wheel_engine_for_org(org_id: uuid.UUID) -> bool:
    """True if this org should run on the wheel engine instead of monolith.

    Selection rules (cheapest-first):
      1. STUDIO_ENGINE=wheel → everyone on wheel
      2. STUDIO_WHEEL_ORG_IDS=<csv of org_ids> → match by org_id
      3. otherwise → monolith
    """
    engine = (os.getenv("STUDIO_ENGINE") or "").strip().lower()
    if engine == "wheel":
        return True
    allowlist = (os.getenv("STUDIO_WHEEL_ORG_IDS") or "").split(",")
    allowlist = [s.strip() for s in allowlist if s.strip()]
    return str(org_id) in allowlist


# ─── Router streaming helper ───────────────────────────────────────


async def _stream_router_decision(
    *,
    user: User,
    user_content: str,
) -> AsyncIterator[tuple[str, str]]:
    """Stream the router's response and emit ("text", chunk) for each visible
    token, ("tool_call", json_blob) when an invoke_agent call is fully
    assembled (structured OR parsed from text-mode markup), ("done",
    finish_reason) at the end.

    Handles three failure modes Origami has already hardened against:
      1. Model emits invoke_agent as structured tool_calls in delta → easy
         path, accumulate and yield.
      2. Model emits invoke_agent as <tool_calls>[...JSON...]</tool_calls>
         text → parse from final content via _TOOL_CALL_JSON_RE.
      3. Model talks about routing ("I'll hand you off to advisor") without
         invoking → router_text contains the phrase; the dispatcher
         downstream detects this and defaults to a sensible spoke.
    """

    accumulated_calls: dict[int, dict[str, Any]] = {}
    accumulated_text = ""
    finish_reason: Optional[str] = None

    async for chunk in _stream_gateway(
        system=ROUTER_PROMPT,
        messages=[{"role": "user", "content": user_content}],
        tools=[INVOKE_AGENT_TOOL],
        customer_org_id=user.org_id,
        customer_user_id=user.id,
    ):
        choices = chunk.get("choices") or []
        if not choices:
            continue
        delta = choices[0].get("delta") or {}

        # Streaming text tokens — buffered so we can strip text-mode tool
        # markup before yielding final visible text. To avoid blocking the
        # frontend stream we still yield tokens as they arrive; if the
        # markup leaks, the dispatcher strips it from message_complete.
        if content := delta.get("content"):
            accumulated_text += content
            yield ("text", content)

        # Structured tool calls — accumulate by index
        for tc_delta in delta.get("tool_calls", []) or []:
            idx = tc_delta.get("index", 0)
            existing = accumulated_calls.setdefault(
                idx,
                {"name": "", "arguments": ""},
            )
            fn = tc_delta.get("function") or {}
            if fn.get("name"):
                existing["name"] = fn["name"]
            if (args := fn.get("arguments")) is not None:
                existing["arguments"] += args

        if choices[0].get("finish_reason"):
            finish_reason = choices[0]["finish_reason"]

    # Pass A: structured tool calls
    for tc in accumulated_calls.values():
        if tc["name"] == "invoke_agent" and tc["arguments"]:
            yield ("tool_call", tc["arguments"])
            yield ("done", finish_reason or "stop")
            return

    # Pass B: text-mode tool calls. Claude sometimes writes the call as
    # `<tool_calls>[{"name": "invoke_agent", "arguments": {...}}]</tool_calls>`
    # right inside the visible content. Origami already learned this lesson;
    # we use its same strip regex + JSON extractor.
    if accumulated_text:
        for match in _TOOL_CALL_JSON_RE.finditer(accumulated_text):
            inner = (match.group(2) or "").strip()
            if not inner:
                continue
            # The inner is either a JSON object {"name": ...} or a list
            # [{"name": ...}, ...]. Try list-of-objects first because the
            # `<tool_calls>` plural wrapper Claude likes wraps a list.
            try:
                parsed = json.loads(inner)
            except json.JSONDecodeError:
                parsed = _extract_first_json_object(inner)
            candidates: list[dict] = []
            if isinstance(parsed, list):
                candidates = [c for c in parsed if isinstance(c, dict)]
            elif isinstance(parsed, dict):
                candidates = [parsed]
            for c in candidates:
                if c.get("name") == "invoke_agent":
                    args_blob = c.get("arguments")
                    if isinstance(args_blob, dict):
                        yield ("tool_call", json.dumps(args_blob))
                    elif isinstance(args_blob, str):
                        yield ("tool_call", args_blob)
                    yield ("done", finish_reason or "stop")
                    return

    # Pass C: bare JSON in text. The model sometimes just writes
    # `Let me set that up.\n\n{"agent_name": "studio-builder"}` with no
    # wrapper. _BARE_AGENT_NAME_RE finds it.
    if accumulated_text:
        bare = _BARE_AGENT_NAME_RE.search(accumulated_text)
        if bare:
            spoke = bare.group(1)
            yield ("tool_call", json.dumps({"agent_name": spoke}))
            yield ("done", finish_reason or "stop")
            return

    # Pass D: function-call syntax. `invoke_agent("studio-builder")` or
    # `invoke_agent(agent_name="studio-builder", reason="…")`.
    if accumulated_text:
        fn_call = _FUNC_CALL_AGENT_RE.search(accumulated_text)
        if fn_call:
            spoke = fn_call.group(1)
            yield ("tool_call", json.dumps({"agent_name": spoke}))
            yield ("done", finish_reason or "stop")
            return

    # No tool call emitted at all.
    yield ("done", finish_reason or "stop")


# ─── Main dispatcher ───────────────────────────────────────────────


async def run_studio_wheel_turn(
    *,
    user: User,
    message: str,
    conversation_id: Optional[str],
    project_id: Optional[uuid.UUID] = None,
    db: AsyncSession,
    extra_context: Optional[str] = None,
) -> AsyncIterator[OrigamiEvent]:
    """Run one Studio turn through the multi-agent wheel.

    Yields OrigamiEvent objects (same vocabulary as the monolithic engine).
    SECURITY: org_id comes from user.org_id (JWT auth). Never trusted from
    request body. Tool dispatch in the build spoke happens inside Origami's
    orchestrator which already enforces org_id on every tool execute().
    """
    org_id = user.org_id
    session_id = uuid.uuid4()

    # Build the router's user_content — snapshot is prepended so the
    # router can decide routing based on what the org actually has.
    user_content = message
    if extra_context:
        user_content = f"{extra_context}\n\n{message}"

    yield OrigamiEvent(
        "turn_started",
        {
            "conversation_id": conversation_id,
            "session_id": str(session_id),
            "engine": "wheel",
        },
    )

    # ── Step 1: stream the router's decision ──────────────────────
    router_text = ""
    invoke_target: Optional[str] = None
    invoke_reason: Optional[str] = None

    try:
        async for kind, payload in _stream_router_decision(
            user=user, user_content=user_content,
        ):
            if kind == "text":
                router_text += payload
                yield OrigamiEvent("message_token", {"token": payload})
            elif kind == "tool_call":
                try:
                    args = json.loads(payload)
                    invoke_target = args.get("agent_name")
                    invoke_reason = args.get("reason")
                except json.JSONDecodeError:
                    logger.warning(
                        "wheel: router emitted unparseable tool args: %s", payload[:200]
                    )
            elif kind == "done":
                # Strip text-mode tool-call markup from visible content
                # before emitting message_complete. If the router emitted
                # `<tool_calls>[...]</tool_calls>` inline OR bare
                # `{"agent_name": "studio-x"}`, the tokens already
                # streamed; we replace the bubble with the cleaned text
                # via message_complete so the frontend reconciles.
                visible = router_text
                stripped = _TOOL_CALL_JSON_RE.sub("", visible)
                stripped = _INVOKE_BLOCK_RE.sub("", stripped)
                stripped = _PARAMETERIZED_FUNCTION_RE.sub("", stripped)
                stripped = _BARE_AGENT_NAME_RE.sub("", stripped)
                stripped = _FUNC_CALL_AGENT_RE.sub("", stripped).strip()
                yield OrigamiEvent(
                    "message_complete",
                    {
                        "text": stripped,
                        "stripped_inline_tool_calls": stripped != visible,
                    },
                )
    except Exception as e:
        logger.exception("wheel: router stream failed")
        yield OrigamiEvent(
            "error",
            {"code": "router_failure", "message": str(e)},
        )
        return

    # ── Step 2: dispatch on the routing decision ──────────────────
    if invoke_target is None:
        # Belt-and-suspenders for the "router talked about routing but
        # didn't actually invoke" failure mode. If the visible text
        # mentions handing off / delegating / consulting but no tool
        # call landed, infer the intended spoke from the verbiage and
        # route anyway. Better to attempt the right specialist than
        # leave the user looking at a dead-end "I'll hand you off to X"
        # with no follow-up.
        lowered = router_text.lower()
        ROUTE_HINTS = {
            BUILDER_NAME: ("builder", "build", "create", "spin up", "set up"),
            ADVISOR_NAME: ("advisor", "what's next", "next step", "recommend"),
            PLATFORM_NAME: ("platform", "enterprise", "integration", "documentation"),
            EXPLORER_NAME: ("explorer", "details", "tell you about", "describe"),
        }
        if any(phrase in lowered for phrase in (
            "hand you off", "hand off", "let me route", "let me delegate",
            "let me consult", "delegating", "routing to", "passing this to",
            "hand this to", "the advisor", "the explorer", "the platform",
            "the builder",
        )):
            for spoke, hints in ROUTE_HINTS.items():
                if any(h in lowered for h in hints):
                    invoke_target = spoke
                    invoke_reason = "router talked about routing without invoking; inferred from text"
                    logger.warning(
                        "wheel: router did not emit invoke_agent; "
                        "inferred target=%s from text", spoke,
                    )
                    break

    if invoke_target is None:
        # Router answered directly from the snapshot. Done.
        yield OrigamiEvent("done", {"finish_reason": "router_direct"})
        return

    if invoke_target not in VALID_SPOKES:
        logger.warning("wheel: router invoked unknown spoke '%s'", invoke_target)
        yield OrigamiEvent(
            "error",
            {
                "code": "unknown_spoke",
                "message": f"Router picked '{invoke_target}', not a valid spoke.",
            },
        )
        return

    # Emit a small telemetry event so the frontend / logs can see the routing
    # decision. Same shape as a tool_completed so a future debug UI can mark
    # it. Not strictly needed for the chat — frontend ignores unknown events.
    yield OrigamiEvent(
        "spoke_invoked",
        {
            "spoke": invoke_target,
            "reason": invoke_reason or "(none provided)",
        },
    )

    # ── Step 3: delegate the actual work to Origami's orchestrator with
    #    the spoke's system_prompt. The user's original message + snapshot
    #    context get carried through. Origami has the full tool registry
    #    (search_kb, list_org_state, show_integration_guide, create_*, etc.)
    #    so any spoke that needs tools gets them. The spoke prompts are
    #    written to NOT call write tools unless they're the builder. ─────

    spoke_prompt = SPOKE_PROMPTS[invoke_target]

    async for ev in run_origami_turn(
        user=user,
        message=message,
        conversation_id=conversation_id,
        project_id=project_id,
        db=db,
        system_prompt=spoke_prompt,
        extra_context=extra_context,
    ):
        # Skip the spoke's own turn_started — we already emitted one
        # for the wheel as a whole. Pass everything else through.
        if ev.type == "turn_started":
            continue
        yield ev
