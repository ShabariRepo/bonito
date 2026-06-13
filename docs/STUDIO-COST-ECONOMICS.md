# Bonito Studio / Origami — Cost Economics at Scale

_Last updated: 2026-06-13. Owner: cost/unit-economics analysis from the
prompt-caching + Bedrock cost-tracking work._

This doc models what Studio/Origami **costs to run** and **earns** as it
scales — per turn, per tier, per fleet, and as the free funnel grows. Studio
and Origami share one orchestrator (`run_origami_turn`), so this applies to
both.

> **TL;DR:** After the 2026-06-13 caching + cost-tracking work, a typical
> Studio build-turn costs **~$0.07 (cached Sonnet)**, the overage business is
> **profitable** (was underwater before), the blended fleet runs **~95% gross
> margin**, and the free funnel pays for itself at just **0.42% conversion**.
> Prod runs `claude-sonnet-4-6`; Haiku is a roadmap lever for ~3× more.

---

## 1. Cost per turn

A "turn" = one user message. A build-turn runs ~4 orchestrator iterations
(multiple LLM calls); a chat/Q&A turn is ~1. The static prefix (system prompt
~9.2K tokens + 13 tool schemas) is identical every call — which is why caching
dominates the cost picture (measured input:output ratio ≈ 21.8:1).

| Turn type | Uncached Sonnet | **Cached Sonnet (prod)** | Haiku (roadmap) |
|---|---|---|---|
| Light (Q&A, single create) | ~$0.06 | **~$0.02** | ~$0.006 |
| Typical build (project+KB+agent) | ~$0.21 | **~$0.07** | ~$0.02 |
| Heavy team (hub + 3–5 spokes) | ~$0.40 | **~$0.13** | ~$0.04 |
| **Blended (mix)** | ~$0.15 | **~$0.05** | ~$0.015 |

**Pricing inputs:** Sonnet $3/$15 per M (in/out); Haiku $1/$5; Opus $15/$75.
Caching: cache-read billed ~0.1×, cache-write 1.25×. Measured cache hit-rate
on a real 20-build run: **79% of input tokens served from cache** → **~71% off
input, ~66% off total turn cost.**

---

## 2. What made the economics work (2026-06-13)

Two fixes flipped Studio from "silently losing money" to "healthy margin":

1. **Prompt caching** (`ORIGAMI_PROMPT_CACHE=1`) — caches the static
   system+tools prefix on Anthropic/Bedrock. **~66% off every turn.** Proven
   on a real 20-person concurrent run (8,470 of 8,797 prompt tokens cache-read)
   and a full local Bedrock hackathon (20/20 builds, 71% input savings).
2. **Bedrock cost-tracking fix** — Bedrock-routed Claude was mislabeled
   `anthropic` and (worse) logged at **$0** because LiteLLM can't price the 4.6
   generation. This hid a ~$700/mo AWS line *and disarmed the $50/day spend
   cap*. The fix re-armed the cap → hard ~$1,500/mo ceiling, no silent runaways.

**Before this work**, a typical build-turn cost ~$0.21 (uncached Sonnet) or
worse on Opus — meaning the $0.12 overage was **−$0.09/turn underwater**, and
the cost bug hid it.

---

## 3. Overage pricing & margin

Studio inherits Origami's metering wholesale (same `metering.check_quota` /
`record_origami_turn`). Monthly base turns by tier, then per-turn overage:

| Tier | Base turns/mo | Sub $/mo | Overage (current flat) | Overage (proposed tiered) |
|---|---|---|---|---|
| Free | 50 | $0 | **hard cap** (blocks) | hard cap |
| Builder | 100 | $49 | $0.12 | **$0.30** |
| Starter | 100 | $199 | $0.12 | **$0.25** |
| Growth | 300 | $349 | $0.12 | **$0.20** |
| Pro | 1,000 | $999 | $0.12 | **$0.16** |
| Enterprise | 5,000 | $6,000+ | $0.10 | **$0.12** |
| Scale | ∞ | $200K+/yr | — | $0.10 |

**Margin on overage vs ~$0.05 blended cost (cached Sonnet):** all rates
profitable — lower tiers ~80–83%, Enterprise ~58%. **Soft spot:** heaviest
team builds (~$0.13) are at/just-over break-even at the $0.12 Enterprise rate.

**Proposed: tiered _descending_ overage** (lower tiers pay more). Matches
commitment to unit price, nudges upgrades, and ~doubles low-tier overage take
(Starter: $18 → $37.50 on 150 overage turns). See roadmap in CLAUDE.md.

---

## 4. Per-tier unit economics (engaged user at ~1.5× base)

Cost = all turns served × blended cost/turn. Cached Sonnet shown; Haiku in ().

| Tier | Sub | Overage rev | Cost (Sonnet) | **Net/mo (Sonnet)** | Net (Haiku) |
|---|---|---|---|---|---|
| Free | $0 | $0 | $2.00 | **−$2.00** | (−$0.60) |
| Builder | $49 | $15 | $7.50 | **$56.50** | ($61.75) |
| Starter | $199 | $37.50 | $12.50 | **$224** | ($232.75) |
| Growth | $349 | $30 | $22.50 | **$356.50** | ($372.25) |
| Pro | $999 | $64 | $70 | **$993** | ($1,042) |
| Enterprise | $6,000 | $240 | $350 | **$5,890** | ($6,135) |

