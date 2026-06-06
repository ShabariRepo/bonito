# Bonito Pricing Strategy — 2026-06 Revision

**Status:** Draft. Structural change shipped (Builder + Growth tiers visible
as "NEW · COMING SOON" on the public page). Final dollar amounts pending.

**Background:** Danny Pantuso (Mucker Capital) advised per-agent pricing
during his hands-on weekend evaluation. Real per-tenant cost data from cat.shabari
and tradesauce orgs (Duncan Lane Financial) showed gateway COGS is small at SMB
volume because providers are BYOK / pass-through. Architecture insight: the
wheel-model (per-tenant orchestrator + specialists) makes agent count scale with
USER count, not capability, so per-agent overage as a primary lever punishes
the architecture Bonito's pitch is built around. Pivoted to request-volume +
project-count + feature-gating as the tier dimensions, with generous agent
counts included.

---

## Tier Ladder

| Tier | Price | Audience |
|---|---|---|
| **Free** | $0 / mo | Evaluators and indie tinkerers |
| **Builder** *(NEW)* | TBD (anchor ~$99) | Solo builders shipping their first agentic app |
| **Growth** *(NEW)* | TBD (anchor ~$349) | Small teams scaling agents across workstreams |
| **Pro** | $999 / mo | Teams shipping AI products across providers |
| **Enterprise** | $10K-$20K / mo | Orgs with governance, SSO, compliance needs |
| **Scale** | Custom | Dedicated infra, 99.99% SLA, multi-region |

Step-up math: each paid tier is roughly **4x the prior tier's request capacity**,
mentally easy for customers to grasp, and matches the value step-up across
feature gates.

---

## Per-Tier Limits

### Free — $0/mo
- 1 project, 1 user, 1 agent
- **25,000 requests/mo**
- 3 cloud providers
- 0 knowledge bases
- 1 gateway key, 2 personal access tokens
- 7-day audit log retention
- Community support (Discord)

### Builder *(NEW · COMING SOON)* — TBD
- 1 project, 1 team member
- **100,000 requests/mo** (matches Helicone / Portkey / Langfuse Pro tier)
- Up to 10 agents
- 3 cloud providers
- 1 knowledge base
- 3 gateway keys, 2 PATs
- CLI access, Stripe billing, cost analytics dashboard
- Memwright (conversational memory)
- 30-day audit log retention
- Email support

### Growth *(NEW · COMING SOON)* — TBD
- 3 projects, up to 5 team members
- **250,000 requests/mo**
- Up to 50 agents
- 5 cloud providers
- 5 knowledge bases
- 10 gateway keys, 5 PATs, 5 project tokens
- Persistent agent memory + vector search
- Approval queue / human-in-the-loop
- Org secrets store (Vault-backed)
- Scheduled autonomous execution
- Token efficiency metrics
- 60-day audit log retention
- Email support

### Pro — $999/mo *(unchanged price, expanded value)*
- 5 projects, unlimited team members
- **1,000,000 requests/mo** *(was 500K)*
- Up to **200 agents** *(was 5 — reflects wheel-model usage observed in prod)*
- All 6 cloud providers
- 20 knowledge bases
- 25 gateway keys, 10 PATs, 15 project tokens
- Advanced routing, load balancing, A/B testing
- One-click model activation, AI copilot, custom prompts library
- Audit trail export
- 90-day audit log retention
- Email support (24h response)

### Enterprise — $10K-$20K/mo
- Unlimited projects, users, agents, requests, providers, KBs
- All Pro features +
- SSO / SAML with JIT provisioning
- Role-based access control (RBAC)
- Compliance-ready architecture (SOC-2, HIPAA, GDPR)
- Agent HPA / Autoscaling
- Overflow queue
- VectorBoost (KB compression)
- IaC templates (Terraform)
- 365-day audit log retention
- 99.9% SLA, dedicated support engineer

### Scale — Custom
- Everything in Enterprise +
- Dedicated infrastructure & compute
- Multi-region deployment
- Custom fine-tuning pipelines
- 99.99% SLA
- 24/7 premium support with war room
- Custom data retention policies
- Dedicated account team

---

## Feature-Gating Matrix

Slack-style escalation: features unlock as you move up the ladder. A `—`
means the feature exists but is hard-gated; a numeric limit means soft-gated
with overage potential.

