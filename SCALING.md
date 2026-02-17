# Bonito Gateway — Scaling & Architecture Assessment

_Last updated: 2026-02-17_

## Current Architecture (What's Live)

### Single Multi-Tenant Gateway
```
Customer App → Bonito Gateway (Railway) → Customer's Cloud (Bedrock/Azure/Vertex)
                    │
                    ├── FastAPI + Uvicorn (2 async workers)
                    ├── LiteLLM Router (in-memory, per-worker, per-org)
                    ├── PostgreSQL (Railway, connection pool 10+20 per worker)
                    ├── Redis (rate limiting, single connection)
                    └── Vault (credential storage, HTTP calls)
```

**One Railway instance. All orgs share it.** Per-org isolation is logical (separate Vault credentials, separate LiteLLM Router instances cached in memory, separate API keys/policies), not physical.

### Request Flow
1. Customer app sends `POST /v1/chat/completions` with `bn-...` API key
2. Gateway authenticates key → resolves `org_id` (DB query)
3. Policy enforcement: model allow-list, spend cap, org restrictions (DB queries)
4. Build/retrieve LiteLLM Router for org (Vault fetch on cache miss, 50 min TTL)
5. LiteLLM proxies request to customer's own cloud deployment
6. Response streams back, cost/tokens logged to DB
7. Total gateway overhead: ~5-20ms (excluding upstream latency)

---

## Throughput — Honest Assessment

### What the current setup can handle

| Metric | Value | Notes |
|--------|-------|-------|
| Uvicorn workers | 2 (async) | `start-prod.sh` default |
| Concurrent connections (theoretical) | ~200-500 | Async I/O, not thread-bound |
| DB connection pool | 30 per worker (60 total) | 10 base + 20 overflow |
| Redis connections | 1 (no pool) | Single `redis.from_url()` |
| Per-key rate limit | 100 req/min default | ~1.7 req/s sustained per key |
| Global rate limit | 100 req/60s per IP | Dashboard API tier |

### The real bottleneck: upstream latency

The gateway itself is lightweight — it's an async proxy. The actual latency is:
- **AWS Bedrock**: 500ms - 15s (depends on model/tokens)
- **Azure OpenAI**: 300ms - 20s
- **GCP Vertex**: 400ms - 15s

Each request holds an async task (not a thread) while waiting for upstream. With 2 workers and asyncio, we can have **hundreds of in-flight requests** simultaneously because they're just waiting on I/O.

### Where it breaks

| Bottleneck | Threshold | What happens |
|-----------|-----------|-------------|
| DB connection pool | >60 concurrent DB operations | Requests queue on `pool_timeout` (30s), then 500 |
| Redis (single conn) | High concurrent rate-limit checks | Serialized; degrades gracefully (fail-open) |
| Router cache (in-memory) | Many orgs × 2 workers | Memory grows; each worker builds its own cache |
| Vault fetches | Router cache miss burst | HTTP calls to Vault stack up |
| Railway container | Memory/CPU limits | OOM kill or CPU throttle |

### Realistic capacity estimate

For a **single Railway instance** (likely 512MB-1GB RAM, shared vCPU):

| Scenario | Sustainable? | Notes |
|----------|-------------|-------|
| 1-5 orgs, light usage (<10 req/min each) | ✅ Easy | Current state, no issues |
| 10-20 orgs, moderate (50 req/min each) | ⚠️ Tight | DB pool and memory pressure |
| 50+ orgs or any org at >100 req/min | ❌ No | Need horizontal scaling |
| Single enterprise client, 1000 req/min | ❌ No | DB pool exhaustion, need dedicated infra |

**Bottom line: Current setup handles early customers fine. It does NOT handle enterprise-grade load from a single large client doing hundreds of req/s.**

---

## Known Architecture Issues

### 1. In-Memory Router Cache is Per-Worker
```python
_routers: dict[uuid.UUID, tuple[litellm.Router, float]] = {}
```
Each Uvicorn worker has its own `_routers` dict. With 2 workers:
- 2x memory usage for cached routers
- Cache miss on one worker even if another just built it
- No shared state between workers

