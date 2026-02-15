# Bonito Roadmap

_Last updated: 2026-02-15_

## Current Status
- All 18 core phases complete ✅
- Live at https://getbonito.com
- 3 cloud providers (AWS Bedrock, Azure OpenAI, GCP Vertex AI)
- 387+ models catalogued, 6 active deployments
- CLI tooling on `feature/bonito-cli` branch (merging to main)

---

## Near-Term (Next 2-4 weeks)

### 🔧 Production Polish
- [ ] Fix Azure deployment gap — zero deployments despite 133 models; need API key auth or TPM quota allocation
- [ ] Analytics endpoint — `/api/gateway/analytics` returns 404, needs fix or redirect to `/api/gateway/logs`
- [ ] Gateway logs field consistency — some fields show blank in list view
- [ ] UI warning when provider has 0 active deployments

### 🔐 SSO / SAML
- [ ] SAML 2.0 integration for enterprise SSO
- [ ] Support Okta, Azure AD, Google Workspace
- [ ] Role mapping from IdP groups → Bonito roles (admin, member, viewer)
- [ ] Session management & token refresh for SSO users

### 🖥️ CLI Finalization
- [x] Core commands: auth, providers, models, deployments, chat, gateway, policies, analytics
- [ ] Publish to PyPI as `bonito-cli` (name available)
- [ ] `bonito doctor` command — diagnose connectivity, auth, provider health
- [ ] Shell completions (bash/zsh/fish) via `bonito completion install`
- [ ] `--quiet` flag for CI/CD automation
- [ ] Homebrew formula / tap for macOS users
- [ ] README + docs page for CLI

---

## Medium-Term (1-3 months)

### 🧠 Smart Routing (Pro Feature) ⭐
_Complexity-aware model routing — auto-detect prompt complexity and route to the cheapest model that can handle it._

**Why:** Save 40-70% on AI spend without manual model selection. No competitor (LiteLLM, Portkey, Helicone) has this natively.

**Approach:** Classifier-based (Phase 1), then upgrade to embeddings (Phase 2).

**Phase 1 — Rule-Based Classifier (~1 week)**
- Heuristic scoring: token count, keyword detection (translate/summarize = simple; analyze/compare/code = complex)
- Map complexity tiers to model tiers (e.g., simple → Flash Lite, medium → Flash, complex → Pro)
- Configurable thresholds per routing policy
- New strategy type: `smart_routing` alongside existing cost_optimized, failover, etc.

**Phase 2 — Embedding-Based (~2-3 weeks)**
- Embed prompts, cluster into complexity buckets using historical data
- Train on org's own usage patterns (personalized routing)
- A/B test against rule-based to measure savings

**Packaging:**
- Free tier: rule-based routing only (failover, cost-optimized, A/B test)
- **Pro ($499/mo): Smart routing ON** — the headline feature
- Enterprise: smart routing + custom model tiers + SLA + routing analytics dashboard showing savings

**Competitive positioning:** "Connect your clouds, turn on smart routing, save 50%+ on AI spend."

### 🏗️ VPC Gateway (Enterprise)
- Self-hosted gateway deployed into customer's VPC
- Control plane stays hosted by Bonito (SaaS management)
- Like Kong/Istio model — data never leaves customer's network
- Terraform module for one-click VPC gateway deployment
- Enterprise tier: $2K-$5K/mo base + usage

### 📊 Advanced Analytics
- [ ] Cost optimization recommendations (auto-suggest cheaper models based on usage)
- [ ] Model performance comparison dashboard
- [ ] Department-level cost attribution
- [ ] Budget alerts and automatic throttling
- [ ] Weekly digest emails via Resend

### 🤖 Agent Framework (Phase 19+)
- [ ] Agent registry — define AI agents with tool chains
- [ ] Agent observability — trace multi-step agent runs
- [ ] Agent cost attribution — who/what is spending
- [ ] Multi-model agent pipelines (chain cheap→expensive for RAG patterns)

---

## Long-Term (3-6 months)

### 🌐 Marketplace
- [ ] Pre-built routing templates (cost-saver, quality-first, compliance-focused)
- [ ] Community-shared policies and configurations
- [ ] Partner integrations (LangChain, LlamaIndex, CrewAI)

### 🔒 Compliance & Governance
- [ ] Full SOC2 / HIPAA compliance checks (not just structural)
- [ ] Data residency enforcement (route to specific regions only)
- [ ] PII detection and redaction in prompts
- [ ] Audit log export (SIEM integration)
- [ ] DLP policies — block certain content from leaving the org

### 📱 Multi-Channel
- [ ] Slack bot for team model management
- [ ] Teams integration for enterprise orgs
- [ ] Mobile app (iOS/Android) for monitoring

---

## Pricing Strategy
| Tier | Price | Key Features |
|------|-------|-------------|
| Free | $0 | 3 providers, basic routing, 1K requests/mo |
| Pro | $499/mo | **Smart routing**, unlimited requests, analytics, API keys |
| Enterprise | $2K-$5K/mo | VPC gateway, SSO/SAML, compliance, SLA |
| Scale | $50K-$100K+/yr | Dedicated support, custom integrations, volume pricing |

---

## Competitor Watch
| Competitor | Smart Routing? | Self-Hosted? | Notes |
|-----------|---------------|-------------|-------|
| LiteLLM | ❌ Rule-based only | ✅ | OSS proxy, no complexity awareness |
| Portkey | ❌ Loadbalance/fallback | ❌ SaaS only | Good observability |
| Helicone | ❌ No routing | ❌ SaaS only | Logging/analytics focused |
| OpenRouter | ✅ via NotDiamond | ❌ Consumer | Not enterprise, adds dependency |
| CGAI | ❌ | ❌ | Crypto verification angle |
| Cloudflare AI GW | ❌ Basic | ❌ | Tied to CF ecosystem |

**Bonito's edge:** Integrated product (onboarding + IaC + console + governance + gateway + smart routing + agent) — not just a proxy.
