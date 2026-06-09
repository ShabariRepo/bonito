# Bonito — Progress Tracker

_Last updated: 2026-06-06 (end of session)_

## Most recent session — Origami Phase 1 skeleton

Save file for tomorrow-you. Branch: `origami-mvp`, 28 commits ahead of `main`.

### What landed tonight

A full Phase 1 Origami skeleton, smoke-tested end-to-end against real Bedrock through our own gateway.

**Code shipped:**

- **Phase 0 KB ingestion scaffold** — `backend/app/services/origami/ingestion/` — 6 modules, 24 tests, 444 IngestionRecords produced when run
- **`og-` token type** — `backend/app/services/origami/auth.py` — auto-mint, revoke, FastAPI dependency, org-scope locked at the perimeter
- **Hand-rolled orchestrator** — `backend/app/services/origami/orchestrator.py` — httpx → Bonito gateway, NO SDK. Streams `message_token` events token-by-token. Token-estimate fallback for Bedrock (LiteLLM doesn't echo usage on streaming).
- **5 read tools** — `list_org_state`, `view_usage`, `view_logs`, `list_available_models`, `check_tier_access`
- **Per-turn metering** — `origami_turn_log` table (migration 046), customer-org-attributed, tier-quota-enforced (Free 50/Builder 100/Growth 300/Pro 1000/Enterprise 5000, overage $0.12 / $0.10)
- **Per-action audit** — `origami_audit_log` (migration 046) with project_id (migration 047)
- **Admin endpoints** — `/api/admin/origami/usage-by-org`, `/recent-activity`, `/turns` (super-admin only, cross-tenant)
- **Frontend chat** — `/origami` page, SSE parser, typewriter cursor, collapsible activity log

**Decisions locked:**

- **SKIP `claude-agent-sdk`** — spike measured 18.9× token overhead + can't route through Bonito gateway (Anthropic format only). Dead, don't relitigate.
- **Rename Origami** — collision with YC-backed `origami.chat`. Shortlist: Kigumi / Kunai / Jutsu. Pick + collision-check before any external mention.
- **Pricing for Origami turns** — chat included every tier; quotas calibrated to ~3-5× realistic heavy use; overage $0.12/$0.10
- **Workspace UX = Replit-style split-pane** — locked in spec, builds in Phase 3 (chat left, resources grid + activity log right)
- **System-org pattern for gateway key** — single `bn-` key (cat.shabari in prod), customer attribution via OpenAI `user` field + X-Bonito headers, billing flows through `origami_turn_log` per customer

**Smoke test (proven on local DB):**

Returns real Claude Haiku 4.5 streaming response via `us.anthropic.claude-haiku-4-5-20251001-v1:0` (auto cross-region inference). Turn log row lands with `status=success`, real cost, real tokens.

Local env tweaks made tonight:
- `docker-compose.yml`: added `SECRET_KEY` + `ENCRYPTION_KEY` env vars to backend service (defaults match what's in Vault under `bonito/app`)
- AWS Bedrock creds from `~/Desktop/code/bonito-infra/aws/terraform.tfstate` written into Test Admin's org's AWS provider via `store_credentials()`

### What's open

**Phase 1 leftovers (task #23 still in_progress):**

- **`POST /api/origami/session/start` endpoint** — thin route that calls `get_or_create_origami_token(user)` and returns the `og-` token. Frontend can stash it on first `/origami` visit. ~15 min.
- **Memwright session memory** — wire across-turn context so Origami remembers what was said. Currently each turn is fresh.
- **Per-org `bn-` key resolution** — switch from env var to Vault path keyed on a system-org concept. Today's `ORIGAMI_GATEWAY_KEY=bn-...` env var works; production wants Vault-backed.

**Phase 2 (real next jump — task #26):**

- **Plan card UX + first write tool.** This is the moment Origami stops answering questions and starts building things. Structured response schema (`message`, `plan_card`), Deploy/Edit/Cancel buttons in React, then `create_kb` as the first write tool. Then `create_agent`. ~3-4 hours.

**Phase 3 (task #28):**

- **Split-pane workspace at `/origami`.** Resources grid + activity log + plan card inline + progress header + result preview. ~1 week of focused work.

**Smaller open items:**

- **Rename** — pick from Kigumi / Kunai / Jutsu, run collision check, search-and-replace across `backend/app/services/origami/`, `frontend/src/`, docs
- **Danny email** — was copied to clipboard 2026-06-06 with subject "Origami update". Probably gone from clipboard by now; redo from `project_mucker_danny.md` memory if you didn't send
- **Stripe metered overage** (task #34) — blocked on Shabari signing up for Stripe + getting account keys
- **Usages page UI** (task #33) — customer-facing version of `/api/admin/origami/usage-by-org`, scoped to their own org. Reads `get_origami_usage_summary()`.

### Files worth opening first tomorrow

- `docs/ORIGAMI-MVP-PLAN.md` — the canonical spec (workspace UX, decisions, build phases, token model, audit, upgrade-in-place)
- `docs/PRICING-STRATEGY-2026-06.md` — pricing matrix + Origami COGS analysis
- `backend/app/services/origami/README.md` — how to run + billing architecture
- `backend/app/services/origami/orchestrator.py` — streaming loop + tool dispatch + metering
- `frontend/src/components/origami/OrigamiChat.tsx` — SSE parser + reducer + typewriter cursor

### What you should NOT relitigate

These took real effort tonight; don't undo them:

- **SDK skip** — proven by measurement, not vibes. `spikes/origami-sdk/notes.md` has the math.
- **Origami uses Bonito gateway, not direct provider** — three iterations to get this right. Final state in `_call_gateway` + `_stream_gateway` (httpx only, no LLM library).
- **Customer-org metering via `origami_turn_log`, system-org gateway key for LLM cost** — this dual-path is intentional. Documented in `backend/app/services/origami/README.md` "Billing architecture".
- **`org_id` injected server-side from auth context, never from model output** — load-bearing for multi-tenancy.

---

## Recently Completed (prior sessions, kept for reference)

See `CHANGELOG.md` for full history.

- **2026-06-06:** Origami Phase 1 skeleton (this session)
- **2026-05-27:** Personal Access Tokens, project tokens, log retention tier gating, GCS log sink org-partitioning, KB linked-agents fix, queue drainer adaptive polling, UX onboarding improvements
- **2026-05-25:** KB delete fix (pgvector), vector dimension fix, alembic merge migration 042, greenlet_spawn fix, ingestion error handler fix
- **2026-05-23:** External orchestration / Breadcrumbs tracing, Agent Health dashboard, gateway duplicate-provider fix
