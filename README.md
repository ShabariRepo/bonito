# 🐟 Bonito

**The enterprise AI control plane.**

Provision, configure, manage, and govern AI workloads across AWS Bedrock, Azure AI Foundry, and Google Vertex AI — from one seamless platform.

## Why Bonito?

Every enterprise is under pressure to adopt AI. But the tooling is fragmented — AWS has Bedrock, Azure has AI Foundry, Google has Vertex. Each siloed, each complex, each locked in.

Bonito is the unified layer. Connect your clouds, deploy models, track costs, enforce governance — all from one place, with an AI-native UX that does the thinking for you.

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
│ PostgreSQL│   Redis   │   Vault   │ Cloud APIs   │
│  :5433    │   :6380   │   :8200   │ Bedrock etc  │
└──────────┴───────────┴───────────┴──────────────┘
```

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, Framer Motion |
| Backend | Python FastAPI, async/await, uvicorn |
| Database | PostgreSQL 16, SQLAlchemy, Alembic |
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
| PostgreSQL | 5433 | Primary database |
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

- [x] Phase 1: Foundation (scaffold, DB, secrets, Notion tracking)
- [ ] Phase 2: Core Platform (cloud providers, model catalog, dashboard)
- [ ] Phase 3: Enterprise (cost tracking, RBAC, governance, AI UX)
- [ ] Phase 4: Scale (routing optimization, compliance, IaC export)

---

Built with 🐟 by the Bonito team.
