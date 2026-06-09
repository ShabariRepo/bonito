"""Origami SDK spike — claude-agent-sdk prototype.

What this proves (or disproves) for the build-vs-buy decision:

  1. TOOL FRAMEWORK — register stub tools with @tool + create_sdk_mcp_server.
     The SDK runs them in-process as an in-memory MCP server. No HTTP, no
     external server, no spawn-per-call. This maps directly to what Origami
     needs (12 thin wrappers around internal API).

  2. PLAN-CARD STRUCTURED OUTPUT — we instruct the model to emit a JSON
     plan card BEFORE invoking any write tool, and we parse it out of the
     assistant text stream. The SDK has no first-class "plan card" type
     (it has a `plan` permission_mode for filesystem edits, which is
     different — see notes.md). We work around it with system-prompt
     contract + JSON-block parsing. This is the load-bearing UX of Origami.

  3. USER-CONFIRMATION INTERRUPT — we use `can_use_tool` (the SDK's
     interrupt-for-approval primitive). On every write-tool call the SDK
     hands us tool_name + tool_input + context and waits for a
     PermissionResultAllow / PermissionResultDeny before executing.
     This is the closest SDK primitive to "user clicks Deploy."

  4. STREAMING — async iteration over query() yields partial messages as
     the model emits them. Confirmed below by printing each block as it
     arrives. (Set `include_partial_messages=True` for token-level deltas;
     we keep block-level here for cleaner demo output.)

  5. GATEWAY ROUTING — the SDK shells out to the `claude` CLI under the
     hood, so we can only configure the upstream API via env vars passed
     through ClaudeAgentOptions.env. ANTHROPIC_BASE_URL is what Claude CLI
     reads. CRITICAL CAVEAT documented in notes.md: Bonito's gateway only
     speaks OpenAI format (POST /v1/chat/completions), but the CLI speaks
     Anthropic format (POST /v1/messages). So pointing the CLI at
     api.getbonito.com would 404. See notes.md §"Hard requirements."

How to run:

    pip install -r requirements.txt
    # Install the underlying CLI that the SDK shells out to:
    npm install -g @anthropic-ai/claude-code
    export ANTHROPIC_API_KEY=sk-ant-...  # real key, until Bonito ships
                                          # an Anthropic-format gateway
    python main.py
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
)

from stub_tools import ALL_TOOLS


# ─── gateway / auth config ──────────────────────────────────────────────────

# TODO: real key from Shabari before running. Bonito gateway keys are bn-prefix.
BONITO_GATEWAY_KEY = os.environ.get("BONITO_GATEWAY_KEY", "bn-SPIKE-PLACEHOLDER")

# The Bonito gateway base URL. NOTE: Bonito's /v1/chat/completions is OpenAI
# format — Claude CLI expects Anthropic /v1/messages format. Pointing the CLI
# at the gateway will currently 404. We still wire the env var to document
# the seam — see notes.md "Hard requirements" for the workaround.
BONITO_GATEWAY_BASE_URL = os.environ.get(
    "BONITO_GATEWAY_BASE_URL", "https://api.getbonito.com"
)

# Set to "1" to actually route through the gateway (will fail until we ship
# an Anthropic-shaped translation layer). Default off so the spike runs
# against direct Anthropic API for measurement purposes.
ROUTE_VIA_BONITO = os.environ.get("ROUTE_VIA_BONITO", "0") == "1"


# ─── plan card contract ────────────────────────────────────────────────────

# We can't make the SDK enforce a JSON schema on the assistant output, so we
# enforce a contract via system prompt + parse a fenced ```json block out of
# the text stream. This is the workaround for "no first-class structured
# output type" — documented in notes.md as a soft gap.

ORIGAMI_SYSTEM_PROMPT = """\
You are Origami, the in-app conversational builder for the Bonito platform.

You can call these tools to build infrastructure for the user:
  - mcp__origami__create_agent
  - mcp__origami__create_kb

CRITICAL RULES:

1. For ANY write action (create_agent, create_kb, etc.), you MUST first emit a
   plan card and STOP. Do NOT call the tool until the user has explicitly
   confirmed in the next turn.

2. Plan card format — emit EXACTLY this fenced block as the LAST thing in your
   message, with nothing after the closing fence:

```json
{
  "intent": "<one-line plain-language summary>",
  "changes": [
    {"action": "create_kb",    "params": {"name": "...", "dimensions": 1024}},
    {"action": "create_agent", "params": {"name": "...", "model_id": "claude-sonnet-4-6", "kb_ids": []}}
  ],
  "tier_impact": "<e.g. uses 1/2 agents on Builder>",
  "estimated_cost_per_month_usd": 3,
  "awaiting_confirmation": true
}
```

3. After emitting the plan card, stop. Wait for the user to say "deploy" or
   "yes" or "no". On confirm, call the tools in order. On deny, acknowledge
   briefly and stop.

4. Be brief. One short paragraph of context above the plan card, then the JSON.
   No preamble like "I'll help you with that!"
