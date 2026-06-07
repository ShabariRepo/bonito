# Origami (in-app conversational interface)

Phase 1 skeleton. See `docs/ORIGAMI-MVP-PLAN.md` for the full spec.

## Pieces

```
backend/app/services/origami/
├── auth.py                  # og- token model + get_origami_context dependency
├── orchestrator.py          # tool-calling loop, emits SSE events
├── tools/
│   ├── base.py              # OrigamiTool ABC + global registry + sanitize_params
│   ├── list_org_state.py    # read-only: providers, agents, KBs, projects, tier
│   └── view_usage.py        # read-only: gateway request count + tier headroom
└── ingestion/               # bonito-knowledge KB ingestion (Phase 0, scaffold)

backend/app/api/routes/origami.py    # POST /api/origami/turn (SSE) + /health
frontend/src/components/origami/OrigamiChat.tsx
frontend/src/app/origami/page.tsx
```

## Test it end-to-end

### 1. Backend prereqs

```bash
# From repo root
docker compose up -d postgres redis  # if not running

# Backend deps (anthropic is required for Phase 1)
cd backend
pip install -r requirements.txt
```

### 2. Set env vars

```bash
export ORIGAMI_ANTHROPIC_KEY=sk-ant-...   # or ANTHROPIC_API_KEY
# DATABASE_URL etc. are picked up from .env via app.core.config
```

> TODO Phase 1.5: route LLM calls through the Bonito gateway instead of
> direct Anthropic SDK. When that lands, no key env var is needed — the
> orchestrator uses a system-org `bn-` key from Vault.

### 3. Smoke test the orchestrator (no FastAPI needed)

```bash
cd backend
python scripts/test_origami.py "what providers do I have connected?"
```

You should see colored event output:

```
        turn_started   {"conversation_id": null}
        tool_started   {"tool_name": "list_org_state", "tool_use_id": "tool_..."}
      tool_completed   {"tool_name": "list_org_state", "result_summary": {...}}
    message_complete   {"text": "You have ... providers connected..."}
                done   {"stop_reason": "end_turn", "iteration": 1}
```

### 4. Full end-to-end via the UI

```bash
# Backend
cd backend && uvicorn app.main:app --reload --port 8001

# Frontend (separate terminal)
cd frontend && npm run dev   # serves on :3001

# Open http://localhost:3001/origami in your browser
```

Sign in normally (existing JWT auth), then chat at `/origami`. Click
"Activity" in the header to see tool calls fire as Origami works.

## Health probe

`GET /api/origami/health` (no auth) returns the registered tools — useful
for sanity-checking the import chain in deployed environments:

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

- Switch orchestrator to LiteLLM via Bonito gateway (TODO in `orchestrator.py`)
- Add streaming (currently non-streaming; will emit `message_token` events)
- Wire Memwright + conversation history (currently stateless per turn)
- Add the remaining 11 read+write tools (see `docs/ORIGAMI-MVP-PLAN.md`)
- Plan card + Deploy button + structured output (Phase 2)
- Workspace UX with resources grid (Phase 3)
