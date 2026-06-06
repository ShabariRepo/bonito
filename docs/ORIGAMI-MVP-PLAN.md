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
   ▼  Cmd+J (panel) or navigate to /origami (full workspace)
Origami chat panel + workspace (Next.js)
   │
   ▼  POST /api/origami/turn (SSE response)
   │  { message, conversation_id }
FastAPI route handler
   │
   ▼  authenticated via og- token (org_id frozen)
Origami orchestrator (Bonobot in system-org, hand-rolled on Bonito gateway)
   │
   ├─ Model router: Sonnet 4.6 default, Opus 4.7 escalation for complex builds
   ├─ Tools: 13 wrappers around internal API (org_id injected server-side, never trusted from model)
   ├─ KB: bonito-knowledge (pgvector HNSW)
   ├─ Memory: Persistent Agent Memory + Memwright (per-user namespace)
   ├─ Tier context: injected per-turn from user.subscription_tier (live, no cache)
   ├─ LLM calls: routed through Bonito gateway (api.getbonito.com), not direct to provider
   └─ Prompt caching: Anthropic's cache-control on static portions (system prompt + tool schemas + tier matrix)
   │
   ▼  emits SSE event stream
{ message_token, plan_ready, tool_started, tool_progress,
  tool_completed, execution_done, tier_check, upgrade_offered, error }
   │
   ▼  Frontend reducer → workspace state updates
Chat populates, plan card appears, resources grid fills,
activity log streams. On Deploy → execution events flow.
   │
   ▼  audit
Every tool call → origami_audit_log (immutable, GCS-sunk)
```

**Key design choices:**

1. **Hand-rolled orchestrator, not `claude-agent-sdk`.** Spike (2026-06-06) measured 18.9× token overhead with the SDK plus inability to route through Bonito gateway. See `ORIGAMI-ADVERSARIAL-REVIEW.md` and `spikes/origami-sdk/notes.md`. Hand-rolled preserves margin, multi-provider freedom, and the gateway-dogfood story.

2. **Origami IS a Bonobot** running on Bonito's gateway. Proves the platform on every interaction. Improvements to the Bonobot framework automatically improve Origami.

3. **SSE event vocabulary is Bonito-native.** Not bound to any SDK's schema. We can extend with Bonito-specific events (`tier_check`, `upgrade_offered`, future `voice_started`, `compliance_check`) without breaking compatibility.

4. **Prompt caching** on static portions (system prompt, tool schemas, tier matrix) — first turn pays full input cost, subsequent turns within cache TTL pay ~10% on cached portions. Makes per-turn cost flatten quickly.

---

## UX surfaces

1. **Dedicated route** `/origami` — full-screen split-pane workspace (primary surface, see "Workspace UX" below). For onboarding and any substantive build work.
2. **Embedded panel** — collapsible right-side panel available from anywhere in the app. `Cmd+J` toggles. Quick chat with no workspace pane; clicking "show workspace" promotes the conversation to the full `/origami` route.
3. **Onboarding redirect** — new orgs land on `/origami` first, not the dashboard. Opening line varies by setup state (see state machine below).

---

## Workspace UX (Replit-style interactive build view)

**The defining UX choice:** Origami is not a chatbot. It's an interactive workspace where you watch Origami build. Chat on the left, live workspace on the right. Replit Agent is the visual reference; Origami is the same shape but simpler — fewer panels, no file editor, focused on Bonito resources.

### Layout

```
┌─────────────────────────────┬─────────────────────────────┐
│  Chat panel                 │  Workspace pane             │
│  (width: 40%)               │  (width: 60%)               │
│                             │                             │
│  You:                       │  📦 Resources building      │
│  > Build me a support       │  ┌───────────────────────┐  │
│    agent for shopify        │  │ 🟡 support-bot        │  │
│                             │  │   Sonnet 4.6          │  │
│  Origami:                   │  │   creating...         │  │
│  Got it — clarify:          │  └───────────────────────┘  │
│  KB from your docs?         │  ┌───────────────────────┐  │
│                             │  │ 🟡 support-help-kb    │  │
│  You: yes                   │  │   2/3 docs uploaded   │  │
│                             │  │   ████████████░░ 67%  │  │
│  ─── Plan card ───          │  └───────────────────────┘  │
│  ✓ Create KB                │  ┌───────────────────────┐  │
│  ✓ Create agent             │  │ ✅ shopify-project    │  │
│  ✓ Link KB to agent         │  │   created             │  │
│  ⚠ uses 1/2 KBs on Builder  │  └───────────────────────┘  │
│  [Deploy] [Edit] [Cancel]   │                             │
│                             │  ━━━━━━━━━━━━━━━━━━━━━━━━  │
│                             │                             │
│                             │  📋 Activity log            │
│                             │  ▸ create_project (180ms)   │
│                             │  ▸ create_kb (240ms)        │
│                             │  ▸ upload_to_kb [2/3]       │
│                             │     chunking doc 2 ⋯        │
│                             │  ⋯                           │
└─────────────────────────────┴─────────────────────────────┘
```

### Components

| Component | Lives in | Responsibility |
|---|---|---|
| **Chat panel** | left pane | User messages, Origami responses, plan cards, upgrade-in-place CTAs. Standard chat affordances. |
| **Resources grid** | top-right | Each agent / KB / project Origami is creating gets a card. State icon (🟡 creating, ✅ done, ❌ error). Click to open the real resource page. Tier impact shown when relevant. |
| **Activity log** | bottom-right | Every tool call appears as a line. Collapsed by default for non-technical users, expandable for power users. Shows tool name, duration, status, parameters on expand. |
| **Plan card** | inline in chat | Structured plan with Deploy / Edit / Cancel. Renders the tier-impact line. On Deploy, transitions to "executing" state and workspace fills in. |
| **Progress header** | top of workspace | "Step 2 of 4: uploading documents" during execution. Fades on completion. |
| **Result preview** | inline in chat after execution | Summary card with links to the resources just created. "Your support-bot is live → [Open agent] [Get gateway key] [Test in playground]" |

### Workspace state model

```typescript
type OrigamiSessionState = {
  status: 'idle' | 'planning' | 'awaiting_confirmation' | 'executing' | 'done' | 'error';
  conversation: ChatMessage[];
  plan: PlanCard | null;
  resources: Resource[];           // agents, KBs, projects being created
  activity: ToolCallLog[];         // every tool call event
  currentStep: number | null;
  totalSteps: number | null;
  tierImpact: TierImpact | null;
  result: ResultPreview | null;
};

