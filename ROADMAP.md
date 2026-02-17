# Bonito Roadmap

_Last updated: 2026-02-17_

## Current Status
- All 18 core phases complete ✅
- Live at https://getbonito.com
- 3 cloud providers (AWS Bedrock, Azure OpenAI, GCP Vertex AI)
- 387+ models catalogued, 6 active deployments
- CLI tooling on `feature/bonito-cli` branch (merging to main)

---

## Near-Term (Next 2-4 weeks)

### ⚡ Gateway Scaling (Done + Next)
- [x] Workers 2→4 (start-prod.sh default)
- [x] Redis connection pool (20 max connections, configurable)
- [x] `ADMIN_EMAILS` env var for platform admin access
- [x] Platform admin portal (org/user management, system stats, knowledge base)
- [ ] Railway replicas (2-3 instances) — when first paying customer arrives
- [ ] Move router cache + Azure AD tokens to Redis (shared across workers/instances)
- [ ] Vault credential caching in Redis (reduce Vault calls on router rebuild)
- [ ] Per-tier rate limits (Free: 30/min, Pro: 300/min, Enterprise: custom)

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

### 🏗️ VPC Gateway — Bonito Agent (Enterprise) ⭐
_Data-sovereign AI gateway deployed into customer's VPC. Control plane stays SaaS._

**Architecture: Control Plane / Data Plane Split**
```
Customer VPC                          Bonito SaaS (Railway + Vercel)
┌──────────────────────────┐          ┌──────────────────────────┐
│ Their Apps → Bonito Agent│          │ getbonito.com (dashboard) │
│       │                  │          │        │                  │
│       ├→ AWS Bedrock     │          │   Railway API (control    │
│       ├→ Azure OpenAI    │  config  │   plane: policies, keys, │
│       └→ GCP Vertex      │←────────→│   analytics, billing)    │
│       (data plane stays) │  + metrics│                          │
└──────────────────────────┘          └──────────────────────────┘
```

- **Data plane** (prompts, responses, embeddings) stays entirely in customer's VPC
- **Control plane** (policies, config, analytics metadata, billing) syncs to/from our Railway backend
- Frontend (getbonito.com) manages everything — never talks to the VPC agent directly
- Admins manage via dashboard as usual; config changes push down to agent automatically

**Bonito Agent: What It Is**
- Lightweight Docker container (~50-100MB): LiteLLM proxy + config sync daemon + metrics reporter
- NOT a full Bonito deployment — no Postgres, no Vault, no frontend
- Reads credentials from customer's own secrets manager (AWS Secrets Manager, Azure Key Vault, GCP Secret Manager)
- Authenticates to control plane via org token (`bt-xxxxx`), separate from user API keys (`bn-xxxxx`)
- Auto-updates from our container registry

**Deployment Options**
- Docker Compose (small teams): `docker run ghcr.io/bonito/gateway-agent:latest`
- Helm Chart (Kubernetes): `helm install bonito-gateway bonito/gateway-agent`
- Terraform Module (IaC): `module "bonito_gateway" { source = "bonito/gateway-agent/aws" }`

**Build Estimate:** 2-4 weeks when first enterprise customer needs it
- Week 1: Split gateway service into "full mode" vs "agent mode", build config sync protocol
- Week 2: Agent container image, org token auth, metrics push
- Week 3: Terraform modules (AWS ECS/Fargate, Azure Container Apps, GCP Cloud Run)
- Week 4: Dashboard integration (VPC status, agent health, deployment instructions)

**Edge Cases**
- Playground: shows note "routes through Bonito infra" or disabled for VPC orgs (point to CLI/curl)
- Agent health monitoring: heartbeat from agent → control plane, alert admin if agent goes dark
- Config sync: agent polls control plane every 30s for policy changes (or WebSocket push)
- Credential rotation: agent watches customer's secrets manager for changes, hot-reloads

**Pricing:** Enterprise tier $2K-$5K/mo base + usage

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
