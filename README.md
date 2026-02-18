# 🐟 Bonito

**Unified AI operations — governance, routing, cost management, and deployment across any AI provider.**

Bonito gives engineering and platform teams a single operational layer to manage AI workloads across AWS Bedrock, Azure AI Foundry, Google Vertex AI, and more. Connect providers, enforce governance policies, track costs in real time, and manage team access — all from one platform with an AI copilot that helps you move faster.

## Why Bonito?

AI adoption is accelerating, but operational tooling hasn't kept up. Teams juggle separate consoles for each cloud provider, have no unified view of costs, and struggle to enforce consistent governance across providers.

Bonito solves this with:

- **Operational control** — One dashboard for all your AI providers. Manage models, deployments, and routing policies without switching between cloud consoles.
- **Governance & compliance** — Built-in policy engine for SOC-2, HIPAA, and GDPR compliance checks. Audit logging across every action.
- **Cost visibility** — Real-time cost aggregation, forecasting, and optimization recommendations across all providers.
- **AI Context (Knowledge Base)** — Cross-cloud RAG pipeline. Upload company docs, embed with any provider's model, and inject context into any LLM query — vendor-neutral knowledge that works with every model on every cloud.
- **Team management** — Role-based access control, team seats, and (coming soon) SSO/SAML for enterprise identity management.
- **AI copilot** — An intelligent assistant that helps with onboarding, configuration, troubleshooting, and infrastructure-as-code generation.
- **Multi-cloud gateway** — OpenAI-compatible API proxy with intelligent routing, failover, and load balancing across providers.

## How Bonito Compares

We're not the only platform in this space. Here's an honest look at how we fit:

| Capability | Bonito | Portkey | LiteLLM | Helicone |
|---|---|---|---|---|
| Multi-cloud gateway | ✅ | ✅ | ✅ | ✅ |
| Cross-cloud Knowledge Base (RAG) | ✅ Built-in | ❌ | ❌ | ❌ |
| Governance & compliance checks | ✅ Built-in | ❌ | ❌ | ❌ |
| Infrastructure-as-Code (Terraform) | ✅ Built-in | ❌ | ❌ | ❌ |
| AI copilot for operations | ✅ Built-in | ❌ | ❌ | ❌ |
| Cost management & forecasting | ✅ | ✅ | Basic | ✅ |
| Provider count | 3 (growing) | 200+ | 100+ | 30+ |
| Open source | No | Partial | Yes | Yes |
| SOC-2 certified | Roadmap | Yes | No | Yes |
| Self-hosted option | Yes (Docker) | Yes | Yes | Yes |

**Where Bonito shines:** Cross-cloud RAG (no competitor has this), integrated governance, IaC generation, and an AI copilot that ties it all together — not just a proxy layer, but a full operations platform.

**Where others lead:** Provider breadth (Portkey/LiteLLM support far more providers today), open-source community (LiteLLM), and compliance certifications (Portkey and Helicone have SOC-2 today).

## Quick Start

```bash
# Clone the repo
git clone <repo-url> && cd bonito

# Copy env file
cp .env.example .env

# Start everything
docker compose up --build -d

# Run database migrations
docker compose exec backend env PYTHONPATH=/app alembic upgrade head

# Open the app
open http://localhost:3001
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│          Next.js 14 · TypeScript · Tailwind      │
│              shadcn/ui · Framer Motion           │
│                  localhost:3001                   │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│                   Backend                        │
│           FastAPI · Python 3.12 · Async          │
│                  localhost:8001                   │
├──────────┬───────────┬───────────┬──────────────┤
│PostgreSQL│   Redis   │   Vault   │ Cloud APIs   │
│ pgvector │   :6380   │   :8200   │ Bedrock etc  │
│  :5433   │           │           │              │
└──────────┴───────────┴───────────┴──────────────┘
```

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, Framer Motion |
| Backend | Python FastAPI, async/await, uvicorn |
| Database | PostgreSQL 18.2 + pgvector (HNSW), SQLAlchemy, Alembic |
| Vector Store | pgvector with 768-dim embeddings (GCP text-embedding-005) |
| Cache | Redis 7 |
| Secrets | HashiCorp Vault (prod), SOPS + age (dev) |
| Infra | Docker Compose (local), Vercel + Railway (prod) |

