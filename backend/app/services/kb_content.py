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
Gateway runs in customer's own cloud — data never leaves their network:

```
┌─── Customer VPC ─────────────────────────────┐
│  Customer App → Bonito Gateway Agent          │
│                      ├── AWS Bedrock          │
│                      ├── Azure OpenAI         │
│                      └── GCP Vertex           │
│                 Config sync (outbound only)    │
└──────────────────────│────────────────────────┘
                       ↓
              Bonito Control Plane (SaaS)
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
