# Origami — MVP Plan

**Date:** 2026-06-06
**Status:** Scope approved, build pending
**Owner:** Shabari + Claude
**Branch:** `origami-mvp`

---

## TL;DR

Origami is Bonito's in-app conversational interface. Think "Claude Code for Bonito" — a chat that knows the entire platform, the user's org context, and their tier, and can plan + deploy real infrastructure through structured plan cards with a Deploy button.

It runs **on Bonito itself** (it's a Bonobot — eats its own dog food). Every demo becomes a live proof of the platform.

Validated by Danny Pantuso (Mucker) on 2026-06-06 as the SMB wedge.

---

## Why now

1. **SMB wedge.** Builder + Growth tiers don't make sense without a self-serve onboarding motion. Origami IS that motion — non-technical buyer goes "Hey" → working agent in 5 minutes. No YAML, no CLI, no dev required.

2. **Demo gravity.** Current demo is "walk through 22 tabs." Origami is "watch me deploy a support agent live in this chat." 10x stickier and easier to repeat at scale.

3. **Moat.** Chat-to-live-infra requires owning the whole control plane. Helicone, Portkey, Langfuse can't ship Origami without rebuilding Bonito first.

4. **Power-user accelerator.** Origami is faster than the CLI for one-off tasks. Collapses 6 commands into one sentence — even devs prefer it for quick work.

---

## What it is (and isn't)

**Is:**
- A Bonobot living in the Bonito platform
- Platform-aware (every feature, tier limit, cookbook pattern)
- Org-context aware (current state, prior builds, usage)
- A planner that proposes before doing
- Tier-gated and upgrade-aware
- Available to every tier (it's a sales surface first)

**Is NOT:**
- A general-purpose code assistant
- A replacement for the canvas builder for complex multi-agent topologies (Phase 2)
- A voice assistant (Phase 2)
- An admin-mode debugger (Phase 2)

---

## Knowledge sources

| Source | Method | Update cadence |
|---|---|---|
| Bonito product spec | KB ingest of `CLAUDE.md`, `ARCHITECTURAL_PATTERNS.md`, `BONOBOT-ARCHITECTURE.md` | Weekly auto-sync |
| Public docs (`docs/`) | KB ingest | Weekly |
| OpenAPI spec | Auto-extracted from FastAPI | Daily |
| CLI reference | Extracted from `bonito --help` walks | On CLI release |
| Use case cookbook | Curated patterns, de-named from real customers | Quarterly |
| Tier matrix | Pulled live from `feature_gate.py` `TIER_CONFIG` | Live (no cache) |
| User org state | Live via internal API (providers, agents, KBs, projects, usage) | Per-turn |
| User build history | Persistent Agent Memory (pgvector) | Continuous |

The knowledge KB is internal-only (`bonito-knowledge`), not visible to customers. Origami queries it like any other RAG-enabled agent.

---

## Tool surface (MVP)

12 tools wired as function-calls. All execute under the user's auth context — Origami acts AS the user, never above them.

**Read-only (no confirmation needed):**

1. `list_org_state` — current providers, agents, KBs, projects, tier, usage
2. `list_available_models` — given connected providers
3. `view_logs` — recent gateway / agent logs (filtered + summarized)
4. `view_usage` — request count, cost, tier headroom
5. `check_tier_access` — what's allowed at current tier + what's gated

**Build / write (requires user-confirmed plan card):**

6. `create_agent` — name, system_prompt, model_id, tools, KB links
7. `update_agent` — same fields
8. `create_kb` — name, dimensions, compression settings
9. `upload_to_kb` — accepts files via signed upload URL
10. `create_project` — for multi-tenant separation
11. `mint_gateway_key` — `bn-` key for the user's app
12. `link_kb_to_agent` — attach KB as agent tool

**Setup / delegated (browser-side modal handoff):**

13. `delegate_provider_connection` — Origami opens the existing connection modal in-place mid-conversation. User completes credential entry in the secure modal (Origami never sees the creds). On modal close, Origami reads the new provider state and resumes the narrative thread.

**Excluded from MVP tool surface (Phase 2):**

- `set_routing_policy` — visual builder lives in UI
- `configure_autoscaler` — Enterprise feature, low-frequency
- `set_approval_queue` — Enterprise feature
- `schedule_agent` — cron complexity, fine in Phase 2
- `delete_*` — never via chat in MVP, always UI-confirmed

---

## The plan card

Every write action produces a structured plan card before execution.

The card shows:

- **Intent** in plain language
- **Changes** — every API call about to happen
- **Tier impact** — "uses 1 of 2 agents in your Builder limit"
- **Cost projection** if relevant
- **Buttons:** `[Deploy]` `[Edit]` `[Cancel]`

On `Deploy`, Origami runs the tool sequence and reports back in chat. On `Edit`, the user types follow-up and Origami regenerates the card.

Plan cards make Origami safe. The user never wakes up to surprise infrastructure.

Structured response schema:

```json
{
  "message": "Here's the build I'd suggest…",
  "plan_card": {
    "intent": "Support agent backed by your help docs KB",
    "changes": [
      {"action": "create_kb", "params": {"name": "support-help"}},
      {"action": "create_agent", "params": {"name": "support-bot", "model_id": "claude-sonnet-4-6"}},
      {"action": "link_kb_to_agent", "params": {...}}
    ],
    "tier_impact": "Uses 1/2 agents and 1/2 KBs on your Builder plan",
    "estimated_cost_per_month": "~$3 in token spend"
  }
}
```

---

## Tier gating

Origami pulls `feature_gate.py` live every turn. Three modes:

| Mode | Behavior |
|---|---|
| **Allowed** | Silent — just does it. |
| **Capped at tier** | "You're 4/5 agents on Builder. This will use #5. Confirm or upgrade for headroom." |
| **Gated above tier** | "Autoscaling is Enterprise-only. Three options: ship without it now [recommended], upgrade [link], or skip this build." |

Origami **never silently degrades**. Always explicit about what tier blocks and why.

---

## Architecture

```
User (browser)
   │
   ▼  Cmd+K or panel toggle
Origami chat panel (Next.js, /app/origami)
   │
   ▼  POST /api/origami/turn  { message, conversation_id }
FastAPI route handler
   │
   ▼  delegate to system-org Bonobot
Origami orchestrator (Bonobot in system-org)
   │
   ├─ Model router: Haiku for Q&A, Sonnet for planning
   ├─ Tools: 12 wrappers around internal API (run as user)
   ├─ KB: bonito-knowledge (pgvector HNSW)
   ├─ Memory: Persistent Agent Memory (per-user namespace)
   └─ Tier context: injected per-turn from user.subscription_tier
   │
   ▼
Structured response { message, plan_card? }
   │
   ▼  User clicks Deploy
Orchestrator executes tool sequence → reports in chat
```

**Key design choice:** Origami IS a Bonobot. Same agent runtime, same tool framework, same memory. This proves the platform on every interaction AND means improvements to the Bonobot framework automatically improve Origami.

---

## UX surfaces

1. **Right-side panel** (always available) — `Cmd+K` toggles. Persists across tabs.
2. **Dedicated route** `/origami` — full-screen mode for onboarding.
3. **Onboarding redirect** — new orgs land on Origami first, not the dashboard. Opening line varies by setup state (see state machine below).

---

## Token model

Origami uses its own access token prefix `og-`. Sits alongside `bn-` (gateway), `bp-` (PAT), `bj-` (project) in the existing `access_tokens` table.

**Properties:**

- **Prefix:** `og-`
- **Scope:** exactly one `(user_id, org_id)` pair, immutable on the token
- **Cannot cross orgs.** Even if the user belongs to multiple orgs, each org gets its own `og-` token. No multi-org token, ever.
- **Permissions:** inherits the user's role within that org (admin gets admin tools, member gets member tools). Tier-gating applied on top.
- **Auto-minted** on first Origami session-open. User never sees the token unless they explicitly request it (Settings → Origami token).
- **Revocable** from Settings — kills that user's Origami access in that org, full stop.
- **TTL:** 90 days, auto-rotates on each new session if expired.

**Why a dedicated prefix (vs reusing `bp-`):**

1. **Hard org-scope at the auth layer.** The auth dependency for `/api/origami/*` checks token prefix is `og-` AND `token.org_id == request.org_id`. Multi-tenancy guarantee at the perimeter, not just in app logic.
2. **Clean revocation.** Kill one token, kill that Origami session permanently. Doesn't affect the user's other access.
3. **Audit isolation.** Every audit log row references the exact `og-` token used. If someone abuses Origami, we have a single revocable identifier to kill.
4. **Phase 3 enablement.** White-label Origami (Memory Creative, Peller embedding their own branded Origami for their end-users) needs per-end-user tokens. The `og-` model maps cleanly: each end-user gets their own `og-` token bound to a single org.
5. **CLI / programmatic access** — `bonito origami chat "build me a support agent"` becomes possible Phase 2 using the user's `og-` token.

**Auth dependency** (FastAPI):

```python
async def get_origami_context(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> OrigamiContext:
    if not authorization.startswith("Bearer og-"):
        raise HTTPException(401, "Origami endpoints require og- token")
    token = authorization.removeprefix("Bearer ")
    record = await db.scalar(
        select(AccessToken).where(
            AccessToken.token_hash == hash_token(token),
            AccessToken.prefix == "og-",
            AccessToken.revoked_at.is_(None),
            AccessToken.expires_at > func.now(),
        )
    )
    if not record:
        raise HTTPException(401, "Invalid or expired og- token")
    return OrigamiContext(
        user_id=record.user_id,
        org_id=record.org_id,    # <-- frozen at token creation, untouchable
        role=record.metadata["role"],
        token_id=record.id,
    )
```

Note `org_id` is read **from the token**, never from the request. The user cannot pass an `org_id` query param to switch orgs — the token determines it.

---

## Onboarding state machine

Origami can't build anything without providers connected, so first-launch behavior is **gated on platform readiness**. Origami checks org state on every session-open and routes to the right behavior:

| State | Trigger | Origami's opening behavior |
|---|---|---|
| `NO_PROVIDERS` | `len(org.providers) == 0` | "Welcome to Bonito. To build anything you'll need at least one AI provider connected. I can walk you through it — which cloud are you on?" + provider picker buttons (Bedrock / Azure / Vertex / OpenAI / Anthropic / Groq). Selecting one fires `delegate_provider_connection`. |
| `PROVIDERS_NO_MODELS` | Providers connected but `available_models == []` | "Your provider is connected but no models synced yet — give me 30 seconds." Polls `model_sync` then transitions. |
| `READY_NO_AGENTS` | Models available, no agents yet | "You're set up. What do you want to build? A support bot? A KB-backed assistant? Tell me the use case." |
| `READY_HAS_AGENTS` | Returning user | "Welcome back. You've got `{n}` agents running. Want to build something new, tweak an existing one, or look at logs?" |

State transitions happen mid-conversation. Each tool call refreshes the snapshot of `org_state` so Origami stays in sync without restarting.

This makes Origami the **narrative thread through the whole onboarding flow**, not a separate wizard. Provider connection, model sync, first agent build — one continuous conversation.

---

## Upgrade-in-place UX

When a build needs a feature gated above the user's tier, Origami **does not bounce the user to `/pricing`**. Instead, the plan card itself becomes the upgrade surface.

**Pattern:**

```
[Plan card]
  Intent: "Customer support agent with autoscaling"

  Changes:
    ✓ Create KB "support-docs"  (within Builder tier)
    ✓ Create agent "support-bot"  (within Builder tier)
    ⚠ Enable autoscaling          (requires Enterprise — currently on Builder)

  Tier impact: This build needs Enterprise.

  [Upgrade to Enterprise and deploy →]   ← single CTA
  [Ship without autoscaling on Builder]
  [Cancel]
```

Clicking the upgrade CTA:

1. Opens an in-chat Stripe Checkout modal (`@stripe/stripe-js` inline embed, no redirect)
2. On `payment_succeeded`, the org's tier flips
3. Origami auto-executes the deferred plan
4. Reports back: "Upgraded to Enterprise and your build is live. Logs are at `/agents/support-bot`."

The motion is: **one click → upgrade + deploy in a single user gesture.** No context switch, no "go to pricing then come back," no abandoned cart.

For users who say "ship without it on Builder," Origami silently degrades the plan, removes the gated lines, and re-renders the card.

---

## Audit trail (hardened)

New table `origami_audit_log`, immutable + append-only, one row per Origami action.

```sql
CREATE TABLE origami_audit_log (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id          UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  og_token_id     UUID NOT NULL REFERENCES access_tokens(id),  -- exact og- token used
  session_id      UUID NOT NULL,
  plan_card_id    UUID,                          -- nullable for read-only turns
  intent_summary  TEXT NOT NULL,                 -- parsed user intent
  tool_name       TEXT NOT NULL,                 -- e.g. 'create_agent'
  tool_params     JSONB NOT NULL,                -- as-called params, redacted creds
  tier_at_time    TEXT NOT NULL,                 -- frozen at action time
  confirmation    TEXT NOT NULL,                 -- 'auto' (read-only) | 'user_clicked' | 'upgrade_then_auto'
  status          TEXT NOT NULL,                 -- 'success' | 'failed' | 'partial'
  error           TEXT,
  created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_origami_audit_org_time ON origami_audit_log(org_id, created_at DESC);
CREATE INDEX idx_origami_audit_user ON origami_audit_log(user_id, created_at DESC);
CREATE INDEX idx_origami_audit_token ON origami_audit_log(og_token_id);
```

**Hardening:**

- **No UPDATE/DELETE allowed** — row-level security policy denies non-INSERT verbs even for service accounts. Append-only.
- **Cred redaction** — `tool_params` strips anything matching credential patterns before insert.
- **GCS sink** — every row also writes async to `{org_id}/origami/{YYYY}/{MM}/{DD}/{HH}.ndjson` via the existing structured log sink. Same per-tier retention as other logs.
- **Admin-viewable** — `/admin/origami-audit` page lets platform admins inspect across orgs. Customer-facing `/audit` page shows their own org only.
- **Sentry context** — every Origami tool call adds breadcrumbs to Sentry for in-the-moment debugging when something fails.

This is the multi-tenancy guarantee: Origami runs in `system-org` but is *constitutionally* incapable of acting without a logged, attributed trace.

---

## Out of scope for MVP

- Voice (in/out)
- Multi-modal (image upload, screen share)
- Full canvas building via chat (multi-agent wheels)
- Provider connection via chat (needs browser-side credential modal)
- Cross-org admin mode
- Slack / Discord / Teams as Origami surfaces
- Live debugging ("why is this agent slow?")
- Origami-builds-Origami (deploy a customer-branded version)
- Code emission (frontend integration snippets)
- Schedule / cron management
- Routing policy authoring
- Delete actions of any kind

---

## Phase 2 (post-MVP)

- Provider connection via chat (browser callback for credential capture)
- Schedule + cron management
- Canvas building (multi-agent topologies via chat)
- Voice surface (existing Bonito voice infra)
- Live debugging mode
- Workshop mode for Chicago Tech Week (Danny / Mucker)
- Delete + destructive actions with double-confirmation

---

## Phase 3 (future)

- **Origami-builds-Origami** — brands deploy a custom-flavored Origami to their end-users (Memory Creative agency white-label, Peller direct-to-customer)
- Code emission (React/Python integration snippets)
- Slack / Discord / Teams as alternate Origami surfaces
- Multi-org admin mode for platform admins
- Origami acting on behalf of an agent (agent-to-Origami)

---

## Build phases

### Phase 0 — Knowledge prep (Week 1)

- Build `bonito-knowledge` KB ingestion pipeline (auto-syncs internal docs)
- Extract CLI reference programmatically from Typer command tree
- Wrap OpenAPI spec as queryable KB entries
- Curate first 10 use case patterns (support agent, Q&A bot, lead qualifier, etc.)

### Phase 1 — Orchestrator (Week 2-3)

- New FastAPI routes: `POST /api/origami/turn`, `POST /api/origami/execute_plan`
- System-org provisioned with Origami as a Bonobot
- **13 tool wrappers** around existing internal API (12 build/read + `delegate_provider_connection`)
- **`og-` token type** added to `access_tokens` table; auto-mint on first Origami session-open; revocable from Settings
- **`get_origami_context` auth dependency** — enforces `og-` prefix + strict `(user_id, org_id)` binding at the perimeter
- Tier injection per-turn (read `user.subscription_tier` live)
- Persistent Agent Memory namespace per user
- Streaming response support
- **Setup state machine** — `NO_PROVIDERS` / `PROVIDERS_NO_MODELS` / `READY_NO_AGENTS` / `READY_HAS_AGENTS` branches in the orchestrator
- **Migration 045: `origami_audit_log` table** with RLS policy (append-only), `og_token_id` FK
- Audit-log write helper invoked from every tool call

### Phase 2 — Plan card UX (Week 3-4)

- Structured response schema (`message`, `plan_card`)
- Plan card React component (Deploy / Edit / Cancel)
- **Upgrade-in-place flow** — Stripe Checkout inline modal triggered from gated plan card; on `payment_succeeded` webhook → tier flip → auto-execute deferred plan
- "Ship without [feature]" silent-degrade branch
- Execute + report-back
- Error states (partial failure mid-deploy with rollback)

### Phase 3 — Chat surface (Week 4-5)

- Right-side panel (persistent across tabs)
- `Cmd+K` open
- Full-screen `/origami` route
- Onboarding redirect for new orgs
- Conversation history sidebar

### Phase 4 — Polish + ship (Week 6)

- Tier-gated upgrade prompts (link to `/pricing`)
- Telemetry (which tools called most, where users get stuck)
- Public launch via Product Hunt + Twitter + LinkedIn
- Demo video for sales

**Total: ~6 weeks to ship MVP.**

---

## Decisions (locked 2026-06-06)

1. **Model routing** — Sonnet 4.6 default for chat + planning. Opus 4.7 for ambiguous / complex builds (router escalation based on intent complexity classifier).
2. **Dedicated `og-` token, strictly org-scoped.** Origami gets its own token prefix. Each token is bound to **exactly one** `(user_id, org_id)` pair, immutable at creation, and cannot be elevated or re-scoped. Even if Origami's orchestrator had a bug that tried to query across orgs, the token would 403 at the auth dependency. Tokens auto-mint on first Origami session-open. Every write action is still gated by a yes/no button click in the chat UI — the token unlocks Origami access, the button unlocks each individual action. See "Token model" section below.
3. **Step-by-step onboarding gated on platform readiness.** Origami can't deliver value if providers aren't connected, so first-launch enters a **setup state machine** (see below). New orgs land on Origami after signup, but Origami's opening behavior depends on what's already wired up.
4. **Both hero + dedicated `/origami` marketing page.** Hero gets the demo loop (typed prompt → plan card → deploy animation). Dedicated page gets the full pitch + use case gallery + signup CTA.
5. **Upgrade-in-place via the plan card itself** (see "Upgrade-in-place UX" below). No modal, no `/pricing` redirect — the upgrade is a button on the plan card, Stripe Checkout fires inline, on success the plan auto-deploys. Single motion, no context switch.
6. **Hardened audit trail confirmed.** New `origami_audit_log` table, immutable + append-only, with per-action rows logging intent, plan card, tier-at-time, tool calls, and confirmation. Also writes to GCS sink under `{org_id}/origami/...`. Admin-viewable.

---

## Success metrics (90 days post-launch)

- % new orgs that complete first agent deployment via Origami (target: **60%+**)
- % active orgs using Origami weekly (target: **40%**)
- Conversion Free → Builder for orgs that hit a tier gate in Origami (target: **15%**)
- Demo-to-deal cycle time reduction (qualitative — measure via sales notes)
- NPS for new-user onboarding (target: **>50**, up from current baseline)

---

## Risks / mitigations

| Risk | Mitigation |
|---|---|
| Hallucinated builds (Origami creates wrong thing) | Plan card pattern — every write is user-confirmed |
| Tier-gate logic drifts from `feature_gate.py` | Pull live every turn, no caching of tier rules |
| Origami knowledge stale (new feature added, KB not synced) | Weekly auto-sync + manual `bonito-knowledge` re-ingest on big releases |
| Cost (Sonnet calls add up at scale) | Haiku for Q&A, Sonnet only for planning. Cache common patterns. |
| Multi-tenancy leak (Origami sees wrong org's data) | Strict `org_id` injection per turn. Audit every tool call. Pen-test before launch. |
| Onboarding regression for technical users | A/B test the redirect. Power users keep CLI as primary. |

---

## Naming + brand notes

**Origami** — chosen 2026-06-06. Reads instantly, evokes simple-folds-to-complex-shapes (conversation → working build), no AI/GPT/Copilot cliché. Domain availability + trademark check pending.

Voice: friendly but not chirpy. Direct, brief, never AI-condescending. Same tone as Bonito itself — jovial opener, technical substance, no AI-speak.

Color/logo: TBD (probably paper-fold mark in Bonito blue).

---

## Cross-links

- Pricing strategy: `docs/PRICING-STRATEGY-2026-06.md`
- Bonobot architecture (Origami inherits): `docs/BONOBOT-ARCHITECTURE.md`
- Architectural patterns: `ARCHITECTURAL_PATTERNS.md`
- Mucker / Danny relationship: memory `project_mucker_danny.md`