**Fix:** Move to Redis-backed router config, or accept the duplication (it's small per org).

### 2. Redis Has No Connection Pool
```python
redis_client = redis.from_url(settings.redis_url, decode_responses=True)
```
Single connection, shared across all async tasks in a worker. Under high concurrency, rate-limit checks serialize.

**Fix:** Use `redis.ConnectionPool` with `max_connections`.

### 3. Azure AD Token Cache is Per-Worker
```python
_azure_ad_cache: dict[str, tuple[str, float]] = {}
```
Same issue as router cache — each worker refreshes independently.

**Fix:** Cache in Redis with TTL matching token expiry.

### 4. No Horizontal Scaling Path
- Single Railway instance, no load balancer
- No sticky sessions needed (stateless per-request), but shared caches would need Redis
- No auto-scaling configured

### 5. DB Pool Sizing
- 10 + 20 overflow = 30 per worker × 2 workers = 60 total connections
- Railway Postgres likely has a connection limit (~100-200)
- With 4+ workers or multiple replicas, pool exhaustion is real

---

## Scaling Roadmap

### Phase S1: Quick Wins (Now → Pre-Launch Polish)
_No architecture changes, just config tuning._

- [ ] **Increase workers**: `WORKERS=4` in Railway env vars (Dockerfile already supports it)
- [ ] **Redis connection pool**: Replace single connection with pooled client
  ```python
  pool = redis.ConnectionPool.from_url(url, max_connections=20)
  redis_client = redis.Redis(connection_pool=pool)
  ```
- [ ] **DB pool tuning**: Reduce `pool_size` per worker if increasing workers (total = workers × pool_size must stay under Postgres limit)
- [ ] **Vault credential caching**: Add Redis-backed cache layer so Vault isn't hit on every router rebuild
- [ ] **Rate limit tuning**: Per-key defaults appropriate for tier (Free: 30/min, Pro: 300/min, Enterprise: custom)

### Phase S2: Horizontal Scaling (When first paying customer arrives)
_Multiple gateway instances behind a load balancer._

- [ ] **Railway replicas**: Scale to 2-3 instances (Railway supports this)
- [ ] **Move caches to Redis**: Router config, Azure AD tokens, Vault credentials
- [ ] **Shared-nothing workers**: Each instance is stateless, all state in Redis/Postgres
- [ ] **Health check endpoint**: Already have `/api/health` — ensure LB uses it
- [ ] **Sticky sessions**: Not needed (every request is self-contained with API key auth)

Architecture becomes:
```
Customer App → Railway Load Balancer → Instance 1 ─┐
                                     → Instance 2 ─┤→ Customer's Cloud
                                     → Instance N ─┘
                                           │
                                    Redis (shared state)
                                    Postgres (shared DB)
                                    Vault (shared secrets)
```

### Phase S3: Dedicated Gateway (Enterprise tier)
_Per-customer gateway for isolation and performance guarantees._

- [ ] **Dedicated Railway instance per enterprise org**: Separate container, own resource limits
- [ ] **Custom domain**: `gateway.{customer}.getbonito.com`
- [ ] **Dedicated DB pool**: Isolated connection pool, own rate limits
- [ ] **SLA-backed**: Guaranteed throughput, latency percentiles
- [ ] **Still managed by Bonito**: We deploy/monitor/update it

### Phase S4: VPC Gateway (Enterprise+ tier)
_Gateway runs in customer's own cloud. Data never leaves their network._

- [ ] **Terraform module**: One-click deploy gateway into customer's AWS/Azure/GCP VPC
- [ ] **Control plane connection**: Gateway phones home to Bonito for config/policies/analytics
- [ ] **Data plane isolation**: AI requests go directly from customer VPC → cloud provider, never through Bonito
- [ ] **Architecture**: Like Kong/Istio — management plane (SaaS) + data plane (customer-hosted)

```
┌─── Customer VPC ──────────────────────────┐
│  Customer App → Bonito Gateway Agent      │
│                      │                     │
│                      ├── AWS Bedrock       │
│                      ├── Azure OpenAI      │
│                      └── GCP Vertex        │
│                      │                     │
│                 Config sync (outbound)     │
└──────────────────────│─────────────────────┘
                       ↓
              Bonito Control Plane (SaaS)
              - Policy management
              - Analytics aggregation
              - Billing & metering
```

**Pricing justification**: VPC Gateway = $2K-$5K/mo because customer gets data sovereignty + dedicated resources + SLA.

---

## What Competitors Do

| | Architecture | Multi-tenant? | VPC Option? |
|---|---|---|---|
| **LiteLLM** | Self-hosted proxy (user deploys) | N/A — user runs it | User's responsibility |
| **Portkey** | SaaS gateway (shared) | Yes | No |
| **Helicone** | SaaS logging proxy | Yes | No |
| **Cloudflare AI GW** | Edge network (CF infra) | Yes | No (CF network) |
| **Kong AI Gateway** | Self-hosted or Konnect (SaaS) | Both | Yes (self-hosted) |

**Bonito's path**: Start shared (like Portkey) → offer dedicated/VPC (like Kong). Best of both worlds.

---

## Action Items (Priority Order)

1. **Now**: Redis connection pool + increase workers to 4
2. **Before first paying customer**: Horizontal scaling (2-3 Railway instances)
3. **Enterprise sales conversations**: Have VPC Gateway architecture ready to discuss
4. **When enterprise signs**: Build dedicated gateway deployment pipeline
5. **When data sovereignty is required**: VPC Gateway Terraform module

---

_This is a living doc. Update as architecture evolves._
