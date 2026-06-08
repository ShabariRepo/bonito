# AGENTS.md — Harness context for AI coding assistants

If you are Codex, Claude Code, Cursor agents, or any other AI assistant walking into this repo, read this first. It is a short, dense map to working in Bonito without breaking things. The fuller spec is in `CLAUDE.md`.

## What this repo is

Bonito is an enterprise AI operations platform — a unified control plane for managing AI workloads across multiple cloud providers (AWS Bedrock, Azure OpenAI, GCP Vertex, OpenAI direct, Anthropic direct, Groq). It gives engineering and platform teams one layer to connect providers, enforce governance, track costs, route requests, and deploy agents.

Live: https://getbonito.com · API: https://api.getbonito.com

## Stack at a glance

| Layer | Tech |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind, shadcn/ui, Framer Motion (port 3001 local) |
| Backend | FastAPI, async SQLAlchemy (port 8001 local) |
| Database | PostgreSQL 18.2 + pgvector HNSW (port 5433 local) |
| Cache | Redis 7 (port 6380 local) |
| Secrets | HashiCorp Vault prod, SOPS + age dev (port 8200, dev token `bonito-dev-token`) |
| AI routing | LiteLLM Router inside the gateway |
| CLI | Python (Typer + Rich), published as `bonito-cli` |
| MCP server | `bonito-mcp` — 18 tools for Claude Desktop |

## Where things live

```
bonito/
├── frontend/              Next.js 14 app
│   └── src/
│       ├── app/           App Router pages
│       └── components/    UI components
├── backend/               FastAPI app
│   ├── app/
│   │   ├── api/routes/    Route handlers
│   │   ├── core/          Config, DB, Vault
│   │   ├── models/        SQLAlchemy models
│   │   ├── schemas/       Pydantic schemas
│   │   └── services/      Business logic
│   └── alembic/           Numbered migrations: 001_, 002_...
├── cli/                   bonito-cli (Typer)
├── mcp-server/            MCP server package (18 tools)
├── vault/                 Vault init scripts
├── secrets/               SOPS-encrypted secrets
└── docs/                  Architecture, pricing, features
```

## Non-negotiable patterns

1. **Multi-tenancy.** Every table has `org_id` FK with `ondelete="CASCADE"`. **Every query filters by `user.org_id`.** No exceptions. The model never sets `org_id` from a request param; the auth dependency injects it server-side.
2. **Async SQLAlchemy.** Use `AsyncSession`. `selectinload()` for eager loading. `flush()` inside a transaction, `commit()` after.
3. **Auth.** JWT bearer via `Depends(get_current_user)`. PATs (`bp-`) and project tokens (`bj-`) also resolved there. Gateway uses `bn-` keys via a separate path. Never trust user identity from request body.
4. **Migrations.** Alembic, numbered `###_descriptive_name`. Always include `org_id` FK, UUID PKs, `created_at`/`updated_at` with `server_default=func.now()`. If multiple migrations branch from the same head, write a merge migration immediately.
5. **Strict schemas.** Agent / connection / group / schedule / execute schemas use `extra = "forbid"`. Unknown fields return 422, not silent drop. Match this when adding new schemas.
6. **Credentials.** Never log them, never return them in API responses, never write them to commits. Vault for prod, encrypted DB column as fallback. The fallback auto-migrates plain JSON → AES-256-GCM on read.
7. **Error handling.** `HTTPException` with appropriate status. 422 for validation, 402 for quota, 403 for tier gating, 404 for not-found-or-not-yours.
8. **Feature gates.** Premium features go behind `feature_gate.require_feature(...)`. Don't sneak features past gates because they're "small."

Full pattern reference: `ARCHITECTURAL_PATTERNS.md` (7 core patterns).

## Working in Origami specifically

If you are touching `backend/app/services/origami/`:
- 16 tools registered in `tools/__init__.py`. Read tools are `is_write = False`, write tools are `is_write = True` and get plan-card-gated automatically.
- Server-side `org_id` injection is enforced by `sanitize_params()` — never trust `org_id` from model output.
- Token aliases live in `_resolve_tool_name()` in `orchestrator.py`. Add to `TOOL_NAME_ALIASES` when the LLM emits a friendly synonym for a registered tool.
- Resources are addressable by UUID or by display name (`kb_name`, `agent_name`, `project_name`). If both are passed and they disagree, refuse the call — don't silently pick.

## Common Bonito gotchas

- **Bedrock + tool calling.** Requires `litellm.modify_params = True` (set in `gateway.py`). Without it, multi-turn tool flows blow up with `UnsupportedParamsError` on iteration 2+.
- **pgvector codec.** Registered on `checkout` event, not `connect`. `connect` can fire outside the async greenlet during pool pre-ping and cause intermittent 500s during agent execution.
- **KB embedding dimensions.** Default is 1024 (Bedrock Titan V2). `EmbeddingGenerator` clamps to model max — GCP text-embedding-005 maxes at 768.
- **Alembic multi-head.** If two branches both descend from the same head, `alembic upgrade head` errors with "Multiple head revisions." Write a merge migration immediately.
- **External docs folder.** Customer / deal / partner docs live at `~/Desktop/Projects/Bonito AI/documentation/` (per-customer subfolders). Move them there, don't keep them in this repo.

## Verification before every PR

```bash
# Backend lint
python3 -m compileall -q backend/app

# Backend tests (when they exist)
cd backend && pytest

# Frontend build
cd frontend && npm run build

# Local up
docker compose up --build -d
open http://localhost:3001
```

If the change touches migrations:

```bash
docker compose exec backend env PYTHONPATH=/app alembic upgrade head
```

## When to read CLAUDE.md vs. this file

- **AGENTS.md** (you're reading it) — short context to start working safely. Stack, patterns, gotchas.
- **CLAUDE.md** — the full spec. Recent changes log (months of history), pricing tiers, features list, full architectural detail. Read this when a question can't be answered from AGENTS.md or the code itself.

If CLAUDE.md and AGENTS.md disagree, CLAUDE.md wins.

## Style rules

- No em-dashes in user-facing copy. Use other punctuation.
- Commit messages: short, factual, what + why. Not how.
- Don't refactor unrelated code in the same PR as a feature.
- Don't introduce a new framework. Existing patterns are deliberate.
- Don't add error handling, fallbacks, or validation for scenarios that can't happen. Trust framework guarantees inside the system; validate at boundaries (user input, external APIs).

## When in doubt

Ask Shabari at shabari@bonito.ai before:
- Touching production data
- Adding new third-party services that need API keys
- Changing pricing or tier definitions
- Renaming anything customer-visible
- Force-pushing to main

Don't ask before: internal code structure, naming, helpers, refactoring scope inside a single PR's intended surface.
