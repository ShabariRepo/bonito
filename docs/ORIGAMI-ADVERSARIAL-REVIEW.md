# Origami MVP — Adversarial Review

**Date:** 2026-06-06
**Run by:** Plan agent, cold read of `docs/ORIGAMI-MVP-PLAN.md` + `docs/PRICING-STRATEGY-2026-06.md`
**Outcome:** Plan needs revision before code starts. 5 critical, 8 high, 10 medium, 5 low.

> Note: "Origami" name is being retired due to collision with YC-backed `origami.chat` (see `ORIGAMI-NAME-COLLISION.md`). Findings below still apply to the feature regardless of final name.

---

## CRITICAL — block code start

1. **Migration number collision.** Spec says "Migration 045: `origami_audit_log`" but `045_add_user_id_isolation.py` already exists in `backend/alembic/versions/`. **Fix:** bump to 046 (or whatever's next); merge migration if branches diverge — Bonito hit this exact bug 2026-05-25.

2. **RLS claim is unenforceable as written.** Audit doc says "row-level security policy denies non-INSERT verbs even for service accounts." Zero existing `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` in the codebase. The backend connects as a superuser-equivalent role, so RLS is a no-op unless a least-priv role exists. **Fix:** either (a) add a dedicated `origami_writer` Postgres role with `INSERT`-only grant and route audit writes through a separate pool, or (b) drop the "append-only enforced at DB" claim and call it "policy enforced in app."

3. **`org_id` injection contract is undefined for tool calls.** Origami runs as a Bonobot in `system-org` but "acts under user auth." Spec doesn't say where the user's `org_id` is injected when tool wrappers fire. The agent runtime fans out to background tasks (autoscaler, queue drainer) which execute under system-org context. One missing `org_id` filter and we leak across tenants. **Fix:** every tool wrapper takes `org_id` as an explicit required arg sourced from the access token record, never from agent session context. Add a pytest that calls each tool with mismatched session/token and asserts 403.

4. **Orchestrator hallucinating `org_id` in a tool call.** Auth dependency reading `org_id` from token only protects HTTP routes. Internal tool dispatch in the Bonobot framework doesn't go through FastAPI — Sonnet emits JSON, framework calls Python. Nothing stops the model from emitting `{"org_id": "<any-uuid>"}` as a tool param and the wrapper trusting it. **Fix:** strip `org_id` from every tool schema; inject server-side from the auth context post-parse, pre-execute. Validate via schema test.

5. **Stripe webhook race on "click Deploy twice."** Plan executes deferred plan on `payment_succeeded`. Webhook delivery is async (Stripe SLA: 24h worst case). User clicks Deploy → pays → clicks Deploy again 10s later → tier still old → second click silently runs degraded path or 402s → first webhook arrives → auto-deploys. **Fix:** lock the plan-card UI in a "pending payment" state keyed by `plan_card_id`; idempotency-key the execute path on `plan_card_id`; require the webhook to set `pending_card_id = NULL` before any execute proceeds.

---

## HIGH

6. **6-week timeline is aspirational by ~3 weeks.** Phase 0 alone is a week. Phase 1 packs orchestrator + 13 tools + new token type + auth dep + state machine + migration + RLS + audit helper into 2 weeks — historically Bonobot tool surfaces took ~3 days *each*. **Fix:** realistic ship is 9-10 weeks. OR scope cut to 6 tools (`list_org_state`, `create_agent`, `create_kb`, `upload_to_kb`, `link_kb_to_agent`, `mint_gateway_key`); drop `delegate_provider_connection` to Phase 2 — it's the riskiest UX.

7. **Pro quota of 10K turns = $660 worst-case at 66% COGS.** A single Pro customer scripting against the API can burn 10K on day one. There's no per-minute rate limit specified — only a monthly cap. **Fix:** per-minute rate limit (20/min Pro, 5/min Builder); 10× average daily usage anomaly trip pages on-call; default API access OFF, require user toggle.

8. **Free abuse vector if `INVITE_REQUIRED` ever flips false.** 50 Sonnet turns × N scripted orgs = blow up. At 10K fake orgs, $18K/mo COGS. **Fix:** pin `INVITE_REQUIRED=true` until billing card is required, or require Stripe card-on-file for chat access on Free (not for signup).

9. **Plan card with cross-tool dependencies has no rollback semantics.** Sequence `create_kb → upload_to_kb → link_kb_to_agent → create_agent` — if `upload_to_kb` fails mid-way (90s embedding timeout per 2026-05-25 fix), orphan KB sits in the tier-limit count. User retries → "tier limit reached" because the dead KB counts. **Fix:** each plan card gets a `saga_id`; on partial failure, reverse-apply via compensating tools. OR simpler: only commit the tier-counter increment on full success.

10. **"User closes tab between Deploy and execution."** If execute runs in HTTP request, tab close = cancel. If background, no progress UI for reopen. Plan doesn't say. **Fix:** background task with `plan_execution` row (`status: pending|running|success|failed`); UI re-attaches via `plan_card_id` on reopen and tails progress.

11. **Token auto-rotate is a footgun.** Phase 3 white-label customers with embedded sessions silently get a new token while old key references die. **Fix:** rotation is explicit; expired = re-auth flow, not silent mint.

12. **"Pull `feature_gate.py` live every turn, no caching" + 7K Sonnet input.** Each turn reads the full tier matrix into the prompt = bloats cost. **Fix:** inject only `{tier_name, hit_limits, gated_features}` summary, not the full `TIER_CONFIG` dict.

13. **Build-vs-buy: 80% of orchestrator + tool-call + plan-card is what existing agent SDKs do.** Plan-card pattern maps 1:1 to OpenAI Agents SDK's `Tool` + `RunResult.new_items` + interrupt-for-approval. Anthropic's `claude-agent-sdk` (released 2025-09) ships streaming + structured output + interrupt-resume. **Fix:** 2-day `claude-agent-sdk` spike before committing to from-scratch build. If it covers plan cards + interrupts, dogfood story becomes "first Bonito-hosted agent built on `claude-agent-sdk`, routed through our gateway" — still dogfood, way less code.

---

## MEDIUM

14. **`PROVIDERS_NO_MODELS` polls model_sync for 30s** but model sync runs every 24h, not on-demand. "Give me 30 seconds" copy lies 95% of the time. **Fix:** trigger immediate `model_sync` call for that provider and stream results, or change copy to "this can take a few minutes."

15. **No `PROVIDERS_PARTIALLY_BROKEN` state.** Multi-provider orgs with one broken connection still show READY. Agent Health dashboard shows red, chat says ready. **Fix:** state includes per-provider health; opening copy surfaces broken ones with `delegate_provider_connection`.

16. **`delegate_provider_connection` modal has no documented threat model.** Modal is in same browser context as chat panel. If chat React panel has an XSS via plan-card render, creds are in same DOM. **Fix:** modal opens in iframe pointed at `/api/providers/connect-frame` with strict CSP. Document the threat model explicitly.

17. **Per-tier turn quotas not in `feature_gate.py` today.** Plan claims live-read but `TIER_CONFIG` has no `turns_per_month` field. **Fix:** add to `TIER_CONFIG` before Phase 1 starts; metering table + Redis counter; otherwise quotas are theoretical.

18. **Audit log "redact creds via regex" rots fast.** Bedrock session tokens, Azure keys, Vertex JSON SAs all look different. Will leak. **Fix:** allowlist approach — explicit `redact: true` flag on tool param schema; default-redact unless explicitly allowed.

19. **GCS audit sink on hot path.** `gcs_log_sink.py` had the 43s GCS hang bug (2026-05-25). Audit is per-tool-call. **Fix:** enqueue to Redis stream, drain to GCS out-of-band; never block tool execute on GCS.

20. **Token rotation breaks audit forensic kill claim.** Spec: "every audit row references the exact token used" — but TTL rotation means original `token_id` row vanishes from `access_tokens`. **Fix:** never DELETE token rows on rotation; mark `revoked_at`, keep FK valid forever.

21. **"Included on every plan" + zero rate limit on Free** = perfect headline-driven abuse. HN crowd will burn 50-turn caps as a parlor trick. **Fix:** 50 is per-month, hard. Test the cap before launch.

22. **Phase 3 white-label promised before MVP ships.** Memory Creative is a live deal. If the Phase 3 promise leaked into a sales conversation, you've sold a 6-month-out feature on a 6-week timeline. **Fix:** strip Phase 3 from any partner-facing version of the spec.

23. **Trademark concerns moot now (renaming) but applies to next name too** — pick something with USPTO Class 9/42 clearance, single-word novel preferred.

---

## LOW

24. **`Cmd+K` collides with universal command-palette key.** Browser extensions, Vercel-hosted tooling, etc. **Fix:** use `Cmd+J` or `Cmd+Shift+K`; reserve `Cmd+K` for a future palette.

25. **"Jovial opener" tone + destructive write actions** is a tension. First time the agent misroutes and confirms-then-deletes wrong agent, jovial reads as gaslighting. **Fix:** tone shifts to neutral-direct on any non-trivial write action.

26. **Success metric "60% new orgs complete first agent deployment via chat" has no baseline.** Set the current % via dashboard in Week 1 or target is unfalsifiable.

27. **Demo gravity claim collides with state machine.** First-time demos start at `NO_PROVIDERS` → demo includes "now connect your Bedrock creds." That's a procurement conversation, not a 30s demo. **Fix:** pre-stage a demo org with providers connected; demo starts at `READY_NO_AGENTS`.

28. **Competitive response: Helicone / Portkey can ship chat-on-top in ~4 weeks** by wrapping their existing API with an OSS agent SDK. The "moat" claim ("requires owning the whole control plane") is true today but doesn't hold against a fast follower. **Fix:** ship before announcing broadly.

---

## Verdict

**Plan needs revision before code starts on:**

1. Migration number + actual RLS enforcement mechanism
2. `org_id` injection contract for tool calls
3. Stripe-webhook-vs-double-deploy idempotency
4. Realistic 9-10 week timeline OR scope cut to 6 tools
5. 2-day `claude-agent-sdk` spike to validate the build-from-scratch decision

Plus the rename, which is independent of these fixes.

---

## Critical files referenced

- `/Users/appa/Desktop/code/bonito/backend/app/services/feature_gate.py`
- `/Users/appa/Desktop/code/bonito/backend/app/models/access_token.py`
- `/Users/appa/Desktop/code/bonito/backend/app/api/routes/access_tokens.py`
- `/Users/appa/Desktop/code/bonito/backend/app/api/routes/bonobot_agents.py`
- `/Users/appa/Desktop/code/bonito/backend/alembic/versions/044_add_access_tokens.py`
