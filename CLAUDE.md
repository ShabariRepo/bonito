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

## Core Features (All 18 Phases Complete)

1. **Multi-cloud gateway** — OpenAI-compatible API proxy (`POST /v1/chat/completions`), LiteLLM-backed, `bn-` prefix API keys
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

## Pricing Tiers

- **Free** — 1 provider, 25K requests/mo, 1 seat, invite-only
- **Pro** — $499/mo, 3 providers, 250K requests/mo, 10 seats, smart routing + failover
- **Enterprise** — $10K-$20K/mo (annual), unlimited everything, SSO/SAML, advanced compliance
- **Scale** — Custom ($200K+/yr), dedicated infra, SOC-2 support, named account manager

## Key Architectural Patterns

- **Auth:** JWT bearer tokens via `Depends(get_current_user)`. Gateway uses separate `bn-` prefix API keys.
- **Multi-tenancy:** Every table has `org_id` FK with `ondelete="CASCADE"`. ALL queries filter by `user.org_id`.
- **Credentials:** Stored in Vault (`providers/{provider_id}`), encrypted DB column as fallback.
- **Database:** Async SQLAlchemy with `AsyncSession`. Use `selectinload()` for eager loading. `flush()` within transaction, `commit()` after.
- **Migrations:** Alembic, numbered format (`###_descriptive_name`). Always include `org_id` FK, UUID PKs, timestamps with `server_default=func.now()`.
- **CLI:** Typer + Rich. `ensure_authenticated()` before API calls. `APIError` for error handling.
- **Error handling:** `HTTPException` with appropriate status codes. 422 for validation (Pydantic).
- **Feature gates:** `feature_gate.require_feature()` for premium features.

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

## What's Planned

- SOC-2 Type II certification
- Smart routing (complexity-aware model selection)
- VPC Gateway Agent (enterprise self-hosted data plane)
- Additional provider integrations (Cohere, Mistral, custom endpoints)
- Advanced audit log export & SIEM integration
