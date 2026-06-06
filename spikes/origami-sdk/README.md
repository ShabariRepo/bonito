# Origami SDK Spike — `claude-agent-sdk`

**Question this spike answers:** Should Bonito's Origami feature be built on
Anthropic's `claude-agent-sdk` (released 2025-09), or hand-rolled on raw
provider API calls?

**TL;DR verdict:** **SKIP THE SDK.** See `notes.md` for the full argument; the
three load-bearing reasons are (1) the SDK shells out to the `claude` CLI binary
which speaks Anthropic-format `/v1/messages` while Bonito's gateway only speaks
OpenAI-format `/v1/chat/completions` — pointing the SDK at the gateway 404s, so
the dogfood story breaks; (2) measured 18.9× cost overhead vs hand-rolled raw
API; (3) hard Anthropic lock-in eliminates the multi-provider failover that is
Bonito's product.

## What's in here

| File | Purpose |
|---|---|
| `main.py` | Minimal Origami prototype using the SDK. Demonstrates: tool framework via `@tool` + `create_sdk_mcp_server`, plan-card emission via system-prompt contract, user-confirmation interrupt via `can_use_tool`, block-level streaming, gateway routing seam via `env`. |
| `stub_tools.py` | Two stub Origami tools (`create_agent`, `create_kb`) — print what they'd do, return structured results. No DB, no real API. |
| `test_run.py` | End-to-end scenario run + measures SDK token usage and compares against the hand-rolled raw Anthropic Messages API baseline (`count_tokens` on the same schemas). Prints the delta. |
| `notes.md` | Build-vs-buy recommendation, what worked, what didn't, token overhead numbers, hard-requirement gaps, engineering savings estimate, lock-in risks. **Read this for the decision.** |
| `requirements.txt` | `claude-agent-sdk==0.2.93`, `anthropic`, `tiktoken`. |

## How to run

```bash
cd spikes/origami-sdk
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# REQUIRED: the SDK shells out to the `claude` CLI binary.
npm install -g @anthropic-ai/claude-code

# Auth — either OAuth (run `claude` once interactively) or:
export ANTHROPIC_API_KEY=sk-ant-...

# Smoke run (talks to live Claude API via the CLI):
python main.py

# Token measurement + raw-API baseline comparison:
python test_run.py
```

## Routing through the Bonito gateway

The spec asked us to point the SDK at `https://api.getbonito.com/v1/chat/completions`
with a `bn-` key. There's a wiring seam (`ROUTE_VIA_BONITO=1` env var) that sets
`ANTHROPIC_BASE_URL` on the subprocess CLI — but this **does not work today**
because the SDK/CLI speaks Anthropic format (`POST /v1/messages`) while Bonito's
gateway is OpenAI-shaped (`POST /v1/chat/completions`). To make this work we'd
need either:

- Ship a new `/v1/messages` endpoint on the Bonito gateway that translates
  Anthropic-format requests into LiteLLM (1–2 engineering days), OR
- Use a custom `Transport` subclass that HTTP-talks to `/v1/chat/completions`
  directly, bypassing the CLI entirely — at which point we're rebuilding the SDK

`notes.md` covers this in detail under "Hard requirements."

## What this spike does NOT cover

- Memory primitives (the SDK has session forking + persistent stores, didn't probe)
- Multi-turn conversation across HTTP requests (we use a single `ClaudeSDKClient`
  context manager; production Origami needs per-user conversation persistence
  across stateless HTTP)
- The `delegate_provider_connection` browser-modal handoff
- Tier-gate logic injection per turn
- Cost at 10K turns/month (extrapolated in `notes.md`, not measured)