"""


# ─── confirmation state ────────────────────────────────────────────────────


@dataclass
class TurnState:
    """Shared state between the streaming loop and the can_use_tool callback.

    Origami's UX is: model emits plan card → frontend renders it → user clicks
    Deploy → frontend tells backend "yes, run it" → tools execute. In this
    spike, the user-confirmation signal is set externally (by test_run.py
    calling `state.confirm("yes")`) before the second turn. The can_use_tool
    callback below reads that signal to allow/deny tool invocations.
    """

    confirmed: bool = False
    deny_reason: str | None = None
    tools_seen: list[str] = field(default_factory=list)

    def confirm(self) -> None:
        self.confirmed = True
        self.deny_reason = None

    def deny(self, reason: str = "user said no") -> None:
        self.confirmed = False
        self.deny_reason = reason


# ─── interrupt-for-approval via can_use_tool ────────────────────────────────


def build_can_use_tool(state: TurnState):
    """Returns the SDK's can_use_tool async callback bound to our TurnState.

    Returning PermissionResultDeny here causes the SDK to skip the tool call
    and surface a tool_result with the deny message back to the model on the
    next turn. The model can then explain to the user what was blocked.
    """

    async def can_use_tool(tool_name: str, tool_input: dict[str, Any], context):
        state.tools_seen.append(tool_name)
        # Only gate our write tools (the mcp__origami__* prefix). Built-in
        # SDK tools (Read, Write, Bash, etc.) we'd typically block entirely
        # in Origami — they're not in the 12-tool surface.
        is_write_tool = tool_name.startswith("mcp__origami__")
        if not is_write_tool:
            return PermissionResultDeny(
                message=f"{tool_name} is not in the Origami tool surface.",
                interrupt=False,
            )

        if state.confirmed:
            print(f"  [approval] User confirmed → allowing {tool_name}")
            return PermissionResultAllow(updated_input=tool_input)

        reason = state.deny_reason or "Plan card not yet confirmed by user."
        print(f"  [approval] DENIED {tool_name}: {reason}")
        return PermissionResultDeny(message=reason, interrupt=True)

    return can_use_tool


# ─── plan card parsing ──────────────────────────────────────────────────────

_PLAN_CARD_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


def extract_plan_card(assistant_text: str) -> dict[str, Any] | None:
    """Pull the JSON plan card out of the assistant's streamed text.

    Returns None if no fenced ```json block was found OR it didn't parse.
    Origami's frontend would render the card from this dict; the spike just
    pretty-prints it.
    """
    match = _PLAN_CARD_RE.search(assistant_text)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


# ─── token measurement ─────────────────────────────────────────────────────


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    cost_usd: float = 0.0

    # Sonnet 4.6 published pricing (USD per 1M tokens). Update when 4.7
    # supersedes.  Source: ORIGAMI-MVP-PLAN.md §"Model routing".
    INPUT_PRICE_PER_M = 3.0
    OUTPUT_PRICE_PER_M = 15.0
    CACHE_READ_PRICE_PER_M = 0.30  # 10% of input
    CACHE_WRITE_PRICE_PER_M = 3.75  # 1.25x input

    def add_from_result(self, result_msg: ResultMessage) -> None:
        u = getattr(result_msg, "usage", None) or {}
        self.input_tokens += u.get("input_tokens", 0) or 0
        self.output_tokens += u.get("output_tokens", 0) or 0
        self.cache_read_tokens += u.get("cache_read_input_tokens", 0) or 0
        self.cache_creation_tokens += u.get("cache_creation_input_tokens", 0) or 0
        # SDK already gives total_cost_usd on the ResultMessage if available.
        cost = getattr(result_msg, "total_cost_usd", None)
        if cost is not None:
            self.cost_usd += cost
        else:
            self.cost_usd += self.compute_cost()

    def compute_cost(self) -> float:
        return (
            self.input_tokens * self.INPUT_PRICE_PER_M / 1_000_000
            + self.output_tokens * self.OUTPUT_PRICE_PER_M / 1_000_000
            + self.cache_read_tokens * self.CACHE_READ_PRICE_PER_M / 1_000_000
            + self.cache_creation_tokens * self.CACHE_WRITE_PRICE_PER_M / 1_000_000
        )


# ─── the actual turn runner ────────────────────────────────────────────────


async def run_origami_turn(
    user_message: str,
    state: TurnState,
    client: ClaudeSDKClient,
) -> tuple[str, dict[str, Any] | None, TokenUsage]:
    """Send one user message through Origami, stream the response, return
    (assistant_text, plan_card_or_none, token_usage).
    """
    usage = TokenUsage()
    full_text_parts: list[str] = []

    await client.query(user_message)

    print(f"\n>>> Origami says (streaming):\n", end="", flush=True)
    async for msg in client.receive_response():
        if isinstance(msg, AssistantMessage):
            # Each AssistantMessage may contain multiple content blocks.
            # We get one per "chunk" — text appears block by block as the
            # model streams. (For token-level deltas, set
            # include_partial_messages=True on ClaudeAgentOptions and listen
            # for StreamEvent — overkill for this spike.)
            for block in msg.content:
                if isinstance(block, TextBlock):
                    sys.stdout.write(block.text)
                    sys.stdout.flush()
                    full_text_parts.append(block.text)
                elif isinstance(block, ToolUseBlock):
                    print(
                        f"\n  [tool_use] {block.name}("
                        f"{json.dumps(block.input, default=str)[:120]}...)"
                    )
        elif isinstance(msg, SystemMessage):
            # init / hook events / mcp_status etc. Skipped for brevity.
            pass
        elif isinstance(msg, ResultMessage):
            usage.add_from_result(msg)
            break

    print()  # newline after streaming
    full_text = "".join(full_text_parts)
    plan_card = extract_plan_card(full_text)
    return full_text, plan_card, usage


# ─── client setup ──────────────────────────────────────────────────────────


def build_options(state: TurnState) -> ClaudeAgentOptions:
    # Wire our stub tools into an in-process MCP server. The SDK prefixes
    # tool names with mcp__<server_name>__<tool_name> when exposing them to
    # the model — so create_agent becomes mcp__origami__create_agent.
    origami_server = create_sdk_mcp_server(
        name="origami",
        version="0.1.0",
        tools=ALL_TOOLS,
    )

    # Pass through env to the underlying `claude` CLI subprocess. This is the
    # only seam for redirecting upstream traffic. ANTHROPIC_BASE_URL is what
    # Claude CLI honors. See notes.md for why this doesn't fully work for
    # Bonito's OpenAI-shaped gateway today.
    subprocess_env: dict[str, str] = {}
    if ROUTE_VIA_BONITO:
        subprocess_env["ANTHROPIC_BASE_URL"] = BONITO_GATEWAY_BASE_URL
        subprocess_env["ANTHROPIC_API_KEY"] = BONITO_GATEWAY_KEY
    # else: inherit ANTHROPIC_API_KEY from process env (real Anthropic call).

    return ClaudeAgentOptions(
        system_prompt=ORIGAMI_SYSTEM_PROMPT,
        mcp_servers={"origami": origami_server},
        # IMPORTANT: We intentionally do NOT list the origami tools in
        # `allowed_tools`. The SDK docs (and our spike confirmed) that
        # can_use_tool is ONLY invoked when CLI permission rules evaluate to
        # "ask" — if a tool is in allowed_tools, it executes silently and our
        # gating callback never fires. Leaving allowed_tools empty for the
        # mcp__origami__* tools forces the CLI to ask → can_use_tool runs →
        # our TurnState.confirmed gate decides allow/deny.
        #
        # If you ever want zero-friction auto-allow during dev, comment this
        # back in:
        # allowed_tools=["mcp__origami__create_agent", "mcp__origami__create_kb"],
        # Lock down everything else — Origami should NOT have file/bash access.
        # The CLI tries to mount Read/Write/Bash by default; we deny via
        # can_use_tool above as a belt-and-braces on top.
        disallowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
        can_use_tool=build_can_use_tool(state),
        permission_mode="default",  # NOT "plan" — that's a filesystem-edit
        # specific mode in the CLI, unrelated to our plan-card UX.
        model="claude-sonnet-4-5",  # TODO: pin to sonnet-4-6 once SDK exposes
        # it; pricing math in TokenUsage already assumes 4.6 rates.
        max_turns=4,
        env=subprocess_env,
        # Help the CLI find any necessary working dir; not load-bearing here.
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )


async def main() -> None:
    """Smoke run — same scenario test_run.py uses. Lets you `python main.py`
    end-to-end without the measurement scaffolding."""
    state = TurnState()
    options = build_options(state)

    async with ClaudeSDKClient(options=options) as client:
        # Turn 1: user asks for a build → we expect a plan card, no tool exec.
        user_msg = (
            "Build me a support agent for our Shopify store, with a KB "
            "called 'shopify-help' from our help docs. Use Sonnet."
        )
        print(f"\n=== TURN 1 ===\nUser: {user_msg}")
        text1, plan1, usage1 = await run_origami_turn(user_msg, state, client)

        print("\n--- Parsed plan card ---")
        print(json.dumps(plan1, indent=2) if plan1 else "(no plan card parsed)")
        print(f"--- Usage turn 1: in={usage1.input_tokens} out={usage1.output_tokens} "
              f"cost=${usage1.compute_cost():.5f} ---")

        if not plan1:
            print("\n!!! Origami didn't emit a plan card — aborting demo.")
            return

        # Turn 2: simulate user clicking Deploy → tools should run.
        state.confirm()
        confirm_msg = "Yes, deploy."
        print(f"\n=== TURN 2 ===\nUser: {confirm_msg}")
        text2, plan2, usage2 = await run_origami_turn(confirm_msg, state, client)
        print(f"--- Usage turn 2: in={usage2.input_tokens} out={usage2.output_tokens} "
              f"cost=${usage2.compute_cost():.5f} ---")
        print(f"--- Tools the SDK routed through can_use_tool: {state.tools_seen} ---")


if __name__ == "__main__":
    asyncio.run(main())
