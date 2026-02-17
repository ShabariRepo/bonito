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

---

#### Core Principle: Unified API Contract

**The frontend, dashboard, and all management APIs are identical regardless of deployment mode.** Whether data comes from our shared gateway or a customer's VPC agent, it lands in the same Postgres tables via the same schema. The frontend never knows the difference.

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

#### Architecture: Control Plane / Data Plane Split

```
┌─── Customer VPC ─────────────────────────────────────────────────┐
│                                                                   │
│  ┌─────────────┐     ┌──────────────────────────────────────┐    │
│  │ Customer App │────→│ Bonito Agent                         │    │
│  │ (their code) │     │                                      │    │
│  └─────────────┘     │  ┌─────────────┐  ┌───────────────┐  │    │
│                       │  │ LiteLLM     │  │ Config Sync   │  │    │
│  ┌─────────────┐     │  │ Proxy       │  │ Daemon        │  │    │
│  │ Customer App │────→│  │ - routing   │  │ - pulls every │  │    │
│  │ (their code) │     │  │ - failover  │  │   30s         │  │    │
│  └─────────────┘     │  │ - rate limit │  │ - hot-reload  │  │    │
│                       │  └──────┬──────┘  └───────┬───────┘  │    │
│                       │         │                  │          │    │
│                       │  ┌──────┴──────┐  ┌───────┴───────┐  │    │
│                       │  │ Metrics     │  │ Health        │  │    │
│                       │  │ Reporter    │  │ Reporter      │  │    │
│                       │  │ - batches   │  │ - heartbeat   │  │    │
│                       │  │   every 10s │  │   every 60s   │  │    │
│                       │  └──────┬──────┘  └───────┬───────┘  │    │
│                       └─────────┼─────────────────┼──────────┘    │
│                                 │                 │               │
│     ┌───────────────────┐       │                 │               │
│     │ Customer's Cloud  │       │                 │               │
│     │ ├── AWS Bedrock   │◄──────┤ DATA PLANE      │               │
│     │ ├── Azure OpenAI  │  (stays in VPC)         │               │
│     │ └── GCP Vertex AI │       │                 │               │
│     └───────────────────┘       │                 │               │
│                                 │                 │               │
│     ┌───────────────────┐       │                 │               │
│     │ Customer Secrets  │       │                 │               │
│     │ Manager           │◄──────┘                 │               │
│     │ (AWS SM / AZ KV / │  credentials            │               │
│     │  GCP SM)          │  stay local              │               │
│     └───────────────────┘                         │               │
└─────────────────────────────────┼─────────────────┼───────────────┘
                                  │                 │
                          outbound HTTPS only (443)
                                  │                 │
┌─────────────────────────────────┼─────────────────┼───────────────┐
│              Bonito Control Plane (Railway)        │               │
│                                 │                 │               │
│  ┌──────────────────────────────┴─────────────────┴────────────┐  │
│  │ Agent Ingestion API                                          │  │
│  │                                                              │  │
│  │  POST /api/agent/ingest     ← metrics (token counts, cost,  │  │
│  │                                latency, model, status)       │  │
│  │  GET  /api/agent/config     → policies, keys, routing rules  │  │
│  │  POST /api/agent/heartbeat  ← agent health, version, uptime │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                 │                                  │
│  ┌──────────────────────────────┴──────────────────────────────┐  │
│  │ Postgres (same tables, same schema)                          │  │
│  │                                                              │  │
│  │  gateway_requests  ← identical rows from shared GW or agent  │  │
│  │  gateway_keys      ← synced to agent for local auth          │  │
│  │  policies          ← synced to agent for local enforcement   │  │
│  │  routing_policies  ← synced to agent for local routing       │  │
│  │  gateway_configs   ← synced to agent for provider settings   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                 ↑                                  │
│  ┌──────────────────────────────┴──────────────────────────────┐  │
│  │ Existing Dashboard APIs (unchanged)                          │  │
│  │                                                              │  │
│  │  GET /api/gateway/usage     → reads gateway_requests table   │  │
│  │  GET /api/gateway/logs      → reads gateway_requests table   │  │
│  │  GET /api/gateway/keys      → reads gateway_keys table       │  │
│  │  PUT /api/gateway/config    → writes config, syncs to agent  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                 ↑                                  │
└─────────────────────────────────┼──────────────────────────────────┘
                                  │
┌─────────────────────────────────┼──────────────────────────────────┐
│              getbonito.com (Vercel) — NO CHANGES                   │
│                                 │                                  │
│  Dashboard, Analytics, Costs, Governance, Team, Alerts             │
│  All pages read from the same APIs, same tables                    │
│  Frontend has ZERO awareness of shared vs VPC mode                 │
└────────────────────────────────────────────────────────────────────┘
```

