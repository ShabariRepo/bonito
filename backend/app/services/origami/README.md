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
| `ORIGAMI_GATEWAY_KEY` | yes | — | A `bn-` key from Bonito's **system org** (`cat.shabari` today; permanent system-org via Vault in Phase 1.5). Same key for every customer's Origami session — see "Billing architecture" below. |
| `BONITO_GATEWAY_URL` | no | `http://localhost:8001` | Where to POST chat completions. Local dev → `http://localhost:8001`. Prod → `http://localhost:8080`. See "Why localhost in prod" below. |

### Why `localhost` in prod

The Origami orchestrator and the gateway endpoint (`POST /v1/chat/completions`) are part of the same FastAPI application running in the same Railway container. When the orchestrator calls the gateway, it's calling itself — `localhost` resolves to the container's own loopback interface, which is the same uvicorn process.

The port on Railway is whatever `$PORT` is set to (currently `8080`). The full prod value is `http://localhost:8080`.

Compared to the alternatives:

| URL | Per-call latency | When you'd use it |
|---|---|---|
| `http://localhost:8080` | ~0.1 ms (kernel loopback, no network) | **Default — current setup** |
| `http://bonito-backend.railway.internal:8080` | 1-5 ms (Railway private network) | If gateway and orchestrator ever split into separate Railway services |
| `https://api.getbonito.com` | 20-50 ms + TLS handshake (out to public DNS, CDN, back to same container) | Last resort. Adds 100-750 ms per Origami turn (each turn fires 5-15 internal calls). |

If you ever see `gateway_call_failed: All connection attempts failed` in prod, check:
1. `BONITO_GATEWAY_URL` set correctly on Railway (must match `$PORT`)
2. `ORIGAMI_GATEWAY_KEY` set on Railway (a `bn-` key from a real Bonito org with Sonnet 4.6 + Opus 4.7 routable)
3. uvicorn actually bound to that port (check the deploy log: `🚀 Starting uvicorn on port {N}`)

No `ANTHROPIC_API_KEY`, no `OPENAI_API_KEY`, no LLM provider key at all
in the Origami code path — the system org's connected provider creds
live in Vault and the gateway resolves them on the way out.

## Billing architecture

This is a load-bearing piece of how Origami is priced. Two separate
money flows, intentionally:

| Layer | Who's billed | Logged where |
|---|---|---|
| **LLM call to provider** | Bonito (via cat.shabari's connected provider) | `gateway_requests` row attributed to cat.shabari's org → **this is Bonito's COGS** |
| **Customer's Origami "turn"** | Customer's org (their billing) | `origami_turn_log` row attributed to customer's org → **counts against their tier quota → Stripe overage** |

The customer **never pays for the LLM call directly**. They pay per
Origami turn — 50/100/300/1000/5000 base/month by tier, then $0.12/turn
overage on paid tiers ($0.10 on Enterprise). The "Origami included on
every plan" marketing line is true because the LLM cost is Bonito's
COGS, not the customer's.

### Identifying Origami calls in cat.shabari's gateway log

Every gateway call from Origami carries the customer's identity in two
places so cat.shabari's dashboard can break Bonito's Origami COGS down
per customer:

1. **OpenAI `user` field** in the request body: `origami:org:{org_id}:user:{user_id}` (lands in `gateway_requests.team_id`)
2. **`X-Bonito-Source: origami` header** plus `X-Bonito-Origami-Customer-Org` / `X-Bonito-Origami-Customer-User` headers — for any future gateway-side aggregation that wants the raw IDs without parsing the `user` string.

The gateway honors these as metadata only — it never re-attributes cost
to a different org based on a header (that would be a tenant-isolation
hole). Cost stays on cat.shabari, the metadata is just for analytics.

### Customer-facing usage

Customers see Origami usage via the Usage page (Phase 1.5 — task #33):

- Turns used this month vs base quota
- Cost per turn at the overage rate (only if over cap)
- Per-day chart, historical 3-month view

This reads from `origami_turn_log`, never from `gateway_requests`. The
customer doesn't see the underlying LLM cost because that's not what
they're paying for.

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
