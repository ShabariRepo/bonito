"""
Static knowledge base articles for the Bonito platform admin portal.
"""

KB_ARTICLES = [
    {
        "slug": "gateway-architecture",
        "title": "Gateway Architecture",
        "description": "How the Bonito multi-tenant AI gateway works — routing, credential isolation, and request flow.",
        "category": "Architecture",
        "updated_at": "2026-02-17",
        "content": """# Bonito Gateway Architecture

## Overview

Bonito runs a **single multi-tenant gateway** deployed on Railway. All customer organizations share the same FastAPI instance, with logical isolation enforced at every layer.

```
Customer App → Bonito Gateway (Railway) → Customer's Cloud (Bedrock/Azure/Vertex)
                    │
                    ├── FastAPI + Uvicorn (async workers)
                    ├── LiteLLM Router (in-memory, per-org)
                    ├── PostgreSQL (connection pool)
                    ├── Redis (rate limiting)
                    └── Vault (credential storage)
```

## Request Flow

1. Customer app sends `POST /v1/chat/completions` with a `bn-...` API key
2. Gateway authenticates the key → resolves `org_id` via DB lookup
3. **Policy enforcement**: model allow-lists, spend caps, org-level restrictions (DB queries)
4. Build or retrieve **LiteLLM Router** for the org:
   - On cache hit: use the in-memory router (50 min TTL)
   - On cache miss: fetch credentials from **Vault**, build a new Router
5. LiteLLM proxies the request to the customer's own cloud deployment (Bedrock, Azure OpenAI, or Vertex AI)
6. Response streams back to the customer; cost and token usage logged to PostgreSQL
7. **Total gateway overhead**: ~5–20ms (excluding upstream LLM latency)

## Per-Org Isolation

Although all orgs share a single process, isolation is enforced through:

| Layer | Isolation Mechanism |
|-------|-------------------|
| **Credentials** | Each org's cloud keys stored in separate Vault paths (`secret/data/org/{org_id}/...`) |
| **LiteLLM Router** | Separate Router instance per org, cached in-memory with TTL |
| **API Keys** | `bn-` prefixed keys hashed and scoped to a single org |
| **Rate Limiting** | Per-key rate limits enforced via Redis |
| **Policies** | Per-org model allow-lists, spend caps, routing rules |

## Credential Flow

```
1. Admin stores cloud credentials via Dashboard
2. Backend encrypts and stores in Vault: secret/data/org/{org_id}/{provider}
3. On first gateway request (or cache miss):
   a. Fetch credentials from Vault
   b. Build LiteLLM Router with provider configs
   c. Cache router in-memory (50 min TTL)
4. Subsequent requests reuse cached router
5. On credential update: router cache invalidated, rebuilt on next request
```

## LiteLLM Router

Each org gets its own `litellm.Router` instance configured with:
- **Model list**: All models available across the org's connected providers
- **Routing strategy**: cost-optimized, latency-optimized, balanced, or failover
- **Fallback chains**: e.g., GPT-4o → Claude 3.5 Sonnet → Gemini Pro
- **Provider credentials**: Injected from Vault at build time

The Router handles:
- Model name normalization (OpenAI-compatible → provider-specific)
- Automatic retries with fallback
- Cost tracking per request
- Token counting and usage logging

## Streaming

Streaming requests (`stream: true`) use Server-Sent Events (SSE):
- Gateway opens an async generator
- Chunks forwarded as `data: {json}\\n\\n` events
- Token counts estimated post-stream if provider doesn't include usage in chunks
- Cost calculated and logged in the `finally` block after stream completes

## Database Schema (Key Tables)

- `gateway_keys` — API keys (hashed), org-scoped, with rate limits and model restrictions
- `gateway_requests` — Request log: model, tokens, cost, latency, status
- `gateway_configs` — Per-org configuration: enabled providers, routing strategy, fallback models
- `cloud_providers` — Connected cloud accounts with encrypted credentials
"""
    },
    {
        "slug": "scaling-guide",
        "title": "Scaling Guide",
        "description": "Phases, bottlenecks, and capacity planning for scaling the Bonito gateway.",
        "category": "Operations",
        "updated_at": "2026-02-17",
        "content": """# Bonito Scaling Guide

## Current Capacity (Single Railway Instance)

| Scenario | Sustainable? | Notes |
|----------|-------------|-------|
| 1–5 orgs, light usage (<10 req/min each) | ✅ Easy | Current state, no issues |
| 10–20 orgs, moderate (50 req/min each) | ⚠️ Tight | DB pool and memory pressure |
| 50+ orgs or any org at >100 req/min | ❌ No | Need horizontal scaling |
| Single enterprise client, 1000 req/min | ❌ No | DB pool exhaustion |

## Key Bottlenecks

| Bottleneck | Threshold | Impact |
|-----------|-----------|--------|
| DB connection pool | >60 concurrent DB operations | Requests queue, then 500 errors |
| Redis (single connection) | High concurrent rate-limit checks | Serialized; degrades gracefully |
| Router cache (in-memory) | Many orgs × N workers | Memory grows; each worker has its own cache |
| Vault fetches | Router cache miss burst | HTTP calls stack up |
| Railway container | Memory/CPU limits | OOM kill or CPU throttle |

## Scaling Phases

### Phase S1: Quick Wins (Pre-Launch)
No architecture changes — just configuration tuning:

- **Increase workers**: Set `WORKERS=4` in Railway env vars
- **Redis connection pool**: Replace single connection with pooled client (20 connections)
- **DB pool tuning**: Adjust `pool_size` per worker so total stays under Postgres limit
- **Vault credential caching**: Add Redis-backed cache layer
- **Rate limit tuning**: Free: 30/min, Pro: 300/min, Enterprise: custom

### Phase S2: Horizontal Scaling (First Paying Customer)
Multiple gateway instances behind a load balancer:

- **Railway replicas**: Scale to 2–3 instances
- **Move caches to Redis**: Router config, Azure AD tokens, Vault credentials
- **Shared-nothing workers**: Each instance is stateless, all state in Redis/Postgres
- **Health checks**: `/api/health` endpoint for load balancer

```
Customer App → Railway LB → Instance 1 ─┐
                           → Instance 2 ─┤→ Customer's Cloud
                           → Instance N ─┘
                                 │
                          Redis (shared)
                          Postgres (shared)
                          Vault (shared)
```

### Phase S3: Dedicated Gateway (Enterprise Tier)
Per-customer gateway for isolation and performance guarantees:

- Dedicated Railway instance per enterprise org
- Custom domain: `gateway.{customer}.getbonito.com`
- Dedicated DB pool and rate limits
- SLA-backed throughput and latency guarantees

### Phase S4: VPC Gateway (Enterprise+)
Gateway runs in customer's own cloud — data never leaves their network.
**The agent is fully stateless — no database on the customer's side.** It caches config in memory, pushes metrics to our Postgres, and serves requests via LiteLLM. All state lives in our control plane. See the **VPC Gateway Agent** article for the full architecture spec.

```
┌─── Customer VPC ─────────────────────────────┐
│  Customer App → Bonito Agent (stateless)      │
│                      ├── AWS Bedrock          │
│                      ├── Azure OpenAI         │
│                      └── GCP Vertex           │
│                 Config sync (outbound only)    │
└──────────────────────│────────────────────────┘
                       ↓
              Bonito Control Plane (SaaS)
              Our Postgres ← metrics pushed here
```

## Throughput Details

- **Uvicorn workers**: 2 async (default), supports 4+ with config
- **Concurrent connections**: ~200–500 (async I/O, not thread-bound)
- **DB pool**: 30 per worker (10 base + 20 overflow)
- **Per-key rate limit**: 100 req/min default (~1.7 req/s sustained)
- **Real bottleneck**: Upstream LLM latency (500ms–20s), not the gateway itself

The gateway overhead is ~5–20ms per request. The async architecture means hundreds of in-flight requests can be held simultaneously while waiting on upstream I/O.
"""
    },
    {
        "slug": "setup-guide",
        "title": "Deployment Setup Guide",
        "description": "How to deploy and configure a new Bonito instance from scratch.",
        "category": "Operations",
        "updated_at": "2026-02-17",
        "content": """# Bonito Deployment Setup Guide

## Prerequisites

- **Railway account** (or any Docker-compatible hosting)
- **PostgreSQL** database (Railway provides this)
- **Redis** instance (Railway provides this)
- **HashiCorp Vault** instance (for credential storage)

## Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/bonito` |
| `REDIS_URL` | Redis connection string | `redis://host:6379/0` |
| `VAULT_ADDR` | Vault server URL | `https://vault.example.com` |
| `VAULT_TOKEN` | Vault authentication token | `hvs.xxxxx` |
| `SECRET_KEY` | JWT signing key (or load from Vault) | Random 64-char string |
| `ENCRYPTION_KEY` | Data encryption key (or load from Vault) | Random 64-char string |
| `ADMIN_EMAILS` | Comma-separated platform admin emails | `admin@company.com,ops@company.com` |
| `ENVIRONMENT` | `development` or `production` | `production` |
| `CORS_ORIGINS` | Allowed frontend origins | `https://app.getbonito.com` |

## Step-by-Step Setup

### 1. Database Setup

```bash
# Railway creates PostgreSQL automatically, or provision manually:
createdb bonito

# Run migrations
cd backend
alembic upgrade head
```

### 2. Redis Setup

```bash
# Railway creates Redis automatically
# Or run locally:
redis-server
```

### 3. Vault Configuration

```bash
# Enable KV v2 secrets engine
vault secrets enable -path=secret kv-v2

# Store application secrets
vault kv put secret/app secret_key="your-jwt-secret" encryption_key="your-encryption-key"
vault kv put secret/api groq_api_key="your-groq-key"

# Per-org credentials are stored dynamically by the application at:
# secret/data/org/{org_id}/aws
# secret/data/org/{org_id}/azure
# secret/data/org/{org_id}/gcp
```

### 4. Railway Deployment

```bash
# Link to Railway project
railway link

# Deploy backend
cd backend
railway up

# Deploy frontend
cd frontend
railway up
```

### 5. Post-Deployment

1. Set `ADMIN_EMAILS` env var with platform admin email addresses
2. Register an account with one of those emails
3. Verify email and log in
4. Access the Admin Portal at `/admin/system`

## Backend Configuration

The backend uses a **secret loading chain**: Vault → Environment Variables → Dev Defaults.

In production (`ENVIRONMENT=production`), required secrets (`secret_key`, `encryption_key`) must be available from either Vault or env vars. In development, hardcoded defaults are used as a last resort.

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply all pending migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

Migrations run automatically in `start-prod.sh` before Uvicorn starts.

## Frontend Configuration

The frontend needs `NEXT_PUBLIC_API_URL` pointing to the backend:

```bash
NEXT_PUBLIC_API_URL=https://api.getbonito.com
```

## Health Check

```bash
curl https://api.getbonito.com/api/health
# → {"status": "healthy"}
```
"""
    },
    {
        "slug": "enterprise-sizing",
        "title": "Enterprise Sizing Guide",
        "description": "How to size Bonito infrastructure based on customer scale and requirements.",
        "category": "Operations",
        "updated_at": "2026-02-17",
        "content": """# Enterprise Sizing Guide

## Quick Reference

| Tier | Orgs | Request Volume | Instances | Workers/Instance | Redis | DB Pool |
|------|------|---------------|-----------|-----------------|-------|---------|
| **Small** | 1–10 | <100 req/min | 1 | 2 | Single connection | 10+20 overflow |
| **Medium** | 10–50 | <1,000 req/min | 2–3 | 4 each | Connection pool (20) | 10+10 per worker |
| **Large** | 50+ | 1,000+ req/min | Dedicated | 4–8 each | Cluster | Dedicated pool |

## Small Tier (1–10 orgs, <100 req/min)

**Infrastructure:**
- 1 Railway instance (512MB–1GB RAM)
- 2 Uvicorn async workers
- Shared PostgreSQL (Railway default)
- Single Redis connection

**Configuration:**
```env
WORKERS=2
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

**Cost estimate:** ~$20–50/mo (Railway Pro plan)

**Suitable for:** Early-stage startups, development teams, POC deployments.

## Medium Tier (10–50 orgs, <1,000 req/min)

**Infrastructure:**
- 2–3 Railway instances behind Railway's internal load balancer
- 4 workers per instance
- PostgreSQL with connection pooling (PgBouncer or Railway's built-in)
- Redis with connection pool (20 connections per instance)

**Configuration:**
```env
WORKERS=4
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
REDIS_POOL_SIZE=20
```

**Key changes from Small:**
- Move caches to Redis (router config, Azure AD tokens)
- Enable PgBouncer for connection multiplexing
- Set up monitoring and alerting
- Per-key rate limits: 300 req/min for Pro tier

**Cost estimate:** ~$100–300/mo

**Suitable for:** Growing SaaS with multiple active customers.

## Large Tier (50+ orgs or Enterprise)

**Infrastructure:**
- Dedicated instances per enterprise customer
- 4–8 workers per instance
- Dedicated PostgreSQL with tuned connection pools
- Redis cluster for cache and rate limiting
- Optional: VPC gateway deployment

**Configuration:**
```env
WORKERS=8
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
REDIS_POOL_SIZE=50
```

**Key changes from Medium:**
- Dedicated gateway instance per enterprise org
- Custom domain: `gateway.{customer}.getbonito.com`
- SLA-backed: guaranteed throughput and latency percentiles
- VPC Gateway option for data sovereignty
- Dedicated monitoring dashboards per customer
- Custom rate limits and routing policies

**Cost estimate:** $500–2,000+/mo per enterprise customer

**Suitable for:** Enterprise deployments with SLA requirements, data sovereignty needs, or high-throughput workloads.

## Capacity Planning Formula

```
Required instances ≈ ceil(peak_req_per_min / 500)
Workers per instance = min(8, available_cpu_cores × 2)
DB pool total = instances × workers × pool_size ≤ PG max_connections × 0.8
Redis connections = instances × workers × 2
```

## Monitoring Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| DB pool utilization | >70% | >90% |
| Request latency (p95) | >500ms gateway overhead | >2s gateway overhead |
| Error rate | >1% | >5% |
| Memory usage | >70% | >85% |
| Redis connection count | >80% of pool | >95% of pool |
"""
    },
    {
        "slug": "api-reference",
        "title": "Gateway API Reference",
        "description": "Quick reference for the OpenAI-compatible gateway API endpoints and authentication.",
        "category": "Reference",
        "updated_at": "2026-02-17",
        "content": """# Gateway API Reference

## Authentication

All gateway API requests require a `bn-` prefixed API key in the Authorization header:

```bash
Authorization: Bearer bn-xxxxxxxxxxxxxxxxxxxx
```

API keys are created in the Dashboard under **API Gateway → Keys**. Each key is:
- Scoped to a single organization
- Optionally restricted to specific models or providers
- Rate-limited (default: 100 req/min, configurable per key)
- Revocable at any time

Routing policy keys use `rt-` prefix and work the same way.

## Endpoints

### Chat Completions

```http
POST /v1/chat/completions
```

OpenAI-compatible chat completions. Supports streaming.

**Request:**
```json
{
  "model": "gpt-4o",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "temperature": 0.7,
  "max_tokens": 1000,
  "stream": false
}
```

**Response:**
```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "model": "gpt-4o",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "Hello! How can I help?"},
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 8,
    "total_tokens": 28
  }
}
```

**Streaming:** Set `"stream": true` to receive Server-Sent Events.

### Legacy Completions

```http
POST /v1/completions
```

Text completions (non-chat). Same auth, similar request format with `prompt` instead of `messages`.

### Embeddings

```http
POST /v1/embeddings
```

**Request:**
```json
{
  "model": "text-embedding-3-small",
  "input": "The quick brown fox"
}
```

**Response:**
```json
{
  "object": "list",
  "data": [{
    "object": "embedding",
    "index": 0,
    "embedding": [0.0023, -0.0091, ...]
  }],
  "model": "text-embedding-3-small",
  "usage": {"prompt_tokens": 5, "total_tokens": 5}
}
```

### List Models

```http
GET /v1/models
```

Returns all models available to the authenticated org. Respects key-level model restrictions.

**Response:**
```json
{
  "object": "list",
  "data": [
    {"id": "gpt-4o", "object": "model", "owned_by": "azure"},
    {"id": "claude-3-5-sonnet-20241022", "object": "model", "owned_by": "aws"},
    {"id": "gemini-1.5-pro", "object": "model", "owned_by": "gcp"}
  ]
}
```

## Supported Models

Models are dynamically available based on connected providers:

| Provider | Example Models |
|----------|---------------|
| **AWS Bedrock** | `anthropic.claude-3-5-sonnet-20241022-v2:0`, `amazon.nova-pro-v1:0`, `meta.llama3-3-70b-instruct-v1:0` |
| **Azure OpenAI** | `gpt-4o`, `gpt-4o-mini`, `o1`, `text-embedding-3-small` |
| **GCP Vertex AI** | `gemini-1.5-pro`, `gemini-1.5-flash`, `gemini-2.0-flash` |

## Error Codes

| Status | Meaning |
|--------|---------|
| `401` | Invalid or missing API key |
| `403` | Model not allowed by policy or key restrictions |
| `413` | Request body too large (>1MB) |
| `429` | Rate limit exceeded |
| `502` | Upstream provider error |

## Rate Limiting

Rate limits are enforced per API key:
- **Default**: 100 requests/minute
- **Custom**: Set per key via Dashboard
- Returns `429 Too Many Requests` when exceeded
- Rate limit headers included in response

## Cost Tracking

Every request logs:
- Input/output token counts
- Cost (calculated using LiteLLM's cost tables)
- Latency (gateway overhead + upstream)
- Model requested vs. model used (if fallback occurred)

View in Dashboard under **Analytics** or **API Gateway → Logs**.
"""
    },
    {
        "slug": "vpc-gateway-agent",
        "title": "VPC Gateway Agent — Enterprise Architecture",
        "description": "Complete spec for the Bonito Agent: unified API contract, control/data plane split, ingestion API, deployment options, security, and build timeline.",
        "category": "Architecture",
        "updated_at": "2026-02-17",
        "content": """# VPC Gateway Agent — Enterprise Architecture

## Core Principle: Unified API Contract

The frontend, dashboard, and all management APIs are **identical regardless of deployment mode.** Whether data comes from our shared gateway or a customer's VPC agent, it lands in the same Postgres tables via the same schema. The frontend never knows the difference.

```
Mode A — Shared Gateway (Free/Pro):
  Customer App → Bonito Gateway (Railway) → logs directly to Postgres
                                                    ↑
                                            Dashboard reads same tables

Mode B — VPC Agent (Enterprise):
  Customer App → Bonito Agent (VPC) → pushes metadata → /api/agent/ingest → same Postgres tables
                                                                                    ↑
                                                                            Dashboard reads same tables
```

Same `GatewayRequest` rows. Same `/api/gateway/usage` endpoint. Same costs page. Same analytics. Same alerts. **Zero frontend changes.**

---

## Architecture: Control Plane / Data Plane Split

The Bonito Agent is a lightweight container deployed into a customer's VPC. It handles the **data plane** (AI requests with prompts and responses) locally, while the **control plane** (policies, analytics, billing) stays on Bonito's SaaS infrastructure.

This is the same model used by Datadog (agent), Kong (Konnect data plane), HashiCorp (HCP), and Tailscale (node).

```
Customer VPC                                Bonito SaaS (Railway + Vercel)

┌────────────────────────────────┐          ┌────────────────────────────────┐
│                                │          │                                │
│  Customer Apps → Bonito Agent  │          │  getbonito.com (dashboard)     │
│                    │           │          │         │                      │
│     ┌──────────────┼───────┐   │          │  Railway API (control plane:   │
│     │ LiteLLM      │       │   │  config  │  policies, keys, analytics,   │
│     │ Proxy     Config     │   │←────────→│  billing)                      │
│     │            Sync      │   │ + metrics │                               │
│     │ Metrics   Health     │   │          │  Postgres (same tables,        │
│     │ Reporter  Reporter   │   │          │  same schema as shared GW)     │
│     └──────────────────────┘   │          │                                │
│                    │           │          └────────────────────────────────┘
│     ┌──────────────┼───────┐   │
│     │ Customer's Cloud     │   │          Frontend (Vercel) has ZERO
│     │ ├── AWS Bedrock      │   │          awareness of shared vs VPC mode.
│     │ ├── Azure OpenAI     │   │          All pages read from the same
│     │ └── GCP Vertex AI    │   │          APIs, same tables.
│     └──────────────────────┘   │
│                                │
│     Customer Secrets Manager   │
│     (credentials stay local)   │
│                                │
└────────────────────────────────┘
```

---

## What Stays in VPC vs. What Syncs

### Data Plane — Stays in VPC

| Data | Where it lives | Never leaves VPC |
|------|---------------|-----------------|
| Prompts & responses | Customer app ↔ Agent ↔ Cloud provider | ✅ |
| Cloud credentials | Customer's secrets manager (AWS SM / Azure KV / GCP SM) | ✅ |
| Request/response payloads | In-memory during processing | ✅ |
| Model inference | Customer's cloud account | ✅ |

### Control Plane — Syncs to Bonito

| Data | Direction | Frequency | Format |
|------|-----------|-----------|--------|
| Usage metrics | Agent → Railway | Every 10s (batched) | `GatewayRequest` schema (no content) |
| Agent health | Agent → Railway | Every 60s | Heartbeat: uptime, version, providers |
| Policies | Railway → Agent | Agent pulls every 30s | Model allow-lists, spend caps, rate limits |
| API key registry | Railway → Agent | Agent pulls every 30s | Key hashes for local authentication |
| Routing policies | Railway → Agent | Agent pulls every 30s | Failover chains, A/B weights, strategies |
| Gateway config | Railway → Agent | Agent pulls every 30s | Enabled providers, default settings |

### Metrics Payload Per Request

Identical to what the shared gateway writes to `gateway_requests`:

```json
{
  "model_requested": "gpt-4o",
  "model_used": "gpt-4o",
  "input_tokens": 500,
  "output_tokens": 200,
  "cost": 0.0035,
  "latency_ms": 1200,
  "status": "success",
  "key_id": "uuid",
  "provider": "azure",
  "timestamp": "2026-02-17T11:20:00Z"
}
```

No prompts. No responses. Just the numbers our dashboard already expects.

---

## How Every Dashboard Feature Works

| Feature | Shared Gateway (today) | VPC Agent (enterprise) | Frontend change? |
|---------|----------------------|----------------------|-----------------|
| **Costs page** | Reads `gateway_requests` directly | Same — agent pushes to same table | None |
| **Analytics** | Reads `gateway_requests` directly | Same — agent pushes to same table | None |
| **Gateway logs** | Reads `gateway_requests` directly | Same — agent pushes to same table | None |
| **Alerts / spend caps** | Control plane checks DB | Same — data came from agent push | None |
| **Policies** | Enforced in gateway process | Synced to agent, enforced locally | None |
| **Routing policies** | Applied in gateway process | Synced to agent, applied locally | None |
| **API key management** | Keys validated in gateway | Key hashes synced to agent for local validation | None |
| **Team management** | Control plane only | Control plane only | None |
| **Model catalog** | Synced from cloud APIs | Agent reports available models | None |
| **Audit logs** | Logged in gateway | Agent pushes audit events | None |
| **Governance** | Enforced in gateway | Synced + enforced locally by agent | None |
| **Playground** | Routes through our gateway | ⚠️ Routes through Bonito infra (with note) | Minor UX note |

---

## Bonito Agent — Technical Specification

**Container image**: `ghcr.io/bonito/gateway-agent:latest` (~50-100MB)

```
bonito-gateway-agent
├── LiteLLM Proxy (data plane)
│   ├── OpenAI-compatible API (/v1/chat/completions, /v1/embeddings, etc.)
│   ├── Model routing: failover, cost-optimized, A/B test, round-robin
│   ├── Rate limiting (in-memory or local Redis)
│   ├── Policy enforcement (cached from control plane)
│   └── Credential loading (from customer's secrets manager)
│
├── Config Sync Daemon (control plane client)
│   ├── GET /api/agent/config — pulls every 30s
│   │   ├── Active policies (model access, spend caps)
│   │   ├── API key hashes (for local authentication)
│   │   ├── Routing policies (strategies, model priorities)
│   │   └── Gateway config (enabled providers, defaults)
│   ├── Diffing — only applies changes, no full reload
│   ├── Local cache — works offline with last-known config
│   └── Hot-reload — zero-downtime config updates
│
├── Metrics Reporter (telemetry)
│   ├── POST /api/agent/ingest — batches every 10s
│   ├── Writes to same GatewayRequest schema
│   ├── Retry queue — buffers if control plane unreachable
│   └── Compression — gzip payloads for bandwidth efficiency
│
└── Health Reporter
    ├── POST /api/agent/heartbeat — every 60s
    ├── Reports: uptime, version, request count, error rate
    ├── Connected providers and their health
    └── Control plane alerts admin if heartbeat missed >5 min
```

**NOT included in agent** (stays on control plane):
- PostgreSQL database
- HashiCorp Vault
- Frontend / dashboard
- User authentication (JWT, sessions)
- Email service (Resend)
- Notification system

---

## Stateless Agent — No Database Required

The agent is **completely stateless**. It has no database, no persistent storage, and no disk dependencies. Everything is held in memory.

```
Agent (customer's VPC)                 Bonito Control Plane (Railway)

┌───────────────────────┐              ┌──────────────────────────┐
│  In-memory only:      │  push every  │  Postgres (OUR database) │
│  - Config cache       │───10s───────→│  gateway_requests table  │
│  - API key hashes     │  metrics     │  (single source of truth)│
│  - Rate limit counters│              │                          │
│  - Metrics retry queue│  pull every  │  policies, routing rules,│
│  (no DB, no disk)     │←──30s────────│  gateway_keys, configs   │
└───────────────────────┘  config      └──────────────────────────┘
```

| Data | Where it lives | Why there |
|------|---------------|-----------|
| Usage metrics / logs | **Our Postgres** (Railway) | Agent pushes metadata, we store it. Dashboard reads from here. |
| Policies, keys, config | **Our Postgres** (Railway) | Source of truth. Agent caches in-memory. |
| Rate limit counters | **Agent memory** | Ephemeral. Resets on restart. Acceptable. |
| Metrics retry buffer | **Agent memory** | Queues up to 1 hour if control plane unreachable. Lost on crash. |

**Why no database on the customer's side:**
- **Simpler deployment** — one container, zero dependencies to manage
- **No migrations, no backups, no schema upgrades** on their infrastructure
- **Single source of truth** — our DB, no sync conflicts or split-brain
- **Agent crashes? Just restart it.** Nothing to recover, no corruption risk.

**Trade-off:** If the agent crashes while holding buffered metrics, that window (~10s of request data) is lost. This means a small gap in analytics charts — not a functional failure. The data plane continues serving requests immediately on restart since LiteLLM is also stateless.

**Future option:** If a customer requires local data retention (e.g., compliance, audit trail), the agent can optionally write to their own DB as a secondary sink. This is an add-on, not a requirement for the platform to function.

---

## Authentication Model

Three token types, clear separation of concerns:

| Token | Prefix | Who uses it | Purpose |
|-------|--------|------------|---------|
| **User API key** | `bn-` | Customer's apps → Agent | Authenticate AI requests |
| **Routing policy key** | `rt-` | Customer's apps → Agent | Route via specific policy |
| **Org token** | `bt-` | Agent → Control plane | Config sync, metrics push, heartbeat |

### Org Token Provisioning Flow

1. Enterprise customer enables "VPC Mode" in dashboard settings
2. Control plane generates `bt-xxxxx` org token
3. Admin copies token into their agent deployment config
4. Agent uses token for all control plane communication
5. Token can be rotated from dashboard without redeploying agent

### Customer App Migration

SDK-compatible — just change the base URL, same key, same API:

```python
# Before (shared gateway):
client = OpenAI(base_url="https://api.getbonito.com/v1", api_key="bn-xxx")

# After (VPC agent) — same key, same API:
client = OpenAI(base_url="http://bonito-agent.internal:8000/v1", api_key="bn-xxx")
```

---

## Backend Changes Required

### New API Endpoints (Railway backend)

```
# Agent-facing endpoints (authenticated via bt- org token)
POST /api/agent/ingest          ← Receive batched metrics from agent
GET  /api/agent/config          → Serve current config snapshot for agent
POST /api/agent/heartbeat       ← Receive agent health status
GET  /api/agent/keys            → Serve API key hashes for local validation

# Dashboard endpoints (new)
GET  /api/admin/agents          ← List all VPC agents across orgs
GET  /api/orgs/{id}/agent       ← Agent status for specific org
POST /api/orgs/{id}/agent/token ← Generate/rotate org token
```

### Agent Ingestion Service

```python
async def ingest_metrics(org_id, batch, db):
    # Write agent-pushed metrics into the SAME GatewayRequest table.
    # Identical schema to what the shared gateway writes directly.
    # Dashboard/analytics/costs pages read from this table
    # regardless of source.
    for record in batch:
        entry = GatewayRequest(
            org_id=org_id,
            key_id=record.get("key_id"),
            model_requested=record["model_requested"],
            model_used=record["model_used"],
            input_tokens=record["input_tokens"],
            output_tokens=record["output_tokens"],
            cost=record["cost"],
            latency_ms=record["latency_ms"],
            status=record["status"],
            provider=record.get("provider"),
            source="vpc_agent",  # distinguishes origin for admin visibility
        )
        db.add(entry)
```

### Database Change

One new column (one migration):
```sql
ALTER TABLE gateway_requests ADD COLUMN source VARCHAR(20) DEFAULT 'shared_gateway';
-- Values: 'shared_gateway' | 'vpc_agent'
-- Used for admin visibility only; dashboard queries don't filter on it
```

---

## Deployment Options

### Option A: Docker Compose (Small Teams)

```yaml
version: "3.8"
services:
  bonito-agent:
    image: ghcr.io/bonito/gateway-agent:latest
    environment:
      BONITO_CONTROL_PLANE: https://api.getbonito.com
      BONITO_ORG_TOKEN: bt-xxxxx
      AWS_SECRETS_MANAGER_ARN: arn:aws:secretsmanager:us-east-1:123:secret:bonito
      AZURE_KEY_VAULT_URL: https://myvault.vault.azure.net
      GCP_SECRET_NAME: projects/123/secrets/bonito-gcp
    ports:
      - "8000:8000"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
```

### Option B: Kubernetes / Helm (Production, HA)

```bash
helm repo add bonito https://charts.getbonito.com
helm install bonito-gateway bonito/gateway-agent \\
  --set controlPlane.url=https://api.getbonito.com \\
  --set controlPlane.token=bt-xxxxx \\
  --set replicas=3 \\
  --set resources.requests.memory=256Mi \\
  --set resources.limits.memory=512Mi \\
  --namespace bonito
```

### Option C: Terraform (IaC, Full Automation)

**AWS ECS/Fargate:**
```hcl
module "bonito_gateway" {
  source              = "bonito/gateway-agent/aws"
  version             = "~> 1.0"
  vpc_id              = var.vpc_id
  subnet_ids          = var.private_subnet_ids
  org_token           = var.bonito_org_token
  desired_count       = 2
  cpu                 = 512
  memory              = 1024
  secrets_manager_arn = var.credentials_secret_arn
}
```

**Azure Container Apps:**
```hcl
module "bonito_gateway" {
  source            = "bonito/gateway-agent/azure"
  version           = "~> 1.0"
  resource_group    = var.resource_group_name
  vnet_id           = var.vnet_id
  subnet_id         = var.container_apps_subnet_id
  org_token         = var.bonito_org_token
  key_vault_url     = var.key_vault_url
  min_replicas      = 2
  max_replicas      = 5
}
```

**GCP Cloud Run:**
```hcl
module "bonito_gateway" {
  source         = "bonito/gateway-agent/gcp"
  version        = "~> 1.0"
  project_id     = var.project_id
  region         = "us-central1"
  vpc_connector  = var.vpc_connector_name
  org_token      = var.bonito_org_token
  min_instances  = 2
  max_instances  = 10
}
```

---

## Dashboard Integration

### New UI Elements (added to existing dashboard)

1. **Settings → Deployment Mode toggle**
   - "Shared Gateway" (default) vs "VPC Agent"
   - Enabling VPC mode generates the `bt-` org token
   - Shows deployment instructions (Docker/Helm/Terraform snippets)

2. **Agent Status indicator** (header bar when VPC mode is on)
   - 🟢 Agent connected (last heartbeat <2 min ago)
   - 🟡 Agent delayed (last heartbeat 2-5 min ago)
   - 🔴 Agent offline (last heartbeat >5 min ago, alert sent)

3. **Admin → Agents page** (platform admin only)
   - List all VPC agents across all orgs
   - Health status, version, uptime, request rate
   - Per-agent config sync status

4. **Analytics page** — no changes needed
   - Optional: add "Source" filter (Shared Gateway / VPC Agent) for admin visibility

---

## Graceful Degradation

| Failure | Agent behavior | Control plane behavior |
|---------|---------------|----------------------|
| Control plane unreachable | Continue serving with last-known config. Queue metrics for retry (up to 1 hour buffer). | Show agent as "delayed" then "offline". Alert admin. |
| Customer's cloud provider down | LiteLLM failover to next provider (if configured). Return 502 if all fail. | Show elevated error rate in analytics. |
| Agent crash / OOM | Container orchestrator restarts automatically. Metrics gap during downtime. | Show gap in analytics timeline. Alert admin. |
| Credentials expired | Agent detects 401 from cloud provider. Re-reads from secrets manager. Logs error if refresh fails. | Error rate spike visible in dashboard. |
| Config sync conflict | Agent always takes latest from control plane (last-write-wins). | N/A — control plane is source of truth. |

---

## Security Considerations

- **Outbound only**: Agent initiates all connections. No inbound ports required from internet.
- **mTLS optional**: Agent ↔ control plane can use mutual TLS for additional assurance.
- **Org token rotation**: Rotatable from dashboard without redeploying agent (agent picks up new token on next sync).
- **No data exfiltration**: Agent code is open for customer audit. Only metadata (counts, costs) leaves VPC.
- **Network policies**: Agent only needs outbound to: (1) Bonito control plane, (2) Cloud AI endpoints. Everything else blocked.
- **Container signing**: Agent images signed with cosign for supply chain integrity.

---

## Build Timeline

| Week | Deliverable | Details |
|------|------------|---------|
| **1** | Gateway service split | Refactor gateway into shared core + full_mode (Railway) + agent_mode (VPC). Config sync protocol spec. Agent Dockerfile. |
| **2** | Agent container + ingestion API | Working agent image. /api/agent/ingest, /api/agent/config, /api/agent/heartbeat. Org token (bt-) auth. E2E test: agent → control plane → dashboard shows data. |
| **3** | Terraform modules + Helm chart | AWS ECS, Azure Container Apps, GCP Cloud Run modules. Helm chart. CI/CD for agent image builds. |
| **4** | Dashboard integration + polish | VPC mode toggle. Agent status indicator. Admin agents page. In-app deployment instructions. Customer onboarding runbook. |

**Pricing:** Enterprise tier $2K-$5K/mo base + usage
"""
    },
]