---

#### What Stays in VPC (Data Plane)

| Data | Where it lives | Never leaves VPC |
|------|---------------|-----------------|
| Prompts & responses | Customer app ↔ Agent ↔ Cloud provider | ✅ |
| Cloud credentials | Customer's secrets manager | ✅ |
| Request/response payloads | In-memory during processing | ✅ |
| Model inference | Customer's cloud account | ✅ |

#### What Syncs to Control Plane

| Data | Direction | Frequency | Format |
|------|-----------|-----------|--------|
| Usage metrics | Agent → Railway | Every 10s (batched) | `GatewayRequest` schema (no content) |
| Agent health | Agent → Railway | Every 60s | Heartbeat: uptime, version, connected providers |
| Policies | Railway → Agent | Agent pulls every 30s | Model allow-lists, spend caps, rate limits |
| API key registry | Railway → Agent | Agent pulls every 30s | Key hashes for local authentication |
| Routing policies | Railway → Agent | Agent pulls every 30s | Failover chains, A/B weights, strategies |
| Gateway config | Railway → Agent | Agent pulls every 30s | Enabled providers, default settings |

**Metrics payload per request** (identical to shared gateway's `GatewayRequest` row):
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

#### How Every Dashboard Feature Works with VPC Agent

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
| **Playground** | Routes through our gateway | ⚠️ Routes through our infra (with note) | Minor UX note |
| **Audit logs** | Logged in gateway | Agent pushes audit events | None |
| **Governance** | Enforced in gateway | Synced + enforced locally by agent | None |

---

#### Bonito Agent — Technical Specification

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

#### Authentication Model

Three token types, clear separation of concerns:

| Token | Prefix | Who uses it | Purpose |
|-------|--------|------------|---------|
| **User API key** | `bn-` | Customer's apps → Agent | Authenticate AI requests |
| **Routing policy key** | `rt-` | Customer's apps → Agent | Route via specific policy |
| **Org token** | `bt-` | Agent → Control plane | Config sync, metrics push, heartbeat |

**Org token provisioning flow:**
1. Enterprise customer enables "VPC Mode" in dashboard settings
2. Control plane generates `bt-xxxxx` org token
3. Admin copies token into their agent deployment config
4. Agent uses token for all control plane communication
5. Token can be rotated from dashboard without redeploying agent

**Customer app migration** — SDK-compatible, just change base URL:
```python
# Before (shared gateway):
client = OpenAI(base_url="https://api.getbonito.com/v1", api_key="bn-xxx")

# After (VPC agent) — same key, same API, just a URL change:
client = OpenAI(base_url="http://bonito-agent.internal:8000/v1", api_key="bn-xxx")
```

---

#### Backend Changes Required

**New API endpoints** (added to Railway backend):

```python
# Agent-facing endpoints (authenticated via bt- org token)
POST /api/agent/ingest          # Receive batched metrics from agent
GET  /api/agent/config          # Serve current config snapshot for agent
POST /api/agent/heartbeat       # Receive agent health status
GET  /api/agent/keys            # Serve API key hashes for local validation

# Dashboard endpoints (new)
GET  /api/admin/agents          # List all VPC agents across orgs
GET  /api/orgs/{id}/agent       # Agent status for specific org
POST /api/orgs/{id}/agent/token # Generate/rotate org token
```

**Agent ingestion service** (`app/services/agent_ingest.py`):
```python
async def ingest_metrics(org_id: UUID, batch: list[dict], db: AsyncSession):
    """Write agent-pushed metrics into the same GatewayRequest table.
    
    Identical schema to what the shared gateway writes directly.
    The dashboard/analytics/costs pages read from this table
    regardless of source.
    """
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
            source="vpc_agent",  # new column to distinguish origin
        )
        db.add(entry)
```

**New DB column** (one migration):
```sql
ALTER TABLE gateway_requests ADD COLUMN source VARCHAR(20) DEFAULT 'shared_gateway';
-- Values: 'shared_gateway' | 'vpc_agent'
-- Used for admin visibility only; dashboard queries don't filter on it
```

---

#### Agent Container — Deployment Options

**Option A: Docker Compose** (small teams, single VM)
```yaml
version: "3.8"
services:
  bonito-agent:
    image: ghcr.io/bonito/gateway-agent:latest
    environment:
      BONITO_CONTROL_PLANE: https://api.getbonito.com
      BONITO_ORG_TOKEN: bt-xxxxx
      # Credential source (pick one per provider)
      AWS_SECRETS_MANAGER_ARN: arn:aws:secretsmanager:us-east-1:123:secret:bonito-aws
      AZURE_KEY_VAULT_URL: https://myvault.vault.azure.net
      GCP_SECRET_NAME: projects/123/secrets/bonito-gcp
    ports:
      - "8000:8000"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

**Option B: Kubernetes / Helm** (production, HA)
```bash
helm repo add bonito https://charts.getbonito.com
helm install bonito-gateway bonito/gateway-agent \
  --set controlPlane.url=https://api.getbonito.com \
  --set controlPlane.token=bt-xxxxx \
  --set replicas=3 \
  --set resources.requests.memory=256Mi \
  --set resources.limits.memory=512Mi \
  --set credentials.aws.secretsManagerArn=arn:aws:secretsmanager:... \
  --namespace bonito
```

**Option C: Terraform** (IaC, full automation)

AWS ECS/Fargate:
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
  
  tags = {
    Environment = "production"
    ManagedBy   = "bonito"
  }
}

output "agent_endpoint" {
  value = module.bonito_gateway.internal_url
  # e.g., http://bonito-agent.internal:8000
}
```

Azure Container Apps:
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

GCP Cloud Run:
```hcl
module "bonito_gateway" {
  source         = "bonito/gateway-agent/gcp"
  version        = "~> 1.0"
  project_id     = var.project_id
  region         = "us-central1"
  vpc_connector  = var.vpc_connector_name
  org_token      = var.bonito_org_token
  secret_name    = var.gcp_secret_name
  min_instances  = 2
  max_instances  = 10
}
```

---

#### Dashboard Integration

**New UI elements** (added to existing dashboard, not a separate app):

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
   - Data is identical in either case

---

#### Graceful Degradation

| Failure | Agent behavior | Control plane behavior |
|---------|---------------|----------------------|
| Control plane unreachable | Continue serving with last-known config. Queue metrics for retry (up to 1 hour buffer). | Show agent as "delayed" then "offline". Alert admin. |
| Customer's cloud provider down | LiteLLM failover to next provider (if configured). Return 502 if all providers fail. | Show elevated error rate in analytics. |
| Agent crash / OOM | Container orchestrator restarts automatically. Metrics gap during downtime. | Show gap in analytics timeline. Alert admin. |
| Credentials expired | Agent detects 401 from cloud provider. Attempts to re-read from secrets manager. Logs error if refresh fails. | Error rate spike visible in dashboard. |
| Config sync conflict | Agent always takes latest from control plane (last-write-wins). | N/A — control plane is source of truth. |

---

#### Security Considerations

- **Outbound only**: Agent initiates all connections. No inbound ports required from internet.
- **mTLS optional**: Agent ↔ control plane can use mutual TLS for additional assurance.
- **Org token rotation**: Rotatable from dashboard without redeploying agent (agent picks up new token on next sync).
- **No data exfiltration**: Agent code is open for customer audit. Only metadata (counts, costs) leaves VPC.
- **Network policies**: Agent only needs outbound to: (1) Bonito control plane, (2) Cloud AI endpoints. Everything else blocked.
- **Container signing**: Agent images signed with cosign for supply chain integrity.

---

#### Build Timeline — Detailed

| Week | Deliverable | Details |
|------|------------|---------|
| **1** | Gateway service split | Refactor `gateway.py` into shared `core` + `full_mode` (Railway) + `agent_mode` (VPC). Config sync protocol spec. Agent Dockerfile. |
| **2** | Agent container + ingestion API | Working agent image. `POST /api/agent/ingest`, `GET /api/agent/config`, `POST /api/agent/heartbeat`. Org token (`bt-`) auth. E2E test: agent → control plane → dashboard shows data. |
| **3** | Terraform modules + Helm chart | AWS ECS module, Azure Container Apps module, GCP Cloud Run module. Helm chart with values.yaml. CI/CD pipeline for agent image builds. |
| **4** | Dashboard integration + polish | Settings → VPC mode toggle. Agent status indicator. Admin agents page. Deployment instructions in-app. Documentation. Customer onboarding runbook. |

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
