# Chicago Tech Week Workshop — Roadmap

**Status:** scoping
**Lead:** Shabari + Danny Pantuso (Mucker Capital)
**Target:** Chicago Tech Week 2026 (date TBD pending dry-run + venue lock)
**Format:** harness-first hands-on agent build, 90 min, 30-50 attendees

---

## TL;DR

Attendees walk in with their AI coding harness (Claude Code, OpenClaw, Hermes,
etc.) and a laptop. We hand each one a care package containing a Bonito
token, an `AGENTS.md` context file, example YAMLs, and a cheat sheet. They
open the folder in their harness, the harness reads `AGENTS.md`, and the
attendee builds a working agent on Bonito by talking to their harness — same
way a Bonito-using founder iterates on their own product.

No MCP, no special protocol, no curl marathon. The harness's existing
capabilities (file edit, terminal, env vars) are enough. Our job is to ship
a care package the harness can actually run with.

---

## Workshop format

```
00:00  Open       Danny frames the agent thesis. Shabari shows Bonito at altitude.
00:10  Provision  Attendees claim care package. Open in their harness.
00:15  Build      60-min hands-on. Each attendee tells their harness what to build.
01:15  Showcase   3-5 attendees demo what their harness shipped.
01:25  Close      Keys to keep, community link, post-workshop access.
```

The build block is the entire workshop. Everything else exists to serve it.

---

## Care package contents (the deliverable that matters most)

```
workshop-2026/{attendee}/
├── .env                  # BONITO_TOKEN=... (model TBD — see token decision)
├── AGENTS.md             # harness-facing context doc — the most important file
├── examples/
│   ├── support-agent.yaml
│   ├── tool-agent.yaml
│   └── multi-provider.yaml
├── cheat-sheet.pdf       # for the human, when they get curious
└── README.md             # "step 1: pip install bonito-cli. step 2: open in harness."
```

**`AGENTS.md` is the single highest-leverage artifact.** It's the system
prompt for every attendee's harness. If it's good, the harness handles 80%
of the workshop without instructor intervention. If it's vague or stale,
every harness will subtly misuse Bonito and the workshop becomes a
firefighting exercise.

`AGENTS.md` must cover:
- What Bonito is (one paragraph, no marketing voice)
- Auth model: which token is in `.env`, which endpoints it authorizes, what *not* to call
- YAML schema for agents: minimal valid example + full example
- CLI commands the harness should reach for, with what each does
- Common patterns: RAG agent, tool-using agent, multi-provider routing
- Common errors and what they mean (same content as cheat sheet, but for an AI agent reading it, not a human skimming)
- Explicit `## Do not` section: "don't try to hit `/v1/*` with `bj-`", "don't regenerate the token, it's in env"

---

## Token model — open decision

| Token | `/v1/*` (gateway) | `/api/*` (CRUD + execute) | Per-org cap |
|---|---|---|---|
| `bn-` | ✅ | ❌ | unlimited |
| `bp-` (PAT) | ✅ | ✅ | Free=2, Pro=10, Enterprise+=unlimited |
| `bj-` (project) | ❌ today | ✅ | TBD — verify (Task #16) |

**The harness needs ONE token in `.env`** so it doesn't have to juggle
auth across surfaces. Three viable models:

1. **Pro tier + N `bj-` tokens, accept gateway-via-bn-on-screen-only.** Attendees can't curl `/v1/chat/completions` themselves. Works if workshop is purely agent-centric. Risk: harness tries a raw gateway call to test, hits 401, gets confused.
2. **Enterprise+ tier + N `bp-` (PATs).** One PAT per attendee covers everything. Cleanest UX. Higher cost ($10-20K/mo for the workshop month).
3. **Pro tier + N `bj-` tokens + Path B shipped first.** Path B = extend gateway auth to accept `bj-` (Task #18). One `bj-` covers everything. Lowest cost. Requires ~2 days of dev work pre-workshop.

**Decision criteria:** verify the `bj-` per-org cap on Pro first (Task #16). If Pro caps `bj-` at 10 like PATs, only Option 2 or 3 works for 30+ attendees. If `bj-` is uncapped, Option 1 ships today.

**My read:** Option 3 is the win — adds a real product capability (project tokens become first-class everywhere), and lets the workshop ship on Pro tier.

---

## Pre-event timeline

### Phase 1 — before announcing a date (next 2 weeks)
- [ ] Draft `AGENTS.md` v1 (Task #15)
- [ ] Verify `bj-`/`bp-` tier caps (Task #16)
- [ ] Decide token model based on caps (this doc, post-Task #16)
- [ ] Build care-package generator script (Task #17)
- [ ] Dry-run with 3-5 friendly external testers — time signup→deployed agent. Anything they trip on goes into `AGENTS.md` v2.

### Phase 2 — before locking with Danny
- [ ] Confirm prod state of `INVITE_REQUIRED` (done — currently OFF, no action)
- [ ] Test `pip install bonito-cli` on clean macOS / Linux / Windows boxes
- [ ] If Option 3 chosen: ship Path B PR (Task #18) and merge to prod
- [ ] Co-author workshop format doc with Danny — split between Bonito and Mucker responsibilities

### Phase 3 — workshop month
- [ ] Spin up workshop org on chosen tier
- [ ] Connect 1-2 providers (OpenAI + Anthropic minimum)
- [ ] Run care-package generator against attendee list, distribute
- [ ] Pre-event: 24-hour Slack/Discord support window for attendees doing pre-install
- [ ] Day-of: 2 Bonito engineers on-site for live tech support

---

## Related product roadmap items

These are real product gaps the workshop surfaces, worth doing regardless
of whether the workshop happens:

| Item | Tracked as | Why beyond the workshop |
|---|---|---|
| Path B: gateway accepts `bj-` | Task #18 | Project scoping should extend to the most-used surface (gateway), not just `/api/*`. Current split is awkward for any multi-project customer. |
| Auto-mint `bn-` on signup | (not tracked) | Today's onboarding has a hidden step before first gateway call. Removes friction for every new user, not just workshop. |
| Better error messages (gateway 4xx) | (not tracked) | The audit found raw `litellm` errors bubbling to users. Failover PR covers one slice; others remain. |
| Bulk provisioning helpers | Task #17 | Workshop-specific, but reusable for any sales/POC scenario where you need N sandbox accounts. |

---

## Open questions

1. **Workshop tier cost.** Pro = $999/mo. Enterprise+ = $10-20K/mo. Decision is gated on Task #16 (bj- caps) and #18 (Path B feasibility).
2. **Date.** Don't lock with Danny until Phase 1 is complete. Tell him "format locking in next 2 weeks, date locking together after that."
3. **Mucker logistical commitments.** Venue, registration, food, photographer — need a doc from Mucker side mirroring this one.
4. **Post-workshop access.** Do attendees keep their tokens after the workshop? For how long? Default: 30 days, revocable per-attendee via the workshop org admin.

---

## Reference

- Bonito CLAUDE.md — architectural patterns, agent framework, token types
- ouchgpt — running example of `bj-` token usage at runtime (`/Users/appa/Desktop/code/ouchgpt/lib/bonito.ts`)
- Failover PR — example of strictly-additive auth changes (#43058)
- `bonito_cli/examples/support-agent.yaml` — starting point for the workshop examples folder