type Resource = {
  id: string;                      // local UUID until real ID assigned
  type: 'agent' | 'kb' | 'project' | 'gateway_key';
  name: string;
  state: 'queued' | 'creating' | 'done' | 'error';
  progress?: { current: number; total: number };  // for multi-step (KB uploads)
  realId?: string;                 // assigned after creation
  meta: Record<string, any>;
};

type ToolCallLog = {
  id: string;
  toolName: string;
  startedAt: number;
  completedAt?: number;
  status: 'running' | 'success' | 'error';
  paramsRedacted: Record<string, any>;
  result?: any;
};
```

### SSE event schema (server → client)

Origami's `/api/origami/turn` endpoint streams Server-Sent Events. Frontend reducer maps events to state updates.

| Event | Payload | Triggers |
|---|---|---|
| `message_token` | `{ token: string }` | Append to current assistant message |
| `message_complete` | `{ message_id, full_text }` | Finalize message |
| `plan_ready` | `{ plan_card: PlanCard }` | Show plan card in chat, populate `resources[]` as "queued" |
| `awaiting_confirmation` | `{ plan_card_id }` | Lock UI, show Deploy button |
| `execution_started` | `{ total_steps }` | Set progress header |
| `tool_started` | `{ tool_call_id, tool_name, params_redacted, step }` | Add to activity log, mark resource as "creating" |
| `tool_progress` | `{ tool_call_id, progress: { current, total } }` | Update resource progress bar (e.g. KB upload 2/3) |
| `tool_completed` | `{ tool_call_id, duration_ms, result }` | Mark tool success, mark resource as "done", store real ID |
| `tool_failed` | `{ tool_call_id, error }` | Mark tool error, mark resource as "error" |
| `tier_check` | `{ feature, allowed, message }` | Surface in plan card if blocking |
| `upgrade_offered` | `{ from_tier, to_tier, price }` | Show upgrade CTA on plan card |
| `execution_done` | `{ result_preview }` | Show result preview card, clear progress header |
| `error` | `{ code, message, recovery_options }` | Show error state with recovery actions |

This event vocabulary is Bonito-native. We can extend it for future Bonito features (e.g. `voice_started`, `compliance_check`, `routing_decision`) without breaking the schema — no SDK constraints in the way.

### Why this is *better* than chatbot-only

1. **Non-technical buyers see progress visually.** Replit's whole growth lever is "look at what the agent is doing." Same here.
2. **Power users get inspection.** Activity log is collapsible — closed for non-tech, open for devs who want to see every tool call.
3. **The plan card has visual feedback** — as Origami stages the build, the resources grid populates with queued cards. The user sees the plan land before they click Deploy.
4. **Errors are contextual.** Resource turns red, activity log shows the failing tool call, recovery options appear inline. No "something went wrong" generic toast.
5. **Demo gravity.** Workshop demo becomes "watch Origami build this support agent in 90 seconds" with visible motion. Strictly stronger than chat-only.

### Build implications for the spec

- Phase 1 orchestrator must emit the event schema above, not just final responses
- Phase 2 plan card UX expands to the full workspace layout
- Phase 3 chat surfaces split into two: the embedded panel (chat-only, simpler) and the `/origami` route (full split-pane workspace)
- Frontend gets a `useOrigamiSession()` hook with the reducer over SSE events
- Activity log component reused across resource cards (different filters)

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

### Phase 1 — Orchestrator (Week 2-4)

- New FastAPI routes: `POST /api/origami/turn` (SSE response), `POST /api/origami/execute_plan` (SSE response)
- **Hand-rolled orchestrator** on raw chat completions through Bonito gateway (not `claude-agent-sdk`)
- System-org provisioned with Origami as a Bonobot
- **13 tool wrappers** around existing internal API (12 build/read + `delegate_provider_connection`)
- **`og-` token type** added to `access_tokens` table; auto-mint on first Origami session-open; revocable from Settings
- **`get_origami_context` auth dependency** — enforces `og-` prefix + strict `(user_id, org_id)` binding at the perimeter; `org_id` read from token, NEVER from request or model output
- **Tool schema hardening** — `org_id` stripped from every tool's JSON schema; injected server-side from `OrigamiContext.org_id` post-parse, pre-execute; pytest asserts mismatched-token-vs-session returns 403
- Tier injection per-turn (read `user.subscription_tier` live, project only `{tier, hit_limits, gated_features}` summary — not full `TIER_CONFIG` dict)
- Persistent Agent Memory + Memwright namespace per user
- **SSE event emission** — `message_token`, `plan_ready`, `tool_started`, `tool_progress`, `tool_completed`, `tier_check`, `upgrade_offered`, `execution_done`, `error` (see Workspace UX section for full schema)
- **Prompt caching** via Anthropic's `cache_control` on static portions (system prompt, tool schemas, tier summary)
- **Setup state machine** — `NO_PROVIDERS` / `PROVIDERS_NO_MODELS` / `READY_NO_AGENTS` / `READY_HAS_AGENTS` / (new) `PROVIDERS_PARTIALLY_BROKEN` branches; opening copy adapts to state
- **Migration 046: `origami_audit_log` table** (was 045 — 045 was already taken by `add_user_id_isolation`). Either RLS via dedicated `origami_writer` Postgres role with `INSERT`-only grant, OR drop "DB-enforced append-only" claim and document app-enforced. Decide before migration writes.
- Audit-log write helper invoked from every tool call with `og_token_id` FK
- Cred redaction allowlist (per-param schema flag), NOT regex
- GCS audit sink writes async via Redis stream — never block tool execute on GCS

### Phase 2 — Plan card UX (Week 3-4)

- Structured response schema (`message`, `plan_card`)
- Plan card React component (Deploy / Edit / Cancel)
- **Upgrade-in-place flow** — Stripe Checkout inline modal triggered from gated plan card; on `payment_succeeded` webhook → tier flip → auto-execute deferred plan
- "Ship without [feature]" silent-degrade branch
- Execute + report-back
- Error states (partial failure mid-deploy with rollback)

### Phase 3 — Chat surfaces + workspace UX (Week 5-7)

**Two surfaces, shared session state:**

- **`/origami` full-screen route** (primary) — split-pane workspace:
  - Chat panel (left, 40%)
  - Resources grid (top-right)
  - Activity log (bottom-right, collapsible)
  - Progress header during execution
  - Result preview card on completion
- **Embedded panel** (secondary) — `Cmd+J` toggles. Chat-only, no workspace pane. "Show workspace" button promotes the conversation to `/origami`.

**Frontend pieces:**

- `useOrigamiSession()` hook — reducer over SSE event stream, produces `OrigamiSessionState`
- `<ResourceCard>` component — animated state transitions (queued → creating → done / error)
- `<ActivityLog>` component — collapsible, expandable per-row
- `<PlanCard>` component — Deploy / Edit / Cancel, plus upgrade-in-place CTA when tier-gated
- `<ProgressHeader>` — step counter + animated progress bar during execution
- `<ResultPreview>` — summary card with links to created resources, gateway key reveal, "test in playground" CTA
- Conversation history sidebar (last 30 days, click to reload session)

**Onboarding routing:**

- New orgs redirect to `/origami` on first login (full-screen)
- Setup state machine drives opening copy and CTA buttons
- Provider connection modal (delegated tool) opens in a focused iframe

### Phase 4 — Polish + ship (Week 6)

- Tier-gated upgrade prompts (link to `/pricing`)
- Telemetry (which tools called most, where users get stuck)
- Public launch via Product Hunt + Twitter + LinkedIn
- Demo video for sales

**Total: ~9-10 weeks to ship MVP** (recalibrated 2026-06-06 — old 6-week target was optimistic per adversarial review). Phase 1 expanded from 2 weeks → 3 weeks (event schema + state machine + audit migration), Phase 3 expanded from 2 weeks → 3 weeks (workspace UX is meatier than chat-only).

---

## Decisions (locked 2026-06-06)

0. **Hand-roll the orchestrator on Bonito gateway, do NOT use `claude-agent-sdk`.** Spike measured 18.9× token overhead and the SDK is hardwired to Anthropic's API format — pointing it at `api.getbonito.com` 404s, killing the dogfood story. Hand-rolled approach preserves margin (~85% gross), multi-provider freedom (failover pitch intact), and gateway dogfood. Saved estimated engineering: 2 days (the adversarial reviewer estimated 3 weeks of savings — recalibrated by measurement). See `spikes/origami-sdk/notes.md` for full numbers.

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