def get_all_articles() -> list[dict]:
    """Return all KB articles (without full content for listing)."""
    return [
        {
            "slug": a["slug"],
            "title": a["title"],
            "description": a["description"],
            "category": a["category"],
            "updated_at": a["updated_at"],
        }
        for a in KB_ARTICLES
    ]


def get_article_by_slug(slug: str) -> dict | None:
    """Return a single KB article by slug, or None."""
    for a in KB_ARTICLES:
        if a["slug"] == slug:
            return a
    return None


# ---------------------------------------------------------------------------
# Vector KB search (used by Bonobot agent engine)
# ---------------------------------------------------------------------------
import uuid
import logging
from typing import List, Dict, Any, Optional

from sqlalchemy import text as sa_text, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

_kb_logger = logging.getLogger(__name__)


async def search_knowledge_base(
    kb_id: uuid.UUID,
    query: str,
    limit: int = 5,
    similarity_threshold: float = 0.5,
    org_id: uuid.UUID = None,
    db: AsyncSession = None,
) -> List[Dict[str, Any]]:
    """
    Semantic search over a pgvector-backed knowledge base.

    Returns a list of dicts with keys: content, source_name, score, chunk_index.
    """
    from app.models.knowledge_base import KnowledgeBase, KBChunk
    from app.services.kb_ingestion import EmbeddingGenerator

    if db is None:
        return []

    # Verify the KB exists and belongs to the org
    if org_id:
        kb_result = await db.execute(
            select(KnowledgeBase).where(
                and_(KnowledgeBase.id == kb_id, KnowledgeBase.org_id == org_id)
            )
        )
    else:
        kb_result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
    kb = kb_result.scalar_one_or_none()
    if not kb:
        _kb_logger.warning(f"Knowledge base {kb_id} not found")
        return []

    # Generate embedding for the query using the SAME model as ingestion
    embedding_gen = EmbeddingGenerator(org_id or kb.org_id)
    # Use the KB's configured embedding model to avoid dimension mismatch
    kb_embedding_model = getattr(kb, 'embedding_model', None)
    if kb_embedding_model and kb_embedding_model != 'auto':
        embed_model = kb_embedding_model
    else:
        embed_model = None  # auto-detect
    try:
        embed_dims = getattr(kb, 'embedding_dimensions', None)
        query_embeddings = await embedding_gen.generate_embeddings([query], model=embed_model, dimensions=embed_dims)
        if not query_embeddings:
            _kb_logger.error("Failed to generate query embedding")
            return []
        query_embedding = query_embeddings[0]
    except Exception as e:
        _kb_logger.error(f"Embedding generation failed: {e}")
        return []

    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    try:
        result = await db.execute(
            sa_text("""
                SELECT c.content, c.source_file, c.chunk_index,
                       1 - (c.embedding <=> CAST(:query_vec AS vector)) AS score
                FROM kb_chunks c
                WHERE c.knowledge_base_id = :kb_id
                  AND c.org_id = :org_id
                  AND c.embedding IS NOT NULL
                ORDER BY c.embedding <=> CAST(:query_vec AS vector)
                LIMIT :top_k
            """),
            {
                "query_vec": embedding_str,
                "kb_id": str(kb_id),
                "org_id": str(org_id or kb.org_id),
                "top_k": limit,
            },
        )
        rows = result.fetchall()
    except Exception as e:
        _kb_logger.error(f"Vector search failed for KB {kb_id}: {e}")
        return []

    results: List[Dict[str, Any]] = []
    for row in rows:
        score = float(row.score) if row.score else 0.0
        if score < similarity_threshold:
            continue
        results.append({
            "content": row.content,
            "source_name": row.source_file or "unknown",
            "score": score,
            "chunk_index": row.chunk_index,
        })

    return results
