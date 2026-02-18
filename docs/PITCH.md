# Bonito — Pitch Document

*Last updated: February 18, 2026*

---

## One-Liner

**Bonito is the enterprise AI control plane — unified governance, routing, and cost management across every cloud AI provider. With Bonobot, we're adding autonomous AI agents scoped per department, powered by centralized company knowledge.**

---

## The Problem

Enterprise AI adoption is exploding. By 2026, most mid-to-large companies use 2-3 cloud AI providers (AWS Bedrock, Azure OpenAI, GCP Vertex AI). Every team picks their own. The result:

- **3 separate billing dashboards** — nobody knows total AI spend
- **3 sets of credentials and governance** — compliance is a nightmare
- **3 duplicate RAG pipelines** — every team builds their own knowledge layer
- **Premium models for everything** — no cost optimization, 80% of requests don't need GPT-4o
- **No unified audit trail** — CISOs can't answer "what AI touches our data?"

This is exactly where cloud computing was in 2010 before tools like Terraform and Datadog unified the chaos.

---

## The Solution: Bonito

### Today — Enterprise AI Control Plane (Live in Production)

Bonito gives organizations a single pane of glass across all their AI providers:

| Capability | Status |
|---|---|
| **Multi-cloud onboarding** | ✅ Connect AWS, Azure, GCP in minutes with auto-generated IaC |
| **381+ model catalog** | ✅ Browse, compare, and deploy models across all clouds |
| **Smart routing gateway** | ✅ OpenAI-compatible API — route by cost, quality, or latency |
| **AI Context (RAG)** | ✅ Centralized knowledge base — any model, any cloud gets company docs |
| **Cost tracking & analytics** | ✅ Per-request, per-key, per-team cost attribution |
| **Compliance monitoring** | ✅ SOC2, HIPAA, GDPR, ISO27001 framework scanning |
| **One-click model activation** | ✅ Deploy models across clouds without console-hopping |
| **Gateway key management** | ✅ Per-team API keys with rate limits and restrictions |
| **Routing policies** | ✅ Cost-optimized, failover, A/B testing — configurable per use case |

**Validated in production:** 12 active deployments, 3 clouds, 187+ tracked requests, RAG search in <500ms, 84% cost reduction demonstrated.

### Tomorrow — Bonobot: Enterprise AI Agents

**The insight:** OpenClaw proved that personal AI agents — ones that connect to your tools, remember context, and act autonomously — are a billion-dollar category. But OpenClaw runs on your MacBook with your personal API keys. Enterprises need the same thing, but governed.

**Bonobot is OpenClaw for the enterprise.** Autonomous AI agents scoped per department, running on Bonito's control plane.

#### How It Works

```
┌─────────────────────────────────────────────────┐
│                 BONITO CONTROL PLANE             │
│   Models • Routing • Governance • Cost Tracking  │
├─────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ BONOBOT  │  │ BONOBOT  │  │ BONOBOT  │      │
│  │ Ad Tech  │  │ Support  │  │ Legal    │      │
│  │          │  │          │  │          │      │
│  │ 🧠 Ad    │  │ 🧠 Product│  │ 🧠 Policy │      │
│  │ Context  │  │ Context  │  │ Context  │      │
│  │          │  │          │  │          │      │
│  │ → Slack  │  │ → Teams  │  │ → Email  │      │
│  └──────────┘  └──────────┘  └──────────┘      │
│                                                  │
│  Each Bonobot:                                   │
│  • Has its own AI Context (scoped knowledge)     │
│  • Routes through Bonito's gateway (governed)    │
│  • Uses the cheapest model for each task         │
│  • Logs everything for compliance                │
│  • Stays within its project's budget             │
└─────────────────────────────────────────────────┘
```

#### The "Projects" Model

Each department or use case gets a **Project** in Bonito:

