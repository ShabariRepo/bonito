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

**Excluded from MVP tool surface (Phase 2):**

- `connect_provider` — requires browser-side credential capture
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
3. **Onboarding redirect** — new orgs land on Origami first, not the dashboard. Opening line: "Hi, what are we building today?"

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
- 12 tool wrappers around existing internal API
- Tier injection per-turn (read `user.subscription_tier`)
- Persistent Agent Memory namespace per user
- Streaming response support

### Phase 2 — Plan card UX (Week 3-4)

- Structured response schema (`message`, `plan_card`)
- Plan card React component
- Deploy / Edit / Cancel flow
- Execute + report-back
- Error states (partial failure mid-deploy)

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

## Open questions

1. **Model for planning** — Sonnet 4.6 vs Opus 4.7? Sonnet recommended for cost + latency. Opus for ambiguous/complex builds only.
2. **Token type** — Should Origami have its own `og-` prefix tokens for programmatic access in Phase 2? Or reuse `bp-` (PAT).
3. **Onboarding aggressiveness** — Is auto-redirecting new orgs to Origami too aggressive for technical users? Probably A/B.
4. **Public page placement** — Hero section, dedicated `/origami` marketing page, or both?
5. **Upgrade-prompt UX** — Modal? Inline card? Embedded `/pricing` iframe in chat?
6. **System-org isolation** — Origami runs in `system-org` but acts under user auth. Need a hardened audit trail for "Origami did X on behalf of Y" to keep multi-tenancy clean.

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
