# Studio / Origami load-test harness

A **separate-orgs** hackathon simulator for Studio (`/api/studio/turn`). Each
simulated participant runs in its **own org** (real-attendee isolation — no
cross-project contamination), every prompt + outcome is logged to JSONL, and a
summary classifies failures (success / cap-throttle / model under-deliver /
wiring fail / contamination).

> **Why separate orgs?** Running N personas in ONE org causes cross-project
> contamination: `create_agent`'s "most recent project" fallback grabs a
> neighbor's project under concurrency, so team builds wire across projects and
> fail. A real hackathon is N separate orgs — this harness mirrors that.

## Files

| File | Where it runs | What it does |
|---|---|---|
| `provision.py` | **in-container** (`railway ssh`) | creates N test orgs + admin users + a managed Anthropic provider each (enterprise tier), prints `{tag, org_id, email, password}` JSON |
| `run.py` | **locally** (hits the API) | logs each org in, runs a persona per org concurrently, logs every prompt + outcome, verifies per-org, prints pass/fail |
| `teardown.py` | **in-container** | deletes all `htest-%` orgs + their resources |

## Run it

```bash
# 1. provision N orgs (in-container; capture the JSON to a local file)
N=40
B64=$(base64 < provision.py | tr -d '\n')
railway ssh --service backend "echo $B64 | base64 -d | python3 - $N" \
  | awk '/PROV_JSON_START/{f=1;next} /PROV_JSON_END/{f=0} f' | tail -1 > /tmp/htest_orgs.json

# 2. (only if testing prod) bump the cap on the org that owns ORIGAMI_GATEWAY_KEY.
#    The orchestration LLM bills to that org, NOT the per-persona orgs, and the
#    default $50/day cap throttles early (it counts FULL-price/phantom cost,
#    ~2.6x real). Bump it via the policies API as a superadmin, then revert after.
#    (find the spend_limits policy id via GET /api/policies)

# 3. run the harness (local)
python3 run.py                       # prod (default)
BONITO_API=http://localhost:8001 LOADTEST_CONCURRENCY=6 python3 run.py   # local dev

# 4. teardown (in-container)
B64=$(base64 < teardown.py | tr -d '\n')
railway ssh --service backend "echo $B64 | base64 -d | python3"
```

Env for `run.py`: `BONITO_API` (default prod), `LOADTEST_ORGS`
(default `/tmp/htest_orgs.json`), `LOADTEST_RUNDIR`, `LOADTEST_CONCURRENCY`.

## Output

- `<rundir>/run-<ts>.jsonl` — one line per turn: `{org, persona, prompt,
  tools_completed, tools_failed, error, text_preview, classify}`.
- Console: per-persona pass/fail + totals.

## Gotchas learned building this (so the next person doesn't relearn them)

1. **Auth: log in, don't mint tokens.** The running server can use a different
   `SECRET_KEY` than the current Railway env (env changed since last restart;
   redeploying to "fix" it logs out all real users — don't). So `run.py`
   **logs in via `/api/auth/login`** to get a server-signed token.
2. **Valid email domains only.** `EmailStr` rejects reserved TLDs (`.test`,
   `.example`). `provision.py` uses `@htestsim.com`.
3. **Test orgs need a provider.** A fresh org with no provider makes the model
   bail on team builds ("no models available"). `provision.py` attaches a
   **managed Anthropic** provider (`BONITO_ANTHROPIC_MASTER_KEY`) — no creds
   needed, mirrors an onboarded customer.
4. **Cap throttling != build failure.** On prod the spend cap on the
   ORIGAMI_GATEWAY_KEY org fires ~2.6x early (full-price cost tracking). A
   `CAP_429` classify means the turn never ran, not that the build is broken.

## Reference result (2026-06-13, 40 isolated prod orgs, Sonnet)

Every build that **ran** succeeded — 26/26 (100%), incl. multi-agent team
builds. All 16 "misses" were `CAP_429` (cap throttling), zero real build
failures. Confirms: the single-org 25/40 was contamination; the product is
reliable at hackathon scale.