- **Own AI Context** — ad-tech indexes ad data, support indexes product docs, legal indexes contracts
- **Own Bonobot** — an autonomous agent that lives in Slack/Teams/WhatsApp
- **Own Resource Connectors** — scoped, audited access to enterprise data sources (S3, SharePoint, Google Drive, GitHub, Jira, Snowflake, databases, and more)
- **Own model routing** — high-volume tasks get cheap models, complex tasks get premium ones
- **Own budget** — spend caps, alerts, automatic throttling per project
- **Own audit trail** — every action logged, every model call tracked, every resource access recorded

The platform team manages it all centrally. Each department gets an AI assistant that feels personal but is fully governed.

#### Resource Connectors — Enterprise Data Access

Personal AI assistants (like OpenClaw) access your local file system. Enterprise needs something fundamentally different: **structured, scoped, audited access to enterprise data sources.**

Each Bonobot gets **Resource Connectors** — integrations with the systems that department actually uses:

```
┌─── BONOBOT: Ad Tech Department ─────────────────────────┐
│                                                          │
│  🧠 AI Context (indexed knowledge — semantic search)     │
│     └── Reads from connected resources, indexes in       │
│         pgvector for RAG queries                         │
│                                                          │
│  🔌 Resource Connectors (live, real-time access)         │
│     ├── 📁 AWS S3: s3://adtech-assets/* (read-only)      │
│     ├── 📊 Google Sheets: Campaign Tracker (read/write)  │
│     ├── 💬 Slack: #adtech channel (read/send)            │
│     └── 🔧 GitHub: adtech-configs repo (read-only)       │
│                                                          │
│  ❌ Cannot access:                                       │
│     ├── HR's SharePoint                                  │
│     ├── Finance's Snowflake                              │
│     └── Any resource not explicitly connected            │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Two modes of data access:**

| Mode | Purpose | When to use |
|---|---|---|
| **AI Context (RAG)** | Indexed knowledge for semantic search. Docs ingested → chunked → embedded → pgvector. | "What does our policy say about X?" — static docs, infrequent changes |
| **Resource Connectors** | Live read/write to enterprise systems at query time. Real-time, structured or unstructured. | "What's the status of campaign Y right now?" — dynamic, live data |

**Security guarantees:**
- **Scoped**: Admin controls exactly which resources each agent can touch. No ambient authority.
- **Audited**: Every data access logged with context — who, what, when, why, result. SOC2/HIPAA ready.
- **Credential isolation**: Agents never see raw credentials. Short-lived tokens from Vault (hosted) or customer's secrets manager (VPC).
- **Revocable**: Disconnect a connector = instant access removal.
- **Compliant**: CISO can answer "what data does the Ad Tech AI access?" in one dashboard view.

**Supported connectors (at launch):**

| Tier 1 (Launch) | Tier 2 (Fast-follow) |
|---|---|
| AWS S3, Azure Blob, GCS | Confluence, Jira |
| SharePoint / OneDrive | Slack, Microsoft Teams |
| Google Drive / Docs / Sheets | Snowflake, PostgreSQL, MySQL |
| GitHub / GitLab | Salesforce |

Custom connectors via REST/GraphQL adapter for Enterprise tier.

---

## Why Now

1. **Category validated:** OpenClaw's acquisition by OpenAI (Feb 2026) proves personal AI agents are a massive market. Enterprise is the next frontier.

2. **Enterprise AI spend is exploding:** Companies are spending $100K-$1M+/year on AI API calls with zero optimization. Bonito's smart routing saves 60-90%.

3. **RAG is the #1 enterprise use case:** Every company wants AI that knows their data. Bonito's AI Context is already built and working. Most competitors don't have a knowledge layer.

4. **Multi-cloud is the default:** 73% of enterprises use 2+ cloud providers. Single-cloud solutions don't work anymore.

5. **Compliance pressure is mounting:** SOC2, HIPAA, GDPR requirements are making ungoverned AI untenable. Bonito provides the audit trail.

---

## Market

### TAM/SAM/SOM

| | Size | Basis |
|---|---|---|
| **TAM** | $45B | Enterprise AI infrastructure & ops tooling (2027 projection) |
| **SAM** | $8B | Multi-cloud AI management, routing, governance for mid-to-large enterprises |
| **SOM** | $200M | 2,000 enterprise customers × $100K avg annual contract (Year 3-5 target) |

### Competitive Landscape

| Competitor | What They Do | What They Don't |
|---|---|---|
| **LiteLLM** | Open-source AI gateway/proxy | No management console, no AI Context, no compliance, no agents |
| **Portkey** | AI gateway + observability | No IaC onboarding, no RAG, no deployment provisioning |
| **Helicone** | AI observability & cost tracking | Observability only — no routing, no governance, no agents |
| **Kong AI Gateway** | Enterprise API gateway + AI plugins | API gateway, not an AI operations platform |
| **Cloudflare AI Gateway** | Edge AI request management | Single-vendor, no multi-cloud orchestration |
| **Microsoft Copilot** | Enterprise AI assistant | Azure-only, no multi-cloud, no custom knowledge scoping per department |

**Bonito's edge:** No competitor does the full lifecycle — onboarding → IaC → model management → routing → AI Context → governance → agents. Most solve one piece. We're the integrated platform.

**Bonobot's edge:** Enterprise-grade agents with per-department knowledge scoping, governed routing, and cost controls. OpenClaw but for companies, not hackers.

---

## Business Model

### Current (Platform)

| Tier | Price | Target |
|---|---|---|
| **Free** | $0 | Individual developers, POC |
| **Pro** | $499/mo | Teams adopting multi-cloud AI |
| **Enterprise** | $2,000–$5,000/mo | Organizations needing governance + compliance |
| **Scale** | $50K–$100K+/yr | Large enterprises, dedicated infrastructure |

### Expansion (Bonobot — Add-on, requires Pro+)

**Two deployment models:**

| | Hosted (Bonito infra) | Self-Hosted (Customer VPC) |
|---|---|---|
| **Per Agent** | $349/mo | $599/mo |
| **5+ agents** | $297/mo each (15% off) | $509/mo each (15% off) |
| **10+ agents** | $262/mo each (25% off) | $449/mo each (25% off) |

**Each agent includes:**
- Scoped AI Context (dedicated knowledge base)
- Resource Connectors — live access to enterprise data sources (S3, SharePoint, Google Drive, GitHub, databases, etc.)
- Multi-channel messaging (Slack, Teams, WhatsApp, email)
- Governed routing through Bonito gateway (cost-optimized model selection)
- Budget cap + spend tracking per agent
- Full audit trail (every AI call + every resource access)
- Custom persona and instructions

**Connector limits by tier:**
- Pro agents ($349/mo hosted): Up to 5 connectors, Tier 1 connectors
- Enterprise agents ($599/mo VPC): Unlimited connectors, all tiers, custom connectors via REST/GraphQL adapter

**Why two tiers?**
- **Hosted**: Zero infra for the customer. Bonito runs the agents, manages credentials in Vault, handles everything. Lower barrier, faster onboarding.
- **VPC**: Agent runtime deployed in customer's VPC. Prompts and data never leave their network. Credentials stay in their secrets manager (AWS SM / Azure KV / GCP SM). Bonito control plane only sees metadata. For regulated industries and data-sovereign requirements.

**Revenue scenarios:**

| Customer Type | Platform | Agents | Monthly | Annual |
|---|---|---|---|---|
| Small team | Pro ($499) | 3 hosted ($1,047) | **$1,546** | $18,552 |
| Mid-size org | Enterprise ($3K) | 8 VPC ($4,072) | **$7,072** | $84,864 |
| Large enterprise | Scale ($8K) | 20 VPC ($8,980) | **$16,980** | $203,760 |

**At 500 customers averaging $8K/mo = $48M ARR**

---

## Traction

### Production Metrics (Feb 2026)

- **Live at** [getbonito.com](https://getbonito.com)
- **3 cloud providers** connected and active (AWS, Azure, GCP)
- **381 models** cataloged, 12 actively deployed
- **187+ gateway requests** tracked with full cost attribution
- **AI Context (RAG):** 49 chunks indexed, 10/10 search accuracy, avg 484ms latency, 0.634 avg relevance score
- **Gateway inference:** 8/8 tests passed across all 3 clouds with RAG context injection
- **Cost validated:** $0.04 total for test suite → projected 84% savings at enterprise scale

### E2E Validated

- **Meridian Technologies case study:** $2.25M annual savings (84% cost reduction), 37.5:1 ROI at 50K requests/day
- Full production test: auth, providers, models, deployments, gateway keys, routing policies, analytics, compliance, team management — all passing

---

## Product Roadmap

### Built ✅
- All 18 core phases complete
- Multi-cloud onboarding with IaC generation
- AI gateway with smart routing, failover, rate limiting
- AI Context (RAG) with cross-cloud knowledge injection
- One-click model activation across all providers
- Compliance monitoring (SOC2, HIPAA, GDPR, ISO27001)
- CLI (v0.2.0) for terminal-based AI management

### Next 6 Months
- **SSO/SAML** — enterprise authentication (Okta, Azure AD, Google Workspace)
- **Projects** — scoped environments per department (foundation for Bonobot)
- **Resource Connectors v1** — S3, Azure Blob, GCS, SharePoint, Google Drive, GitHub (Tier 1)
- **Bonobot v1** — per-project AI agent with AI Context, resource connectors, messaging integration
- **VPC Gateway** — self-hosted gateway + agent runtime deployed into customer's VPC
- **Advanced analytics** — cost optimization recommendations, budget forecasting

### 12 Months
- **Resource Connectors v2** — Confluence, Jira, Slack, Teams, Snowflake, Salesforce (Tier 2) + custom REST/GraphQL adapter
- **Bonobot marketplace** — pre-built agent templates (support bot, compliance bot, analyst bot)
- **Agent workflows** — multi-step autonomous tasks with approval gates
- **SOC2 Type II** certification
- **Self-serve enterprise** — fully automated onboarding for Enterprise tier

---

## Team

- **Shabari** — Founder & CEO. Software architect at FIS Global. Enterprise infrastructure background. Building Bonito full-stack (frontend, backend, infra, IaC).

*Currently solo founder. Seeking technical co-founder and/or seed funding to accelerate Bonobot development.*

---

## The Ask

**Seed round: $1.5–$3M**

Use of funds:
- **Engineering (60%):** 3-4 engineers to build Bonobot agent layer, Projects system, VPC Gateway
- **Go-to-market (25%):** First enterprise sales hires, content marketing, conference presence
- **Infrastructure (15%):** SOC2 certification, production hardening, multi-region deployment

**Milestones with funding:**
- Month 3: Projects + Bonobot v1 in private beta with 5 design partners
- Month 6: Bonobot GA, 20 paying customers
- Month 12: 100 customers, $2M ARR run rate, Series A ready

---

## Why Bonito Wins

1. **Already built.** Not a mockup — a working production platform with real multi-cloud AI operations.
2. **AI Context is the moat.** Centralized knowledge that any model on any cloud can access. Nobody else has this.
3. **Resource Connectors close the loop.** Agents don't just know your docs — they can read your Sheets, query your databases, access your repos. Scoped, audited, enterprise-grade.
4. **Bonobot is the land-and-expand.** Platform gets you in the door ($499/mo), agents expand to every department ($349-599/mo each). Natural upsell from hosted to VPC.
5. **Category timing.** OpenClaw proved the agent market. Enterprise is next. We're already 80% there.
6. **In the money path.** Every AI dollar flows through Bonito's gateway. That's real stickiness.

---

*"Connect your clouds. Know your costs. Give every team an AI that actually knows your business."*
