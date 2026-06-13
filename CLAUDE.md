# Bonito — CLAUDE.md

## What is Bonito?

Bonito is an enterprise AI operations platform — a unified control plane for managing AI workloads across multiple cloud providers. It gives engineering and platform teams one layer to connect providers, enforce governance, track costs, route requests, and deploy AI agents.

**Live at:** https://getbonito.com
**API:** https://api.getbonito.com
**Contact:** shabari@bonito.ai

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, Framer Motion |
| Backend | Python FastAPI, async/await, uvicorn |
| Database | PostgreSQL 18.2 + pgvector (HNSW), SQLAlchemy, Alembic |
| Vector Store | pgvector with 768-dim embeddings (GCP text-embedding-005) |
| Cache | Redis 7 |
| Secrets | HashiCorp Vault (prod), SOPS + age (dev) |
| Infra | Docker Compose (local), Vercel + Railway (prod) |
| CLI | Python (Typer + Rich), published as `bonito-cli` on PyPI |
| MCP Server | `bonito-mcp` — 18 tools for Claude Desktop / MCP clients |

## Project Structure

```
bonito/
├── frontend/              # Next.js 14 app (port 3001)
│   └── src/
│       ├── app/           # App Router pages
│       └── components/    # UI components
├── backend/               # FastAPI app (port 8001)
│   ├── app/
│   │   ├── api/routes/    # Route handlers
│   │   ├── core/          # Config, DB, Vault client
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   └── services/      # Business logic
│   └── alembic/           # DB migrations (numbered: 001_, 002_, ...)
├── cli/                   # bonito-cli (Typer)
├── mcp-server/            # MCP server package
├── vault/                 # Vault init scripts
├── secrets/               # SOPS encrypted secrets
├── docs/                  # Architecture, pricing, features docs
└── docker-compose.yml
```

## Services (Local Dev)

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3001 | Next.js web app |
| Backend | 8001 | FastAPI REST API |
| PostgreSQL + pgvector | 5433 | Primary database + vector store |
| Redis | 6380 | Cache & sessions |
| Vault | 8200 | Secrets management (token: `bonito-dev-token`) |

## Production Deployment

- **Frontend:** Vercel (with API rewrites to Railway backend)
- **Backend:** Railway (FastAPI + uvicorn, 2 async workers)
- **Database:** Railway PostgreSQL (connection pool 10+20 per worker)
- **Redis:** Railway
- **Vault:** Railway (or env var fallback — recommended to start)
- **Migrations:** Auto-run on deploy via `backend/start-prod.sh` (`alembic upgrade head`)
- **CI/CD:** GitHub Actions — test -> lint -> build -> deploy on push to `main`

## Supported AI Providers (6)

1. AWS Bedrock (with auto cross-region inference profiles)
2. Azure AI Foundry / Azure OpenAI
3. Google Vertex AI
4. OpenAI (direct)
5. Anthropic (direct)
6. Groq (fast OSS inference)

## Core Features (23 Phases)

