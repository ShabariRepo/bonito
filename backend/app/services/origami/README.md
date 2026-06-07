# Origami (in-app conversational interface)

Phase 1 skeleton. See `docs/ORIGAMI-MVP-PLAN.md` for the full spec.

## Architecture summary

Origami is a **customer of Bonito's own gateway** — it POSTs to
`/v1/chat/completions` with a `bn-` system key, exactly like any external
customer would. No `claude-agent-sdk`, no `anthropic` SDK, no direct
LiteLLM call in the Origami code path. LiteLLM lives **inside** the
gateway, which is exactly the dogfood story we want.

```
  Origami orchestrator
        │
        │  httpx POST /v1/chat/completions  (Bearer bn-...)
        ▼
  Bonito gateway  (LiteLLM router lives here)
        │
        ▼  routes to org's connected provider
  Anthropic / Bedrock / Vertex / OpenAI / ...
```

## Pieces

```
backend/app/services/origami/
├── auth.py                  # og- token model + get_origami_context dependency
├── orchestrator.py          # tool-calling loop, calls Bonito gateway, emits SSE events
├── tools/
│   ├── base.py              # OrigamiTool ABC + global registry + sanitize_params
│   ├── list_org_state.py    # read-only: providers, agents, KBs, projects, tier
│   └── view_usage.py        # read-only: gateway request count + tier headroom
└── ingestion/               # bonito-knowledge KB ingestion (Phase 0, scaffold)

backend/app/api/routes/origami.py    # POST /api/origami/turn (SSE) + /health
frontend/src/components/origami/OrigamiChat.tsx
frontend/src/app/origami/page.tsx
```

## Env vars

| Var | Required | Default | Notes |
|---|---|---|---|
| `ORIGAMI_GATEWAY_KEY` | yes | — | A `bn-` key the orchestrator uses to call the gateway. Generate one from any active org (Settings → Gateway Keys) for dev. Production reads a system-org key from Vault (TODO Phase 1.5). |
| `BONITO_GATEWAY_URL` | no | `http://localhost:8001` | Where to POST chat completions. Local dev → `http://localhost:8001`. Prod → `https://api.getbonito.com`. |

No `ANTHROPIC_API_KEY`, no `OPENAI_API_KEY`, no LLM provider key at all
in the Origami code path — the org's connected provider creds live in
Vault and the gateway resolves them on the way out.

## Test it end-to-end

### 1. Prereqs

```bash
# From repo root
docker compose up -d postgres redis backend frontend

# Make sure your org has at least one active provider connected (the
# gateway needs somewhere to route to). Sign in to /settings/providers
# and connect Anthropic / Bedrock / etc. with real creds.
```

### 2. Mint a bn- key for Origami

Settings → Gateway Keys → Create Key → copy the `bn-...` value.

```bash
export ORIGAMI_GATEWAY_KEY=bn-yourkeyhere
```

### 3. Smoke test the orchestrator (no FastAPI server needed)

```bash
cd backend
python scripts/test_origami.py "what providers do I have connected?"
```

Output (colored event stream):

```
        turn_started   {"conversation_id": null}
        tool_started   {"tool_name": "list_org_state", "tool_call_id": "..."}
      tool_completed   {"tool_name": "list_org_state", "result_summary": {...}}
    message_complete   {"text": "You have 2 providers connected..."}
                done   {"finish_reason": "stop", "iteration": 1}
```

### 4. Full UI test

```bash
# Backend (terminal 1)
cd backend && uvicorn app.main:app --reload --port 8001

# Frontend (terminal 2)
cd frontend && npm run dev

# Browser
open http://localhost:3001/origami
```

Sign in normally. Click "Activity" in the chat header to watch tool calls
fire as Origami works.

## Health probe

`GET /api/origami/health` (no auth) returns the registered tools — sanity
check for the import chain in deployed environments:

```bash
curl http://localhost:8001/api/origami/health
# → {"status":"ok","registered_tools":["list_org_state","view_usage"],"tool_count":2}
```

## Security invariants

1. **`org_id` is server-injected.** Every `OrigamiTool.execute()` receives
   `org_id` as an explicit kwarg from `user.org_id` (the JWT auth claim).
   Tools never read `org_id` from `params`.
2. **`sanitize_params` strips `org_id`** from any model-generated tool
   input. Even if Claude hallucinates `{"org_id": "<some-uuid>"}` in a
   tool call, it's removed before `execute()` runs.
3. **Tool `input_schema` deliberately omits `org_id`** so the model never
   sees it as a valid field.
4. **og- token org binding** (when used): `OrigamiContext.org_id` is
   frozen at token creation and read from the token record, never from
   request params.

## What's next

| Status | Item |
|---|---|
| ✅ Done | Tool framework (`OrigamiTool` ABC, registry, sanitize_params) |
| ✅ Done | Read tool: `list_org_state` |
| ✅ Done | Read tool: `view_usage` |
| ✅ Done | Orchestrator loop calling Bonito gateway via httpx |
| ✅ Done | SSE event emission (`turn_started`, `message_complete`, `tool_started`, `tool_completed`, `tool_failed`, `done`, `error`) |
| ✅ Done | Frontend chat at `/origami` with SSE parser + activity log |
| ✅ Done | `og-` token model + `get_origami_context` auth dependency |
| ⏳ Next | 3 more read tools: `view_logs`, `list_available_models`, `check_tier_access` |
| ⏳ Next | Streaming via `stream=True` (emit `message_token` events) |
| ⏳ Phase 1.5 | System-org bn- key in Vault (replace `ORIGAMI_GATEWAY_KEY` env var) |
| ⏳ Phase 1.5 | Memwright session memory across turns |
| ⏳ Phase 1.5 | Migration 046: `origami_audit_log` |
| ⏳ Phase 2 | Plan card + Deploy button + 6 write tools |
| ⏳ Phase 2 | Upgrade-in-place via Stripe Checkout |
| ⏳ Phase 3 | Workspace UX (split-pane with resources grid) |
| ⏳ Phase 4 | Telemetry + Product Hunt launch |