Free is an **acquisition cost** (no overage by design); every paid tier nets
≈ its subscription (LLM cost is a rounding error).

---

## 5. Blended fleet — 100 users

Assumed pyramid: **70 Free / 12 Builder / 8 Starter / 5 Growth / 3 Pro / 2
Enterprise**. Paid usage split 40% power (1.5× base, overage) / 60% light
(0.6× base). Cost split into **included/"free" base turns** vs **overage turns**.

```
                          CACHED SONNET (PROD)        HAIKU (roadmap ref)
MRR (sub + overage)       $19,474                     $19,474
  ├ subscription          $18,922                     $18,922
  └ overage               $552  (~3% of revenue)      $552
Total cost                $968                        $290
  ├ included/free turns   $783  (81% of cost)         $235
  └ overage turns         $185                        $55
NET MARGIN                $18,506/mo  (95.0%)         $19,184/mo  (98.5%)
```

**Key reads:**
- **Subscription is the engine; overage is gravy** (~3% of revenue). Tiered
  overage is a margin/fairness lever, not a growth lever.
- **The included/free base turns are 81% of all cost** — the real variable
  cost, dominated by Free tier ($140/mo for 70 users). This is what scales with
  signups regardless of conversion.
- **~95% gross margin** on Sonnet (98.5% on Haiku). Without caching this would
  be ~85% and invisible.

---

## 6. Net margin vs Free-user count (Sonnet, paid base fixed)

Each Free user costs **$2.00/mo** (40 turns × $0.05). Revenue is flat (Free =
$0), so margin erodes linearly with the Free:paid ratio.

```
 free   free:paid   net $/mo    margin%
    0      0:1       18,646      95.7%
   70      2:1       18,506      95.0%   ← current fleet
  500     17:1       17,646      90.6%
 1000     33:1       16,646      85.5%
 3000    100:1       12,646      64.9%
 5000    167:1        8,646      44.4%
 9323    311:1            0       0.0%   ← break-even
```

- **>85% margin up to ~33 Free users per paid user.**
- **Break-even ~9,300 Free** against a fixed 30-paid base (~**311:1**).
- Haiku triples headroom: break-even ~31,000 Free (~**1,036:1**).
- Hard cap (50 turns) bounds each Free user at **~$2.50/mo max**.

> This holds the paid base FIXED — the "Free balloons but nobody converts"
> stress test. It's a floor, not a forecast; real conversions lift the line.

---

## 7. Free-funnel break-even conversion

Lifecycle view: a Free user is active ~3 months (~$6 spend, Sonnet) before
converting or going dormant. One conversion ≈ **$1,440 LTV** ($120/mo paid
profit × 12-mo retention).

| | Break-even conversion | At typical 2% (per 1,000 free) |
|---|---|---|
| **Sonnet (prod)** | **0.42%** | +$22,800 net |
| Haiku (roadmap) | 0.12% | +$23,200 net |

Typical freemium B2B converts **2–5%** — an order of magnitude above
break-even. **Every Free user is deeply net-positive** as long as conversion
clears ~0.4%. Studio can hand out Free generously (e.g., a hackathon crowd)
without denting margin.

---

## 8. Roadmap levers

1. **Haiku-primary for prod orchestration** (post-Tech-Week) — matched Sonnet
   reliability on simple/RAG builds at ~3× lower cost; ~90% on complex team
   builds (under-delivery, which failover does NOT rescue). Biggest impact is
   making the **free funnel ~3× cheaper to scale**, not the paid builds. Ideal:
   complexity-gated routing — simple → Haiku, multi-agent teams → Sonnet.
2. **Tiered descending overage** (Builder $0.30 → Scale $0.10) — ~doubles
   low-tier overage take, fixes the heavy-build margin on all but Enterprise.
3. **Gate heavy team builds to Haiku** — keeps every turn margin-positive.

---

## 9. Assumptions & caveats

- Cost/turn from a measured 20-build run (~1.34M input / 16K output) + the
  measured 79% cache hit-rate. Real per-turn cost varies with build complexity.
- Fleet distribution (70 Free / 2 Enterprise) and usage (40% of paid overage
  at 1.5× base) are **assumptions** — 2 Enterprise seats drive 62% of MRR here,
  so the fleet is sensitive to enterprise count.
- Conversion model assumes 3-mo free life, $120/mo paid profit, 12-mo
  retention — replace with real cohort data when available.
- **Prod is Sonnet.** All "prod" numbers use cached Sonnet ($0.05/turn
  blended). Haiku figures are roadmap reference only.

---

## Current prod config (2026-06-13)

```
ORIGAMI_MODEL           = claude-sonnet-4-6                     (primary, 20/20)
ORIGAMI_FALLBACK_MODELS = claude-sonnet-4-5,claude-opus-4-6     (failover net)
ORIGAMI_PROMPT_CACHE    = 1                                     (~66% off/turn)
Gateway spend cap       = $50/day per org (re-armed by cost-tracking fix)
```