1. **Multi-cloud gateway** — OpenAI-compatible API proxy across chat, images, and video. `POST /v1/chat/completions` (LiteLLM-backed), `POST /v1/images/generations` (dall-e-3, dall-e-2, gpt-image-1), `POST /v1/videos` + `GET /v1/videos/{id}` + `GET /v1/videos/{id}/content` (Sora-2, Veo 2.0/3.0/3.1). All endpoints share the same `bn-` prefix API keys, cost tracking, and audit log. Customers like AdVan use this for chat AND creative-asset generation through one credential.
2. **Auto cross-region inference** — Bedrock models transparently routed via `us.` prefix when needed
3. **Intelligent multi-provider failover** — Detects rate limits, timeouts, 5xx, model unavailability; retries on equivalent models across providers
4. **AI Context (Knowledge Base)** — Cross-cloud RAG pipeline: upload/parse/chunk/embed docs, pgvector HNSW search, gateway context injection, source citations
5. **Bonobot AI Agents** — Enterprise agent framework with visual canvas (React Flow), project-based org, built-in tools (KB search, HTTP, agent-to-agent), enterprise security (default deny, budget stops, rate limiting, SSRF protection, audit trail)
6. **Shared Conversational Memory (Memwright)** — Per-session memory via SQLite + ChromaDB, model tier gating (zero memory for small models)
7. **Persistent Agent Memory** — Long-term memory with pgvector similarity search, 5 memory types, AI-powered extraction
8. **Scheduled Autonomous Execution** — Cron-based agent tasks, timezone support, multi-channel delivery (webhook/email/Slack)
9. **Approval Queue / Human-in-the-Loop** — Risk assessment, auto-approve conditions, timeout handling, audit trails
10. **Org Secrets Store** — HashiCorp Vault-backed key-value storage, runtime injection into agent system prompts
11. **VectorBoost (KB Compression)** — 3.9-8x storage reduction (scalar-8bit, polar-8bit, polar-4bit)
12. **SAML SSO** — Okta, Azure AD, Google Workspace, Custom SAML; SSO enforcement, break-glass admin, JIT provisioning
13. **Governance & compliance** — SOC-2, HIPAA, GDPR, ISO27001 policy checks across all 3 clouds
14. **Cost intelligence** — Real-time aggregation, forecasting, optimization recommendations
15. **Routing policies** — Visual builder, 5 strategies (cost/latency/balanced/failover/ab_test)
16. **Model playground** — Live testing, parameter tuning, side-by-side comparison (max 4)
17. **One-click model activation** — Enable models from Bonito UI (Bedrock entitlements, Azure deployments, GCP API enable)
18. **AI Copilot** — Groq-powered operations assistant with org-aware context and function-calling tools
19. **Agent HPA (Autoscaling)** — Elastic agent capacity scaling. Virtual mode doubles effective RPM in Redis when utilization crosses threshold (default 60%). Scale-down via background loop (30s). Configurable via API, CLI (`bonito agents scaling`), and bonito.yaml `scaling` block. Enterprise+ only. Migration 043.
20. **Overflow Queue** — When agents hit RPM ceiling (even after HPA max_replicas), requests are queued not dropped. Returns 202 Accepted with ticket_id + poll_url. Background drainer (2s interval, batch 3) processes queued requests as capacity frees up. Max depth 500/agent, results in Redis (1h TTL). CLI: `bonito agents scaling queue`. Requires `autoscale_enabled: true`.
21. **Token Efficiency Metrics** — Gateway dashboard shows cost per 1K tokens: overall stat card, per-model breakdown, and per-request in logs table. Enables comparison of model cost-effectiveness across providers.
22. **Custom Error Pages** — Branded error pages with bonito fish theme for better UX. Covers 404 (not found), 403 (forbidden), 500 (server error), 503 (service unavailable), and general errors. Each page features unique fish-themed ASCII art, animations via Framer Motion, and contextual messaging.
23. **Creative-asset generation** — Gateway endpoints for image (`POST /v1/images/generations` — dall-e-3, dall-e-2, gpt-image-1) and video (`POST /v1/videos`, `GET /v1/videos/{id}`, `GET /v1/videos/{id}/content` — Sora-2, Veo 2.0/3.0/3.1) generation alongside chat. Same `bn-` key, same auth, same cost tracking, same audit log as chat. Powers AdVan's campaign workflows and the local `creative-pipeline` orchestrator (~/Desktop/code/creative-pipeline) used for Memory Creative / Peller / Bonito's own event videos. See the Recent Changes entry "Creative-asset gateway endpoints (2026-05-20)" for commit refs.

## Pricing Tiers

- **Free** — 3 providers, 25K requests/mo, 3 seats, 1 agent, basic failover, invite-only
- **Builder** — $49/mo, 3 providers, 100K requests/mo, 1 seat, 10 agents, RAG (1 KB), CLI. For solo builders / indie devs.
- **Starter** — $199/mo, 3 providers, 100K requests/mo, 5 seats, 2 agents, RAG (2 KBs), analytics, audit trail, CLI, email support. "Swipe your card" tier — no procurement approval needed.
- **Growth** — $349/mo, 3 providers, 250K requests/mo, 5 seats, 50 agents, RAG (5 KBs), approval queue, scheduled execution, persistent agent memory. For small teams scaling agents across multiple workstreams.
- **Pro** — $999/mo, 5 providers, 500K requests/mo, unlimited seats, 5 agents, advanced routing, RAG (5 KBs), analytics, audit trail
- **Enterprise** — starts at $6K/mo (typical band $6K-$20K depending on volume), unlimited providers/requests/seats, SSO/SAML, RBAC, compliance, 99.9% SLA. Single SKU; Enterprise+ tier with dedicated infra + multi-region + named TAM is on the roadmap.
- **Scale** — Custom ($200K+/yr), dedicated infra, multi-region, 99.99% SLA, custom fine-tuning, dedicated account team

## Key Architectural Patterns

