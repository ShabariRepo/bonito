# Bonito Studio — Build Plan

**Status:** Approved 2026-06-12. Build kickoff this week.
**Target:** Demo-ready Jul 17, 2026 (Chicago Tech Week opens Jul 20).
**Why:** Direct feedback from Danny Pantuso (Mucker Capital) — Bonito's post-auth experience is too crowded for first-time users. Origami builds from prompts but isn't intuitive. The fix: replace the post-auth landing with a chat-first surface that reads the org's state and proactively suggests next moves, like a good BDR.

Danny is open to showing Bonito at Tech Week and to his partners *if* this lands. That's the deadline.

---

## Decisions locked

| | |
|---|---|
| **Name** | "Bonito Studio". Bonito wordmark + "Studio" subtitle on home; "Bonito" elsewhere. Studio is a surface, not a brand. |
| **Route** | `/` becomes Studio (replaces current landing). Existing dashboard moves to `/dashboard`. One-time tooltip for returning users: "Your dashboard moved to /dashboard." |
| **Agent voice** | First person, warm, casual, friendly, professional. "I'll set that up for you" — not "Bonito will…". |
| **Opener model** | Hybrid: no intake form. Agent silently reads org state via `/api/studio/init`, then opens with something specific to that state. Zero friction, Claude-Code-like. |
| **Sidebar** | Default-collapsed. Expands to 7 grouped items (see [sidebar grouping](#sidebar-grouping)). No features cut — all 23 phases preserved, just grouped under domain headers. |
| **Tier gating** | Free on all tiers. It's the new front door, not a premium feature. Turn limits inherited from Origami pricing (Free 50 / Builder 100 / Growth 300 / Pro 1K / Enterprise 5K turns/mo). |
| **Token mechanism** | Reuse Origami's `og-` token internally. UX never mentions it. |
| **Backend reuse** | Wholesale reuse of Origami orchestrator, 13-tool registry, SSE event protocol, plan validator, parser preprocessing. Only net-new backend: `/api/studio/init` snapshot endpoint + new BDR system prompt. |

---

## Shape

Studio is a clean, full-bleed chat surface at `/`. On every login, before the first character is rendered, the backend pulls a snapshot of the org's state (providers connected, agents created, KBs, last 7 days gateway usage, billing) and uses it to seed a personalized opener. The opener is the BDR moment — the user sees an agent that already understands their context.

Execution model is unchanged from Origami: agent emits `tool_calls`, frontend renders plan cards, results stream back via SSE. What changes is the framing — talking *to Bonito*, not "using Origami to build."

---

## Sidebar grouping

23 features condensed into 7 top-level items. Nothing removed; everything grouped under the domain it serves.

| Top-level | Rolls up |
|---|---|
| Dashboard | (single page — current `/`'s metrics view) |
| **Agents** | Agent list, Bonobot canvas, Schedules, Approvals, Memory, Autoscaling, Overflow queue |
| **Knowledge** | KBs, VectorBoost config |
| **Gateway** | Routing policies, Models, Cost intelligence, Token efficiency, Request logs, Failover settings, Playground |
| **Integrations** | Providers, Org Secrets, MCP / Plugins |
| **Team** | Members, Roles, SSO, Audit log, Access requests |
| Settings | Plan & billing, API keys (PATs + project tokens), Profile, Notifications |

Sidebar is collapsed by default. Click/hover to expand. Studio keeps focus on the chat.

---

## Reuse vs build

### Reuse — do not modify unless broken
- `backend/app/services/origami/orchestrator.py` — execution loop, tool dispatch, retry logic
- 13-tool registry — `create_agent`, `create_kb`, `create_project`, `connect_provider`, `create_gateway_key`, `link_kb_to_agent`, etc.
- SSE event protocol (`text_delta`, `tool_call`, `tool_result`, `plan_revision`, `plan_warning`, `done`)
- Plan validator + dependency checker (`_validate_plan_dependencies`)
- Parser preprocessing for `${step_N.field}` template references
- `og-` token issuance + binding to `(user_id, org_id)`
- Cost/turn tracking, telemetry

### Build new
- `POST /api/studio/init` — returns org snapshot:
  - providers (count, types, healthy)
  - agents (count, recent activity, autoscale status)
  - knowledge bases (count, total docs)
  - gateway (last 7d requests, last 7d cost, top 3 models)
  - billing (tier, days since signup, card status, days until card capture if trial)
  - projects (count)
- `POST /api/studio/chat` — SSE stream, reuses orchestrator, injects snapshot as system context, swaps system prompt for BDR-flavored prompt
- New BDR system prompt — first-person, warm, professional, snapshot-aware opener, one clarifying question pattern, plan-card execution
- Frontend `/` route — full-bleed chat, collapsed sidebar shell, plan-card V2 styling
- Move existing `/` view → `/dashboard` (zero content change, routing only)
- Snapshot-driven opener templates (~6 org-state scenarios)
- First-login tooltip for returning users
- Plan card V2 — visual redesign, cleaner tool execution status, inline result previews, KB citations

### Cut for V1 (defer to V1.5+)
- Multi-thread chat history (V1 = single persistent thread per `(user_id, org_id)`)
- Stripe inline upgrade flow
- Mobile responsive (desktop demo only)
- Voice input
- Custom themes

---

## Phases

| Phase | Dates | Work |
|---|---|---|
| **0 — Foundation** | Jun 13–14 | Repro + fix PROD plan-card bug from Danny demo (gating — must land before Studio code). Confirm orchestrator can swap system prompt + take a snapshot context block. |
| **1 — Backend** | Jun 15–19 | `/api/studio/init` snapshot endpoint with `<500ms` budget. `/api/studio/chat` reusing orchestrator. New BDR system prompt + ~6 opener templates. Integration tests against 3 mock org states (new, mid-build, active). |
| **2 — Frontend shell** | Jun 22–26 | New `/` route, full-bleed chat layout, collapsed sidebar with 7-item grouped nav. Move existing dashboard view to `/dashboard`. Persistent thread per `(user, org)`, snapshot-aware first message rendered server-side. First-login migration tooltip. |
| **3 — Plan card V2 + polish** | Jun 29–Jul 3 | Visual redesign of plan cards. Tool execution status (planning → executing → done). Inline result previews. KB citations. Loading skeletons, error states, retry affordances. Copy pass on every UI string in BDR voice. |
| **4 — Demo prep** | Jul 6–10 | End-to-end test against 3 real orgs (new test org, Lisa-like mid-build org, active production org). Cross-browser (Safari + Chrome). 4-minute demo script. Loom backup recording in case live demo flakes. |
| **Buffer** | Jul 13–17 | Internal demos. Danny preview (target: week of Jul 13). Final polish. |
| **Demo** | Jul 17–20 | Ship final. Danny demo to Mucker partners + Tech Week. |

---

## BDR system prompt — key behaviors

1. **Open org-specific, never generic.** Snapshot drives turn 1. Patterns:
   - Empty org → invite first provider connect
   - 1 provider / 0 agents → invite first agent build
   - Active gateway → reference yesterday's usage, offer 2–3 next moves
   - Returning user with recent activity → reference last session implicitly ("last time we wired up Bedrock — want to keep going, or something new?")
   - Trial user near day-30 → gently mention card capture timing alongside their goal
   - Power user → skip pleasantries, surface 2–3 active workstreams as quick-jump chips
2. **One clarifying question when intent is vague.** "Set up RAG" → "Sure — what docs are you starting with? Internal wikis, customer support history, product specs?". Then plan.
3. **Plan-card execution when intent is clear.** Emit tool_calls and let the cards do the talking. Don't over-narrate.
4. **First-person, confident voice.** "I'll do X, Y, Z" — not "I think we could maybe do X." Casual but professional. Friendly without being chirpy.
5. **Visible reasoning between tool calls.** 1-line thinking notes like Claude Code does — "Spinning up the agent now…", "Linking that KB so the agent can search it…". User sees the agent working, not just a black box.
6. **Knows what it can and can't do.** If the user asks for something outside the 13-tool surface, says so clearly and offers the closest supported move.

---

## Risks

1. **PROD plan-card bug** — blocks everything. Day-0 task. Cards rendered fine in testing but disappeared during Danny's demo (~1:30–1:40 PM PT 2026-06-11). Likely culprits: different prompt re-hit text-mode pattern, SSE buffering on demo network, or live-load timeout in orchestrator. Repro before any Studio code lands.
2. **Snapshot endpoint perf** — must be <500ms for snappy open. Probably needs aggressive caching (Redis, 30s TTL keyed on `org_id`).
3. **Model pick for opener vs execution** — Origami runs Sonnet 4-6. Studio's first-turn impression matters most; test Opus 4-7 for opener (high quality, low latency tolerance acceptable for 1 turn) vs Sonnet for execution turns. Decide week 1.
4. **SSE buffering on demo network** — Danny's missing cards smells like this. Repro under network conditions before declaring Phase 0 done.
5. **Existing-user surprise** — current users will hit Studio at `/` instead of the dashboard. Tooltip + breadcrumb to `/dashboard` is the cushion. If volume of "where did my dashboard go" hits a threshold, add a one-week migration toast.

---

## Open follow-ups

- Decide Opus vs Sonnet for opener turn (end of Phase 1)
- Confirm sidebar grouping with team after Phase 2 (no features should feel orphaned)
- Pricing/billing: confirm turn counting works correctly when chat happens via Studio vs direct API
- Telemetry: add Studio-specific events (`studio.opener_shown`, `studio.first_tool_call`, `studio.session_complete`) for measuring activation lift

---

## Reference

- Adversarial review of Origami: `docs/ORIGAMI-ADVERSARIAL-REVIEW.md`
- Origami MVP plan (precursor): `docs/ORIGAMI-MVP-PLAN.md`
- Origami name collision context: `docs/ORIGAMI-NAME-COLLISION.md`
- Pricing strategy: `docs/PRICING.md`
- Memory: `~/.claude/projects/-Users-appa-Desktop-code-bonito/memory/project_mucker_danny.md`