| Feature | Free | Builder | Growth | Pro | Enterprise | Scale |
|---|---|---|---|---|---|---|
| **Capacity** | | | | | | |
| Projects | 1 | 1 | 3 | 5 | Unlimited | Unlimited |
| Team members | 1 | 1 | 5 | Unlimited | Unlimited | Unlimited |
| Gateway API keys (`bn-`) | 1 | 3 | 10 | 25 | Unlimited | Unlimited |
| Personal access tokens (`bp-`) | 2 | 2 | 5 | 10 | Unlimited | Unlimited |
| Project tokens (`bj-`) | — | — | 5 | 15 | Unlimited | Unlimited |
| Agents | 1 | 10 | 50 | 200 | Unlimited | Unlimited |
| Knowledge bases | 0 | 1 | 5 | 20 | Unlimited | Unlimited |
| Routing policies | — | 1 | 3 | 10 | Unlimited | Unlimited |
| Requests / month | 25K | 100K | 250K | 1M | Unlimited | Unlimited |
| Cloud providers | 3 | 3 | 5 | 6 (all) | Unlimited | Unlimited |
| Audit log retention | 7d | 30d | 60d | 90d | 365d | Custom |
| **Gateway** | | | | | | |
| Multi-provider failover | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Auto cross-region (Bedrock) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Model playground | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Per-key model restrictions | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Rate limiting (per-key / org) | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Advanced routing (cost / latency / A/B) | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Advanced load balancing | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Multi-region routing | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Agents** | | | | | | |
| Agent framework (Bonobot) | 1 agent | 10 | 50 | 200 | Unlimited | Unlimited |
| Memwright (conversational memory) | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Persistent agent memory + vector | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Agent-to-agent delegation | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Scheduled autonomous execution | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Approval queue / HITL | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Agent HPA / autoscaling | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Overflow queue | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| External orchestration / breadcrumbs | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **AI Context (RAG)** | | | | | | |
| KB upload & indexing | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Vector search (pgvector) | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Citation rendering | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| VectorBoost (KB compression) | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Team-isolated KBs | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Analytics & Cost** | | | | | | |
| Basic cost dashboard | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cost analytics & breakdown | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Budget alerts & spend caps | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Token efficiency metrics | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Usage trends & forecasting | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Per-team cost attribution | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Operations** | | | | | | |
| Stripe billing integration | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Org secrets store (Vault) | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| AI copilot assistant | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Custom prompts library | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| One-click model activation | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Deployment provisioning | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Security & Compliance** | | | | | | |
| CLI access | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Audit trail | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Audit trail export | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| SSO / SAML | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| RBAC | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Compliance scanning (SOC-2, HIPAA, GDPR) | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| IaC templates (Terraform) | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Custom integrations & webhooks | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Support & SLA** | | | | | | |
| Community (Discord) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Email | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Email (24h SLA) | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Dedicated support engineer | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| 99.9% SLA | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| 99.99% SLA | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 24/7 war room access | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Infrastructure** | | | | | | |
| Shared multi-tenant | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| Dedicated infrastructure | ❌ | ❌ | ❌ | ❌ | optional | ✅ |
| Multi-region | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Custom fine-tuning | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| On-premise deployment | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |

---

## Competitive Benchmarks (Request Volume)

| Platform | Tier / Price | Requests included | $/1K equivalent |
|---|---|---|---|
| Helicone | Pro $50/mo | 50K | $1.00 |
| Portkey | Pro $99/mo | 100K | $0.99 |
| Langfuse | Pro $59/mo | 100K events | $0.59 |
| LangSmith | Plus $39/mo | 10K traces | $3.90 |
| **Bonito Builder** | **TBD ~$99** | **100K** | **~$0.99** (aligned) |
| **Bonito Growth** | **TBD ~$349** | **250K** | **~$1.40** (slight premium for added features) |
| **Bonito Pro** | **$999** | **1M** | **~$1.00** (volume tier, equal-rate) |

Bonito's per-request pricing is competitive with the observability/gateway category and
**justifies a slight premium for the agent framework + KB + voice + governance** stack that
competitors don't include.

---

## Profitability Notes (from real data)

**Real per-tenant data, 90-day, from production org (Duncan Lane Financial / tradesauce):**
- 17,307 requests, $324.29 provider cost
- 5 active projects, 49 agents
- Provider cost is **pass-through** (BYOK) — zero COGS to Bonito for inference
- Bonito's actual marginal infra cost (DB writes, audit logs, gateway compute, KB storage) estimated at **$5-15/mo** for a tenant at this volume