- **Auth:** JWT bearer tokens via `Depends(get_current_user)`. Gateway uses separate `bn-` prefix API keys. Personal access tokens (`bp-`) and project tokens (`bj-`) also resolved in `get_current_user()` — PATs work on all endpoints, project tokens enforce `_project_scope`.
- **Multi-tenancy:** Every table has `org_id` FK with `ondelete="CASCADE"`. ALL queries filter by `user.org_id`.
- **Credentials:** Stored in Vault (`providers/{provider_id}`), encrypted DB column as fallback.
- **Database:** Async SQLAlchemy with `AsyncSession`. Use `selectinload()` for eager loading. `flush()` within transaction, `commit()` after.
- **Migrations:** Alembic, numbered format (`###_descriptive_name`). Always include `org_id` FK, UUID PKs, timestamps with `server_default=func.now()`.
- **CLI:** Typer + Rich. `ensure_authenticated()` before API calls. `APIError` for error handling.
- **Error handling:** `HTTPException` with appropriate status codes. 422 for validation (Pydantic).
- **Strict schemas:** Agent, connection, group, schedule, and execute schemas use `extra = "forbid"`. Unknown fields return 422.
- **Agent field names:** Use `model_id` (not `model`) for the model field. Put `temperature`/`max_tokens` inside `model_config`. Tool policy shape: `{"mode": "none|all|allowlist|denylist", "allowed": [], "denied": [], "http_allowlist": []}`.
- **Connection types:** `handoff`, `escalation`, `data_feed`, `trigger`. Connection fields are top-level (`target_agent_id`, `connection_type`), not nested in a `config` object.
- **Feature gates:** `feature_gate.require_feature()` for premium features.
- **External orchestration:** `POST /api/agents/{id}/execute` accepts optional `parent_agent_id` field. When set, a synthetic `invoke_agent` delegation record is logged in the parent agent's session so Breadcrumbs can visualise code-orchestrated pipelines. CLI: `--parent-agent`. Zero latency impact — logging happens after execution.

## Gateway Request Flow

1. App sends `POST /v1/chat/completions` with `bn-...` API key
2. Gateway authenticates key -> resolves `org_id`
3. Policy enforcement: model allow-list, spend cap, org restrictions
4. Build/retrieve LiteLLM Router for org (Vault fetch on cache miss, 50 min TTL)
5. LiteLLM proxies request to customer's cloud deployment
6. Response streams back, cost/tokens logged to DB
7. Gateway overhead: ~5-20ms (excluding upstream latency)

## Key Commands

```bash
# Local dev
docker compose up --build -d
docker compose exec backend env PYTHONPATH=/app alembic upgrade head
open http://localhost:3001

# Secrets
SOPS_AGE_KEY_FILE=secrets/age-key.txt sops decrypt secrets/dev.enc.yaml

# Migrations
cd backend && alembic upgrade head
cd backend && alembic revision --autogenerate -m "description"

# CLI
pip install bonito-cli
bonito auth login
bonito deploy -f bonito.yaml
bonito agents list

# Production deploy
cd backend && railway up --service bonito-backend
cd frontend && vercel --prod
```

## Key Documentation

- `ARCHITECTURAL_PATTERNS.md` — 7 core codebase patterns reference
- `docs/PRICING.md` — Plans and pricing
- `docs/BONOBOT-ARCHITECTURE.md` — Agent framework design
- `docs/SECRETS.md` — Org secrets API, CLI, YAML guide
- `docs/VECTORBOOST.md` — KB compression methods and benchmarks
- `docs/KNOWN-ISSUES.md` — Tracking known issues
- `docs/SOC2-ROADMAP.md` — Path to SOC-2 Type II certification

## Recent Changes (2026-06-13)

