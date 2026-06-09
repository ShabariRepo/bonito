# Origami SDK Spike — Notes & Recommendation

**Date:** 2026-06-06
**SDK probed:** `claude-agent-sdk==0.2.93` (PyPI, Anthropic, released 2025-09; was previously named `claude-code-sdk` v0.0.x)
**Underlying:** `@anthropic-ai/claude-code` CLI v2.1.167 (the SDK shells out to it)
**Run against:** live Claude Sonnet 4.5 (Sonnet 4.6 not yet exposed on this SDK version)

---

## 1. Build-vs-buy recommendation: **SKIP THE SDK**

Confidence: high (8/10).

Five reasons, in priority order:

1. **The dogfood story is broken.** The SDK shells out to the `claude` CLI binary,
   which speaks Anthropic-format `/v1/messages`. Bonito's gateway only exposes
   OpenAI-format `/v1/chat/completions`. Pointing the SDK at
   `api.getbonito.com` 404s. The whole Origami pitch ("Origami is our first
   gateway-routed dogfooded agent") collapses unless we either (a) ship a new
   `/v1/messages` translation endpoint on the gateway (1–2 days, doable but
   non-trivial), or (b) write a custom `Transport` subclass that bypasses the
   CLI — at which point we've rebuilt 80% of the SDK.

2. **Anthropic lock-in eliminates Bonito's core value prop.** Bonito's pitch
   is "your control plane across 6 providers with failover." The SDK can only
   call Anthropic models (the CLI's only upstream is `api.anthropic.com` or
   an Anthropic-compatible relay). If Anthropic rate-limits or has an outage,
   Origami goes down — the failover system Bonito ships to its customers
   doesn't apply to its own flagship demo. That's a board-meeting bad headline.

3. **18.9× measured cost overhead** (see §4 below). At Pro tier's 10K
   turns/month quota, the SDK's ~$0.10/turn vs ~$0.005/turn raw becomes
   ~$1000/mo COGS vs ~$50/mo. The plan's $999 Pro price has zero margin if
   Origami is SDK-backed.

4. **The SDK is a thick CLI wrapper, not a library.** It requires installing
   `npm install -g @anthropic-ai/claude-code` on the server, spawns a node
   subprocess per `ClaudeSDKClient`, and communicates via stdin/stdout JSON-RPC.
   Operationally this is heavier than a pip install: container image bloat
   (~200MB extra for Node), runtime cost (process spawn per session),
   debugging cost (errors come through CLI stderr layer).

5. **Engineering savings are smaller than expected.** Once you cross out the
   parts of the SDK Origami can't use (filesystem tools, bash, `permission_mode:
   plan` for code edits, session storage that doesn't match our multi-tenant
   audit model), what's actually saved is: the `@tool` decorator,
   `can_use_tool` callback shape, and Anthropic SSE plumbing. All three are
   1-day each to hand-roll. Total savings: ~1 week, not the 3-4 weeks the
   adversarial review estimated.

**Caveat:** the 8/10 confidence drops to 6/10 IF Bonito is willing to ship the
Anthropic-format gateway endpoint (a real possibility — it'd benefit other use
cases too). Even then, points #2, #3, #5 still hold.

---

## 2. What worked out of the box (specific SDK primitives → Origami needs)

| Origami need | SDK primitive | Verdict |
|---|---|---|
| Tool framework (12 thin wrappers) | `@tool` decorator + `create_sdk_mcp_server` | ✅ Clean. In-process MCP server, no subprocess per tool, typed schemas. |
| Streaming response | `async for msg in client.receive_response()` | ✅ Worked first try. Block-level by default; `include_partial_messages=True` for token-level. |
| Interrupt-for-approval | `can_use_tool` callback | ⚠️ Works but with a gotcha (see §3.1). |
| Built-in conversation state | `ClaudeSDKClient` context manager + `query()` queues messages | ✅ For single-process. ❌ for stateless HTTP (see §3.3). |
| Cost reporting per turn | `ResultMessage.total_cost_usd` + `usage` dict | ✅ Returned per turn. |
| Multi-tool gating | `disallowed_tools` list | ✅ Belt-and-braces denial of Bash/Read/Write/etc. |

The plan card itself **is not** a first-class primitive. The SDK has a
`permission_mode="plan"` option, but that's for filesystem-edit planning (Claude
Code's plan mode) — it returns a textual plan and refuses to apply edits.
Unrelated to our structured-JSON plan-card UX. We worked around it via
system-prompt contract + JSON-block extraction in `extract_plan_card()`. This
works but is brittle to model drift.

---

## 3. What didn't work / required workarounds

### 3.1 `can_use_tool` is silently bypassed by `allowed_tools`

**Surprise:** if you list your tools in `allowed_tools`, the SDK skips
`can_use_tool` entirely. The docstring says "Invoked when the CLI's permission
rules evaluate to 'ask' — not for tool calls already permitted by
`allowed_tools`." We initially listed our origami tools in `allowed_tools` for
clarity; tools fired silently with no approval gate, `state.tools_seen` was
empty.

**Fix in spike:** remove origami tools from `allowed_tools`; rely entirely on
`can_use_tool` for the gate. Comment in `main.py` flags this.

**Risk for prod:** anyone editing the options later who adds a tool to
`allowed_tools` for "convenience" silently breaks the whole confirmation UX
without warning. Would need a CI test or runtime assertion.

### 3.2 No structured-output type — plan card via system prompt contract

The SDK has no `response_format` / `output_schema` concept like OpenAI's
structured outputs. The plan card has to be coaxed out of the assistant text via
prompt engineering and regex'd out of the stream. Worked in 4/4 spike runs, but:

- Model drift could break the JSON fence pattern (we use ```` ```json ... ``` ````)
- No guarantee of schema conformance — Origami frontend would need defensive parsing
- The newer `output_format` option in `ClaudeAgentOptions` is for CLI-level
  output formatting (json/text/markdown), not response schema enforcement

### 3.3 `ClaudeSDKClient` is a stateful process — doesn't map to stateless HTTP

`ClaudeSDKClient` spawns a CLI subprocess on `__aenter__` and tears it down on
`__aexit__`. Production Origami is `POST /api/origami/turn` — each turn is a new
HTTP request to a stateless FastAPI worker. To preserve conversation across
turns, you'd need to either:

- Keep the subprocess alive across requests (sticky sessions, per-user) — hostile
  to Railway's 2-worker autoscaling model
- Spawn a fresh subprocess per turn and replay history via the `resume` /
  `continue_conversation` options — the CLI then re-loads the entire prior
  history each time, eating the 100K cache-read cost on every turn even with
  caching
- Implement a custom `Transport` that talks HTTP directly, no subprocess

None of these is a clean fit. A hand-rolled `httpx` client storing conversation
in our existing per-user Persistent Agent Memory table is materially simpler.

### 3.4 Gateway base URL: only Anthropic-format

The seam exists: `ClaudeAgentOptions.env` passes env vars through to the CLI
subprocess, and the CLI honors `ANTHROPIC_BASE_URL`. The spike wires this up
behind a `ROUTE_VIA_BONITO=1` flag. But the CLI POSTs to `/v1/messages` in
Anthropic format. Bonito's gateway is OpenAI `/v1/chat/completions` only. So:

- **As-is:** 404. No dogfood.
- **Fix option A:** ship a new `/v1/messages` endpoint on Bonito that
  translates → LiteLLM. Manageable (~2 days). Also useful for any future
  Anthropic-SDK customer.
- **Fix option B:** custom `Transport` subclass speaking HTTP to OpenAI-format
  directly. Rebuilds half the SDK.

### 3.5 Massive system-harness footprint (cache reads)

Each turn reads ~100K cached input tokens of CLI system harness (tool catalog,
hook events, internal prompts). Anthropic bills cache reads at 10% of input
($0.30/M for Sonnet), so this is "only" ~$0.03/turn — but it's $300/mo at 10K
turns/mo even with cache. And the harness includes a bunch of stuff Origami
will never need (filesystem tools, code review primitives, etc.).

---

## 4. Token overhead measured

Measured live against Claude Sonnet 4.5 with the spike's 2 stub tools, the
Origami system prompt, and the sample message
*"Build me a support agent for our Shopify store, with a KB called 'shopify-help'
from our help docs. Use Sonnet."*

| Metric | SDK (2 turns) | Hand-rolled raw (1 turn) | Delta |
|---|---:|---:|---:|
| New input tokens | 34 | 470 | — |
| Cache-read tokens | 100,132 | 0 | huge |
| Output tokens | 1,440 | ~250 | +476% |
| **Total cost** | **$0.097** | **$0.005** | **+1,788% (18.9×)** |

**Why the SDK is more expensive:**

1. ~100K-token cached system harness on every call (CLI tool catalog, hooks,
   internal prompts). Cached, so 10% of input price, but real money at scale.
2. The SDK runs a **second model turn** to execute the confirmed plan — the
   model emits tool_use, the tool runs, the model gets a tool_result and
   writes a "Deployed!" summary. A hand-roll dispatches tools client-side from
   the parsed plan card and writes the summary deterministically (zero model
   cost on confirmation).
3. SDK output runs longer because the model is responding in natural prose +
   tool-use blocks rather than a tight structured JSON.

**Extrapolation to Pro tier (10K turns/month per user quota):**

- SDK: ~$970/month per Pro user in COGS
- Raw: ~$52/month per Pro user in COGS

Pro is priced at $999/mo. SDK-backed Origami has near-zero margin on Pro before
any other usage. Raw-backed Origami has 95% margin.

---

## 5. Hard requirements — met / not met

| Requirement | SDK status | Notes |
|---|---|---|
| **Tool framework** | ✅ Met | `@tool` + `create_sdk_mcp_server`, in-process. |
| **Plan-card structured output** | ⚠️ Workaround | No first-class primitive. System-prompt contract + regex extraction. Brittle. |
| **Interrupt-for-approval** | ✅ Met (with caveat) | `can_use_tool` works, but `allowed_tools` silently bypasses it. |
| **Streaming** | ✅ Met | Block-level out of the box; token-level via `include_partial_messages=True`. |
| **Base URL override → Bonito gateway** | ❌ Not met | Env var seam exists (`ANTHROPIC_BASE_URL`) but gateway format mismatch (Anthropic vs OpenAI). Requires Bonito work or custom Transport. |
| **Multi-provider routing/failover** | ❌ Not met | Anthropic-only. No way to fall back to OpenAI / Bedrock / Groq from the SDK. |
| **Stateless HTTP fit** | ❌ Not met | `ClaudeSDKClient` spawns a per-session subprocess. Doesn't map cleanly to `POST /api/origami/turn`. |
| **Cost reporting** | ✅ Met | `ResultMessage.total_cost_usd` and `usage` dict per turn. |

Two hard requirements failed (base URL, multi-provider). One has a non-trivial
workaround (stateless HTTP). One has a brittle workaround (plan card).

---

## 6. Estimated engineering savings if we use the SDK

Net **savings: ~1 calendar week**. Not the 3 weeks the adversarial review
suggested.

Detailed breakdown:

| Capability | SDK saves | But we still build |
|---|---:|---|
| Tool registration + dispatch | 2-3 days | Bonito API wrappers for the 12 tools (no help from SDK) |
| Anthropic SSE plumbing | 1-2 days | Multi-provider equivalent for failover (not in SDK) |
| `can_use_tool` callback shape | 0.5 days | The approval-state-across-HTTP-requests glue (SDK doesn't help — it's per-session) |
| Conversation history | 1-2 days | Per-user history in our existing memory table (SDK's model doesn't fit stateless HTTP) |
| Plan-card extraction | 0 days | Same prompt+regex either way; SDK has no schema primitive |
| Streaming | 0.5-1 days | Frontend SSE wiring same regardless of source |
| **TOTAL** | **~5 days saved** | |

And we **add** new work:

- Vendor in a Node toolchain so the SDK's CLI subprocess can run on Railway (~0.5 day)
- Build the Anthropic-format gateway endpoint to recover the dogfood story (~2 days)
- Write tests asserting `allowed_tools` doesn't accidentally bypass `can_use_tool`
  (~0.5 day)

Net: ~2 days saved. Possibly negative once you count the COGS at scale.

---

## 7. Lock-in / dependency risks

1. **Anthropic-only upstream.** Origami can't use Bonito's own failover system.
   If Anthropic has a bad day, our flagship demo is dark.
2. **CLI version drift.** SDK pins a Claude Code CLI version range. CLI is on a
   fast release cycle (v2.1.167 today). Each `claude-agent-sdk` bump pulls in
   CLI behavioral changes that may break tool gating, hooks, or output format.
   The SDK warned us in `Transport` source: *"The Claude Code team may change
   or remove this abstract class in any future release."*
3. **MCP protocol is the only tool interface.** All tools must be MCP-shaped.
   That's currently fine but it's a moat-foreign protocol — if MCP loses
   adoption, we've tied our tool surface to it.
4. **Pre-1.0 SDK.** v0.2.93 means breaking changes are normal. Production code
   on a `0.x` SDK requires every dependency bump to be treated as a
   semver-major.
5. **Telemetry leakage.** Anthropic CLI phones home for usage telemetry by
   default (`CLAUDE_CODE_*` env vars). Need to audit + lock down before
   production. Otherwise per-customer Origami runs are visible to Anthropic in
   aggregate.

---

## 8. Conditional path (if we want to revisit)

If two things change, the SDK becomes more interesting:

1. **Bonito ships an Anthropic-format gateway endpoint** (`/v1/messages` with
   LiteLLM translation) — this restores the dogfood story AND opens up
   integrating any Anthropic-SDK customer's code into Bonito.
2. **Anthropic ships a true HTTP-only Python SDK** without the CLI dependency.
   The newer `client.messages.create()` in `anthropic` already does most of
   what `claude-agent-sdk` does; the only gaps are `@tool` ergonomics and
   `can_use_tool`. Those are easy to library-ize.

If both land before Origami ships, re-run this spike.

---

## 9. Files in this spike

- `main.py` — runnable prototype (tested live against Sonnet 4.5)
- `stub_tools.py` — 2 fake Origami tools
- `test_run.py` — measurement harness with raw-API baseline comparison
- `requirements.txt` — `claude-agent-sdk==0.2.93`, `anthropic`, `tiktoken`
- `README.md` — how to run

Replication: `python3.11 -m venv .venv && source .venv/bin/activate && pip
install -r requirements.txt && npm install -g @anthropic-ai/claude-code && python
test_run.py`. Will need `ANTHROPIC_API_KEY` set, or OAuth-authed `claude` CLI
(running inside Claude Code provides this).