**Gross margin per tier (estimated, before support cost):**
- Free: -$5/mo (acquisition cost; ad budget)
- Builder ($99): ~$85-95/mo margin (85-95%)
- Growth ($349): ~$320-340/mo margin (~95%)
- Pro ($999): ~$950+/mo margin (95%+)
- Enterprise+: high absolute, smaller % due to support overhead

**The wheel-model COGS insight:** Bonito's per-tenant orchestrator pattern means an
agent's marginal cost is dominated by *its requests*, not its existence. An idle agent
costs almost nothing. This is why per-agent pricing punishes the architecture; volume-based
pricing aligns with actual cost.

---

## Rollout Plan

### Phase 1 — Structural change (SHIPPED 2026-06-06)
- ✅ Public pricing page: Builder + Growth added with NEW · COMING SOON badges
- ✅ Pro updated: 200 agents, 1M requests, "all 6 providers"
- ✅ Grid restructured for 6 tiers
- ⏳ Comparison table values: Builder/Growth currently mirror Starter; per-row split needed before launch

### Phase 2 — Final pricing decision (next)
- Decide Builder + Growth dollar amounts (anchors: ~$99 / ~$349)
- Validate against Stripe COGS + transaction fee math
- Customer comms plan for existing Starter customers (grandfather or migrate)
- Validate proposed tier limits against real-customer usage (OuchGPT, AdVan, Memory Creative)

### Phase 3 — Backend gating (engineering)
- Audit `feature_gate.require_feature()` coverage; add new tier rows to enum
- Add per-tier limits to `core/feature_gate.py` matrix (already partial)
- Enforce project count, agent count, KB count, KEY count limits
- Audit log retention already tier-gated (done 2026-05-27)
- Memwright already tier-gated (done — small models get none)
- VectorBoost already gated (Enterprise+)
- Add Stripe usage-record metering for request overage
- Add CLI tier indicators (`bonito auth whoami` already shows org)

### Phase 4 — Billing engine (engineering)
- Stripe products: 4 → 6 products (add Builder + Growth)
- Stripe metered billing for request overage (over-cap on Builder/Growth/Pro)
- Webhook for tier upgrade/downgrade
- In-app "Upgrade your plan" UI
- Trial-to-paid conversion flow

### Phase 5 — Marketing & docs
- Pricing page comparison table: detailed Builder/Growth row values
- FAQ updates (current FAQ mentions old Starter)
- Marketing site copy site-wide
- Documentation about tier limits
- "Choose your plan" wizard

---

## Open Decisions Before Launch

1. **Final Builder + Growth prices** (anchor ~$99 / ~$349; gut check against real conversion data)
2. **Overage rate** for requests above tier cap — proposed $0.50-$1 per 1K requests, decision pending
3. **Existing Starter customers** — grandfather at $199 with new bigger limits OR migrate them to Growth (~$349)?
4. **Pro grandfather policy** — Pro stays at $999 but limits expand. No action required for current Pro customers (they get more).
5. **Free tier guard** — cap requests-per-agent to prevent abuse (someone hammering production traffic through 1 free agent)
6. **Per-agent overage at Builder + Growth** — yes/no? Current proposal: NO, agent count is included generously, request volume is the overage lever
7. **AI Code Review limits per tier** — currently included in Pro ("100 reviews/mo"). Need a number for Builder + Growth.

---

## Why This Beats Pure Per-Agent (Danny's Original Advice)

Danny's instinct was right on one front: SMB customers want predictable, value-aligned pricing. He was wrong on the lever:
- Per-agent pricing punishes Bonito's wheel-model architecture (per-user orchestrators inflate agent count)
- Real customer data shows agent count scales with user count, not with capability
- Real COGS is driven by request volume, not agent existence

So we take Danny's *structural* advice (more tiers, smaller SMB anchors, predictable per-tier escalation) without his specific lever (per-agent). The result is value-aligned to actual COGS and architecture-aligned to Bonito's core thesis.

---

## Source

Pricing analysis distilled from:
- Danny Pantuso (Mucker Capital) advice during weekend evaluation (2026-06-06)
- Real per-tenant cost data from cat.shabari + tradesauce production orgs (2026-06-06)
- Competitor pricing from Helicone, Portkey, Langfuse, LangSmith public pricing pages
- Bonito's existing pricing page and feature inventory

This is a starter framework. Final tier limits and dollar amounts pending validation
against Stripe COGS, customer usage curves, and competitive recalibration.