- **Bedrock spend was invisible in cost tracking — two stacked bugs (2026-06-13):** ~$700/mo of real AWS Bedrock Claude spend showed as ~$0 in Bonito's dashboard. (1) **Provider mislabel:** Bedrock Claude ids (`anthropic.claude-sonnet-4-6-v1`, `us.anthropic.claude-...`) contain "claude" but never the literal "bedrock", so the heuristic in `_resolve_provider_for_log` (services/gateway.py) matched "claude"→"anthropic" before any AWS check — and the correct router-derived `primary_provider` (already computed) was discarded at the assignment. Fixed: prefer `_detect_provider_from_model(...)` / `primary_provider`; both the service and route (`_resolve_provider`) heuristics now detect the Bedrock id shape (region/provider-namespace prefix or `:0` suffix) before bare family checks. (2) **Cost logged as $0:** LiteLLM has no price entry for the Claude 4.6 generation on Bedrock — `cost_per_token`/`completion_cost` raise "This model isn't mapped yet", which both call sites caught and recorded as $0. New `compute_request_cost()` in services/gateway.py tries LiteLLM (with a `bedrock/` prefix) then falls back to a static per-family price table (`_FALLBACK_PRICE_PER_M`, $/1M in,out). Wired into the streaming route path and the non-streaming service path. Observability-only — does not change requests/routing/build behavior. Note: this makes dashboard cost numbers JUMP UP to reflect reality.
- **Origami/Studio prompt caching — flag default OFF (2026-06-13):** Anthropic prompt caching for the orchestrator's static prefix (system prompt ~9.2K tokens + 13 tool schemas), which is byte-identical every iteration/turn. Without it that block was re-billed at full 1x per call (measured 21.8:1 input:output ratio = 95%+ of sonnet-4-6 spend). `_build_gateway_body` marks the system block + last tool with `cache_control: ephemeral` when `ORIGAMI_PROMPT_CACHE` is set AND `_is_anthropic_model(ORIGAMI_MODEL)`. Default OFF (deploy is a no-op); flip `ORIGAMI_PROMPT_CACHE=1` in Railway env (no redeploy) to enable. Pure billing/latency optimization — identical tokens to the model, so the 20/20 build reliability is unchanged. Proven on real Bedrock: 8,470/8,797 prompt tokens (96%) read from cache at ~0.1x on a repeat call. Shared by Studio AND Origami (both run `run_origami_turn` / `_build_gateway_body`).
- **Studio/Origami model failover + Haiku cost finding (2026-06-13):** WE ARE BONITO — Studio now fails over like the platform promises. New `ORIGAMI_FALLBACK_MODELS` env (comma-separated) defines a fallback chain after `ORIGAMI_MODEL`. `_stream_gateway_failover` tries each model; on a PRE-OUTPUT failure (HTTP error OR a 200 SSE `{error:...}` chunk from a dead/rate-limited deployment) it advances to the next model and retries the same turn. Once real output (content/tool delta) is produced it commits (mid-stream failure re-raises, never duplicates). Empty chain ⇒ identical to the prior single-model path (20/20 happy path unchanged). Validated locally: bogus primary → Haiku fallback lands a full build; normal builds 3/3 with the wrapper. PROD failover is LIVE (set 2026-06-13): `ORIGAMI_MODEL=claude-sonnet-4-6` primary, `ORIGAMI_FALLBACK_MODELS=claude-sonnet-4-5,claude-haiku-4-5` (all three confirmed routable via the orchestrator org's `/v1/models`), `ORIGAMI_PROMPT_CACHE=1`. Also measured: **Haiku 4.5 matches Opus build reliability** (RAG 6/6 + teams 2/2 = 8/8 incl. hub-and-spoke) at **~14x lower cost** ($0.50 vs ~$6.84 for the same 8 builds). Local dev default switched to Haiku 4.5 (Opus 4.6 fallback). Prod still runs `claude-sonnet-4-6`.
- **"Bedrock tool-call text-mode bug" was a GHOST — stale local container (2026-06-13):** Local Studio builds via Bedrock appeared to text-mode (return "I've set up the project…" with no tool calls, 0/3). Root cause: the local docker backend had been up 16h running orchestrator code from BEFORE the `tool_call_id` fix + dependency self-heal (both landed earlier 2026-06-13). Old continuations came back empty (orphaned tool results), which surfaces as "claims done, builds nothing". Isolation proved the live model/Router/serialization were all fine — only the stale running process failed. After `docker compose restart backend` loaded current `main`, Bedrock builds land 4/4. **Takeaway:** Bedrock tool-calling works through the full gateway path with current code; there is NO separate Bedrock router bug. Also confirms the 20/20 build reliability applies to Bedrock, not just Anthropic-direct — so the full hackathon test can run locally on Bonito's own AWS/Bedrock creds (cheap, off-prod, cheaper still with prompt caching on). Always restart a long-lived local container before trusting a "bug" repro.

## Recent Changes (2026-06-12)

- **Gateway `tool_call_id` drop fix — ROOT CAUSE of all multi-step agentic build failures (2026-06-12):** `ChatMessage` in `backend/app/schemas/gateway.py` was missing the `tool_call_id` field, so Pydantic SILENTLY DROPPED it from `{"role":"tool", "tool_call_id":...}` result messages. Anthropic/LiteLLM require `tool_call_id` to match a tool result to its originating call — without it the result is orphaned and the upstream returns an EMPTY completion (finish_reason None, no content, no tool_calls). Effect: in any multi-tool build (Studio/Origami), the first resource lands in iteration 0, then every follow-up turn comes back empty, so resource #2+ is never created. Single-step builds (one project, one KB, one key) were unaffected because they need no continuation — which is exactly why single creates always worked but project+KB+agent never did. This masqueraded as "model reluctance to create agents"; it was a one-line schema gap. Same lossy-schema class as the earlier `tools`/`tool_choice` drop (also fixed today). Forwarded downstream automatically via `request.model_dump(exclude_none=True)`. Verified: Studio multi-step builds 3/3 land project+KB+agent; full 5-account bootcamp passes 5/5 with 0 exec failures.
- **Idempotent `create_kb` (2026-06-12):** The model occasionally re-emits `create_kb` with a name it already created earlier in the same build (loses track across tool-result round-trips). `knowledge_bases` has a UNIQUE `(org_id, name)` index, so the 2nd INSERT raised `IntegrityError` mid-flush, poisoning the SQLAlchemy session and cascading failures onto every later tool in that batch (`create_agent`, `link_kb_to_agent`). Fix in `create_kb.py`: pre-check for an existing same-named KB and return it as success (`idempotent: true`), plus an `IntegrityError` safety net that rolls back and returns the winning row on a race. Only KB has this unique constraint; projects/agents allow duplicate names so they're unaffected.

## Recent Changes (2026-05-06)

- **Custom error pages (2026-05-30):** Bonito-themed error pages for better UX. Added 5 error page variations: 404 (swimming fish with bubbles), 403 (locked treasure with fish), 500 (belly-up fish with sinking bubbles), 503 (fish in drydock with 60s auto-retry countdown), and global error (catastrophic fish). Each page uses Framer Motion animations, fish ASCII art, and contextual messaging. Updated `global-error.tsx` from plain HTML to bonito theme. Files: `frontend/src/app/{not-found,error,global-error,error-403/page,error-500/page,error-503/page}.tsx`. Routes renamed from `/403`, `/500`, `/503` to `/error-403`, `/error-500`, `/error-503` to avoid Next.js reserved route conflicts.
- **Starter tier (2026-05-28):** New $199/mo tier between Free and Pro. 3 providers, 100K requests/mo, 5 seats, 2 agents, RAG (2 KBs), analytics, audit trail, CLI, email support. Bridges the $0→$999 gap for teams that want to swipe a card without procurement approval. Updated: `feature_gate.py` (enum + TIER_CONFIG), `dependencies.py` (tier hierarchy), `access_tokens.py` (PAT limits: 5), `log_service.py` (retention: 45d), CLI tier displays, frontend settings/sidebar/pricing page, admin org page, PRICING.md.
- **KB search quality fix (2026-05-24):** `_tool_search_kb` threshold lowered from 0.7 → 0.5 (was filtering out relevant results that RAG injection at 0.4 would return). Added `MODEL_MAX_DIMENSIONS` map in `EmbeddingGenerator` to clamp requested dimensions to model's max — fixes silent ingestion failures when GCP `text-embedding-005` (768 max) is used with KB default of 1024 dims.
- **Invite-only registration:** Access request flow (submit → admin approve → invite code → register). Controlled by `INVITE_REQUIRED` env var (default: true). Rate limited at 5 req/60s.
- **Memwright hardening:** Fixed `clear()` lambda bug, added LRU eviction (256 max instances), graceful degradation when `agent_memory` not installed, removed startup pre-warm (caused SQLite locking with multi-worker uvicorn).
- **Dockerfile fixes:** `HOME=/app`, `HF_HOME`/`TRANSFORMERS_CACHE` set, sentence-transformers model pre-downloaded at build time. Fixes ChromaDB vector_similarity layer in production.
- **VectorBoost gated:** KB config endpoints require Enterprise+ tier. Note: compression pipeline is NOT wired into ingestion yet — gating prevents customers from configuring a feature that doesn't fully work.
- **AdVan integration:** Uses memwright standalone (ChromaDB + SQLite) in their own app.py. Bonito is their LLM gateway only. Changes to Bonito's MemwrightService do NOT affect them. Do not break this.
- **Free tier:** 3 providers, 25K gateway requests/month, 3 seats, CLI access enabled.
- **Provider connection fixes (2026-05-06):** Fixed all 6 providers connectable via UI (connect modal + onboarding wizard). Anthropic validation uses `/v1/models` instead of hardcoded model. Groq added to connect modal and onboarding. Connect modal uses `apiRequest()` for JWT auth.
- **Background model sync (2026-05-06):** `model_sync.py` runs every 24h, syncs models for all active providers. Anthropic now uses live API + static pricing fallback. Wired into FastAPI lifespan.
- **Credential storage fix (2026-05-06):** Legacy `POST/PATCH /api/providers` endpoints now encrypt credentials (were storing plain JSON). DB fallback auto-migrates plain JSON → AES-256-GCM on read. Bedrock `_check_model_access` fixed to use real API.
- **Admin access requests (2026-05-06):** Admin UI page at `/admin/access-requests` for invite-only registration approval flow.
- **Sentry backend integration (2026-05-12):** Added `sentry-sdk[fastapi]` to backend. Initializes before FastAPI app, environment-aware sampling (20% prod, 100% dev). DSN via `SENTRY_DSN` env var.
- **Sentry frontend integration (2026-05-12):** Created `bonito-frontend` Sentry project via API. Added `@sentry/nextjs` SDK with client/server/edge configs, instrumentation hook, global error boundary, source map upload via `withSentryConfig`.
- **API schema hardening (2026-05-12):** All Bonobot create/update schemas now reject unknown fields with `extra="forbid"` (422 instead of silent drop). Affected: AgentCreate, AgentUpdate, AgentConnectionCreate, AgentGroupCreate/Update, AgentExecuteRequest, AgentScheduleCreate/Update.
- **Sentry tracking doc (2026-05-12):** Added `docs/SENTRY.md` covering backend (done), frontend (done), and future Helios MCP integration plan.
- **Creative-asset gateway endpoints (2026-05-20):** Bonito's gateway supports image AND video generation alongside chat. Merged via `feat/creative-pipeline`, live on Railway. Any customer with a `bn-` key (AdVan, etc.) can call these — same auth, same cost tracking, same audit log as chat. Two pieces:
  - **Image generation:** `POST /v1/images/generations` (commit `aadb510`). Models: `dall-e-3`, `dall-e-2`, `gpt-image-1`. Cost maps in `gateway.py:1301-1303`.
  - **Video generation:** `POST /v1/videos` (submit, commit `cb6cc30`), `GET /v1/videos/{id}` (poll status), `GET /v1/videos/{id}/content` (download mp4). Models: OpenAI Sora-2 and Vertex AI Veo 2.0/3.0/3.1. Credentials injected from Vault/DB via `_get_video_credentials()` since LiteLLM Router doesn't support video yet. Status/content polling also injects credentials (decoded from base64 video_id). Cost tracking via `_VIDEO_COST_FALLBACK` per-second pricing. Credential-injection fix in commit `b2eb8bf`.
- **Creative-pipeline orchestrator (2026-05-20):** **Separate local-only Python script repo** at `~/Desktop/code/creative-pipeline/`. NOT a deployed Bonito service, NOT in this repo, and **has no git remote** — 4 commits, never pushed; if Shabari's laptop dies the code is gone. It's a 6-stage workflow (Brief → Research → Ideation → Production → Review → Publish) that runs on Shabari's laptop and calls Bonito's prod gateway (via `bonito_client.py`) for every AI call. Files: `app.py`, `pipeline.py`, `produce_bonito_ad.py`, `produce_bomb_ad.py`. Built for the Memory Creative deal; tested with Peller Estates "Niagara Nights" campaign (4 images + 1 video, 94% review score) and used to produce Bonito's own event/sales-ad videos. **Do not conflate this with the gateway endpoints above** — the orchestrator is a script set on a laptop; the gateway endpoints it depends on are in this repo, on main, in prod. Turning the orchestrator into a hosted service is a separate decision (would also want to push the repo to a remote first).
- **External orchestration / Breadcrumbs tracing (2026-05-23):** `POST /api/agents/{id}/execute` now accepts optional `parent_agent_id`. When set, a synthetic `invoke_agent` tool-call message is logged in the parent agent's session, letting code-orchestrated pipelines (like Duncan Lane) appear in Breadcrumbs with zero latency impact. CLI flag: `--parent-agent`. Documented in BONOBOT-ARCHITECTURE.md.
- **Agent Health dashboard (2026-05-23):** Platform admin page at `/admin/agent-health` showing model health across all orgs. `GET /api/admin/agent-health` cross-references agent model_ids against available provider models to detect deprecated or unroutable models. Background check runs after every 24h model sync via `_check_agent_model_health()` in `model_sync.py`. Includes summary cards, search/filter, and per-agent health badges (Healthy, Deprecated, No Route, Warning).
- **Gateway duplicate provider fix (2026-05-23):** `_get_provider_credentials()` now keys by provider UUID instead of provider_type, fixing silent credential overwrites when orgs have multiple providers of the same type. `DELETE /api/providers/{id}` fixed (missing commit). All provider CRUD endpoints now call `reset_router()` for immediate cache invalidation instead of waiting 50min TTL.
- **KB delete fix (2026-05-25):** ORM cascade on `db.delete(kb)` triggered pgvector OID 24578 error because `ARRAY(Float)` can't deserialize `vector` type. Fixed with raw SQL `sa_delete()` statements — deletes chunks → documents → KB without loading row data (PRs #43040-#43042).
- **KB vector dimension fix (2026-05-25):** pgvector column was `vector(768)` but Titan Embed V2 returns 1024-dim natively (dimensions param stripped via `SKIP_DIMENSIONS_PARAM`). Migration 041 NULLs existing embeddings, alters to `vector(1024)`, backfills KBs to `embedding_dimensions=1024`. Schema default changed from 768 → 1024 (PRs #43044-#43045).
- **Alembic multiple heads fix (2026-05-25):** `a1b2c3d4e5f6` (discover_logs) and `041` both branched from `040`, causing "Multiple head revisions" error — **no migration had run on prod since May 15**. Merge migration 042 resolves the split (PR #43046).
- **pgvector greenlet_spawn fix (2026-05-25):** Moved pgvector type codec registration from SQLAlchemy `connect` event to `checkout` event. `connect` can fire during pool pre-ping/recycling outside the async greenlet context, causing intermittent 500 errors during agent execution. `checkout` always fires within the async context. Cached per `connection_record` (PR #43047).
- **Ingestion error handler fix (2026-05-25):** Added `db.rollback()` before updating doc status to "error" — without this, a failed INSERT (e.g. dimension mismatch) corrupts the SQLAlchemy session, preventing the status update, leaving docs stuck at "processing" forever (PR #43045).
- **GCS fast-fail (2026-05-25):** `gcs_storage.py` now fails immediately with `_client_failed` flag when no GCS credentials configured, instead of hanging 43s trying Compute Engine metadata server on Railway (PR #43043).
- **Embedding timeout (2026-05-25):** Increased `EMBEDDING_TIMEOUT` from 30s → 90s for Bedrock Titan V2 under rate limiting (PR #43043).

## What's Planned

- **Origami-as-MCP (post-Studio play)** — Once Studio is the primary in-app surface, repurpose Origami's orchestrator (system prompt + 13 tools + plan validator + retry loop) as an MCP tool: `bonito.build(intent)`. Claude Desktop / Cursor / any MCP client sends a natural-language request, the orchestrator plans + executes server-side, returns a build summary + Studio deep-link. Differs from existing `bonito-mcp` (raw tools list) by exposing the *high-level planner*. Auth via `bp-` PATs (already cross-surface). Open questions: streaming model (likely request/response — final summary only), auto-deploy vs structured `bonito.deploy(plan_id)` second call, per-PAT turn quotas. Idea source: Shabari 2026-06-12, validated against the multi-cloud-moat thesis. Build only after Studio ships for Tech Week.
- **Bonito Studio (chat-first front door)** — Replaces post-auth `/` with a clean, full-bleed chat surface. Existing dashboard moves to `/dashboard`. Reuses Origami's orchestrator/SSE/tool-registry wholesale; net-new is `/api/studio/init` (org snapshot — providers, agents, KBs, 7d gateway usage, billing) + `/api/studio/chat` (orchestrator with new BDR system prompt + snapshot context). Agent voice is first-person, warm, professional. Opens with something specific to the org's state, never generic. Sidebar default-collapsed, 23 features grouped into 7 nav items (Dashboard / Agents / Knowledge / Gateway / Integrations / Team / Settings). Free on all tiers. Direct response to Danny Pantuso (Mucker) feedback 2026-06-12. Target: Jul 17 demo-ready for Tech Week (Jul 20–26). Full spec in `docs/BONITO-STUDIO-PLAN.md`.
- **Origami (interactive build workspace)** — Bonito's in-app split-pane interface: chat panel (left) + live workspace pane (right) showing resources being built, activity log, plan cards, and result previews. Replit-style "watch the agent work" UX, simpler. Hand-rolled orchestrator on Bonito gateway (NOT `claude-agent-sdk` — 18.9× token overhead measured in spike 2026-06-06, plus SDK can't route through our gateway). 13-tool MVP surface (agents, KBs, projects, keys, usage, delegate_provider_connection). `og-` token strictly bound to one (user_id, org_id) pair. SSE event stream for live workspace updates. Tier-gated with upgrade-in-place via inline Stripe Checkout. SMB wedge validated by Danny Pantuso (Mucker) 2026-06-06. Full spec in `docs/ORIGAMI-MVP-PLAN.md`. Branch `origami-mvp`. Target: ~9-10 weeks (recalibrated from 6 after adversarial review). Pricing: chat included on every tier; Free 50 / Builder 100 / Growth 300 / Pro 1K / Enterprise 5K turns/mo base; $0.12/turn overage on paid tiers, $0.10 Enterprise.
- **System Observer** — Two-layer observability: L1 wires `emit_agent_event` into agent engine (execution, tool_use, delegation, error lifecycle events with agent_id). L2 is a Bonito-internal Haiku/Groq agent per org (6h schedule) that reads aggregated metrics and produces structured health/governance findings. See `docs/SYSTEM-OBSERVER-ROADMAP.md`.
- SOC-2 Type II certification
- Smart routing (complexity-aware model selection)
- VPC Gateway Agent (enterprise self-hosted data plane)
- Additional provider integrations (Cohere, Mistral, custom endpoints)
- Advanced audit log export & SIEM integration
- VectorBoost: Wire compression pipeline into KB ingestion (currently endpoint-only, not functional)
- Vault org-namespacing: Move credential paths from `providers/{provider_id}` to `providers/{org_id}/{provider_id}` for proper tenant isolation
- Queue drainer advisory lock: Add PostgreSQL advisory lock to `agent_queue.py` background drainer (like autoscaler uses lock 839272) to prevent 4 workers competing on the same queue
- **Provider tests CI infrastructure (KNOWN-ISSUES #37):** `.github/workflows/ci.yml` lacks pgvector + Vault, so ~20 provider connect tests return 500 in CI. Fix: swap `postgres:16` → `pgvector/pgvector:pg16`, add a `vault` service block with `VAULT_DEV_ROOT_TOKEN_ID=test-token`, add a setup step that runs `CREATE EXTENSION IF NOT EXISTS vector` on the test DB. Blocks PR merges when branch protection requires green checks.
- ~~Log retention tier gating~~ Done (2026-05-27): Per-org retention cleanup based on subscription tier (Free=30d, Pro=60d, Enterprise/Scale=90d). Settings UI locked to tier max.
- ~~Gateway Vault fallback~~ ✅ Done (2026-05-24): `_get_provider_credentials()` now uses `_get_provider_secrets()` with Vault → encrypted DB fallback chain
- ~~Agent HPA~~ ✅ Done (2026-05-25): Phase 1 virtual scaling — reactive scale-up in `_check_rate_limit`, background scale-down loop (30s, advisory lock 839272). Agent model gains `autoscale_enabled`, `autoscale_config`, `primary_agent_id`, `replica_index`. New `agent_scaling_events` audit table (migration 043). API endpoints: `GET/POST /agents/{id}/scaling/*`. CLI: `bonito agents scaling status/configure/events/manual`. YAML: `scaling` block in agent config. Feature-gated to Enterprise+ (`agent_hpa`). Phase 2 (physical replicas with load balancer) planned but not yet built.
- **Token efficiency metrics (2026-05-26):** Gateway dashboard (`/gateway`) now shows cost per 1K tokens at three levels: overall stat card (Gauge icon), per-model in model breakdown, and per-request in logs table. Enables side-by-side model cost-effectiveness comparison.
- **Overflow queue (2026-05-25):** Redis-backed FIFO queue per agent (`agent_queue.py`). When `_check_rate_limit` raises `AgentRateLimitError`, execute endpoint enqueues and returns 202 Accepted with ticket_id + poll_url. Background drainer (2s interval, batch 3) retries queued requests as RPM capacity frees up. Poll via `GET /agents/{id}/queue/{ticket_id}`. Queue depth via `GET /agents/{id}/queue`. CLI: `bonito agents scaling queue <id>`. Max depth 500, result TTL 1h. Only active for agents with `autoscale_enabled: true`. IP rate limit for `/api/agents/` raised to 500/60s to avoid middleware interference.
- **UX onboarding improvements (2026-05-27):** Settings page now shows subscription tier badge (Crown icon, Free/Pro/Enterprise/Scale with per-tier colors). Sidebar nav items that require a higher tier show "Pro" or "Ent" badges and redirect to settings when clicked. KB cards show yellow guidance banner when pending with 0 documents ("Upload documents to activate"). `/api/auth/me` now returns `subscription_tier` field.
- **KB linked-agents fix (2026-05-27):** `GET /api/knowledge-bases/{id}/linked-agents` was throwing `CannotCoerceError: cannot cast type jsonb to text[]`. Fixed to use JSONB `@>` containment operator via `type_coerce` instead of `CAST(... AS TEXT[])`.
- **Queue drainer noise fix (2026-05-27):** Agent overflow queue drainer was running Redis `SCAN agent_queue:*` every 2 seconds even when completely idle. Added adaptive polling: 2s when active, backs off to 30s after 3 idle cycles.
- **Personal Access Tokens & Project Tokens (2026-05-27):** New `access_tokens` table (migration 044). PATs (`bp-` prefix) carry user permissions and work on ALL endpoints (`/api/*` + `/v1/*`). Project tokens (`bj-` prefix, Pro+) scoped to a single project — only org admins (`user.role == "admin"`) can create/revoke project tokens. `check_project_scope()` enforces that `bj-` tokens can only access their assigned project (403 on cross-project). Auth dependency (`get_current_user`) handles bp-/bj- prefixes alongside JWT. Gateway `get_auth_context` supports bp- for `/v1/*`. API: `GET/POST /api/tokens`, `DELETE /api/tokens/{id}`, `GET/POST /api/projects/{id}/tokens`. CLI: `bonito auth token create/list/revoke/login`. Frontend: PAT card in Settings with tooltips. Tier limits (PAT, per user): Free=2, Starter=5, Pro=10, Enterprise=999, Scale=999. Tier limits (project tokens, per org): Pro=20, Enterprise=999, Scale=999 (Pro+ tier-gated AND admin-only). Caps enforced in `access_tokens.py` via `PAT_LIMITS` and `PROJECT_TOKEN_LIMITS` constants.
- **Log retention tier gating (2026-05-27):** Retention cleanup now runs per-org based on subscription tier: Free=30d, Pro=60d, Enterprise/Scale=90d. Previously used a single global `LOG_RETENTION_DAYS` env var (default 90d) for all orgs. Settings UI now shows tier-appropriate options with locked indicators for higher tiers.
- **GCS log sink org-partitioned (2026-05-27):** Restructured `gcs_log_sink.py` from flat `logs/{date}/{server}.ndjson` to `{org_id}/{log_type}/{YYYY}/{MM}/{DD}/{HH}.ndjson`. Buffers keyed by `(org_id, log_type)`. 10 log types: gateway, agent, auth, kb, admin, deployment, billing, compliance, approval, system. Each NDJSON line includes a `feature` field for sub-feature identification (e.g. `failover` within gateway, `scheduler` within agent, `sso` within auth). Middleware infers both `log_type` and `feature` from URL path. Messages prefixed with `[feature]` for readability. Enables per-org GCS lifecycle rules for tier-based retention and structured Helios ingestion.