## Project Structure

```
bonito/
├── frontend/              # Next.js app
│   └── src/
│       ├── app/           # App Router pages
│       └── components/    # UI components
├── backend/               # FastAPI app
│   ├── app/
│   │   ├── api/           # Route handlers
│   │   ├── core/          # Config, DB, Vault client
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   └── services/      # Business logic
│   └── alembic/           # DB migrations
├── vault/                 # Vault init scripts
├── secrets/               # SOPS encrypted secrets
├── docker-compose.yml
└── README.md
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3001 | Next.js web app |
| Backend | 8001 | FastAPI REST API |
| PostgreSQL + pgvector | 5433 | Primary database + vector store |
| Redis | 6380 | Cache & sessions |
| Vault | 8200 | Secrets management (UI available) |

## Secrets Management

**Local dev:** SOPS + age for encrypted secrets in git.

```bash
# Decrypt secrets
SOPS_AGE_KEY_FILE=secrets/age-key.txt sops decrypt secrets/dev.enc.yaml

# Edit secrets
SOPS_AGE_KEY_FILE=secrets/age-key.txt sops edit secrets/dev.enc.yaml
```

**Vault UI:** http://localhost:8200 (token: `bonito-dev-token`)

**Production:** HashiCorp Vault with AppRole/Kubernetes auth, HA mode.

## API Docs

With the backend running: http://localhost:8001/docs (Swagger UI)

## Roadmap

All 18 core phases are complete. Bonito is live at [getbonito.com](https://getbonito.com) with 12 active deployments across 3 clouds and 171+ gateway requests tracked.

### Completed (All 18 Phases) ✅
- ✅ Core platform (auth, RBAC, multi-cloud connections)
- ✅ Cloud integrations (AWS Bedrock, Azure AI Foundry, GCP Vertex AI)
- ✅ AI-powered chat & intelligent routing
- ✅ Compliance & governance engine (SOC-2, HIPAA, GDPR policy checks)
- ✅ Cost intelligence (aggregation, optimization, forecasting)
- ✅ Production deployment (Docker, CI/CD, deployment configs)
- ✅ Onboarding wizard with IaC template generation
- ✅ API Gateway (OpenAI-compatible proxy via LiteLLM)
- ✅ AI Copilot (Groq-powered operations assistant)
- ✅ Engagement & retention (notifications, analytics, digests)
- ✅ Model details & playground (live testing, parameter tuning)
- ✅ Visual routing policy builder (A/B testing, load balancing)
- ✅ Deployment provisioning (cloud endpoints, Terraform, auto-scaling)
- ✅ **AI Context (Knowledge Base)** — Cross-cloud RAG pipeline with pgvector, document upload/parse/chunk/embed, HNSW vector search, gateway context injection, and source citations
- ✅ Database migration to pgvector PG18.2
- ✅ AI Context onboarding integration (optional KB toggle, storage provider picker)
- ✅ IaC templates updated with KB storage permissions (S3, Azure Blob, GCS)
- ✅ One-click model activation across all 3 clouds

### Planned
- 📋 SSO/SAML integration (OIDC first, then SAML 2.0) — [Scoping doc](docs/SSO-SCOPE.md)
- 📋 SOC-2 Type II certification — [Roadmap](docs/SOC2-ROADMAP.md)
- 📋 Smart routing (complexity-aware model selection)
- 📋 VPC Gateway Agent (enterprise self-hosted data plane)
- 📋 Additional provider integrations (Anthropic, Cohere, Mistral)
- 📋 Advanced audit log export & SIEM integration

## Documentation

- [AI Context / Knowledge Base](ROADMAP.md) — Architecture, API design, and RAG pipeline details
- [Known Issues](docs/KNOWN-ISSUES.md) — Tracking document for known issues and fixes
- [Pricing](docs/PRICING.md) — Plans and pricing structure
- [SOC-2 Roadmap](docs/SOC2-ROADMAP.md) — Path to SOC-2 Type II certification
- [SSO Scoping](docs/SSO-SCOPE.md) — SSO/SAML implementation plan
- [Vault Production](docs/VAULT-PRODUCTION.md) — Vault hardening guide

---

Built with 🐟 by the Bonito team.
