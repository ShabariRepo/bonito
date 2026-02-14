# Bonito Completion Plan

## Goal
Make Bonito a fully functional product tested against real AWS, Azure, and GCP accounts.

---

## Phase 5 — Real Cloud Integrations

### 5A: AWS Bedrock ✅
- [x] boto3/aioboto3 SDK integration — connect with real credentials
- [x] Validate AWS credentials on connect (STS get-caller-identity)
- [x] Pull real model catalog from Bedrock (list-foundation-models)
- [x] Model invocation — actually call models through Bonito (6 model families)
- [x] Pull real cost data from AWS Cost Explorer API
- [x] Real-time model availability and status checks
- [x] Error handling — expired creds, permission issues, region limits
- [x] Redis caching for model catalog (5min TTL)
- [x] Static pricing data for 30+ model variants

### 5B: Azure AI Foundry ✅
- [x] REST API integration — connect with real service principal (OAuth2 client credentials)
- [x] Validate Azure credentials on connect (subscription lookup)
- [x] Pull real model catalog from Azure OpenAI deployments + Cognitive Services discovery
- [x] Model invocation via Azure OpenAI Chat Completions API
- [x] Pull real cost data from Azure Cost Management API (AI services filter)
- [x] Error handling — auth failures, quota limits, region availability
- [x] Static pricing for 20+ Azure model variants
- [ ] Copilot license tracking (Microsoft Graph API) — future

### 5C: Google Vertex AI ✅
- [x] REST API + service account JWT auth integration
- [x] Validate GCP credentials (project lookup via Resource Manager)
- [x] Pull real model catalog from Vertex AI (publisher models + custom)
- [x] Model invocation — Gemini (generateContent) + PaLM (predict) APIs
- [x] Cost data endpoint (billing info lookup, BigQuery export needed for detailed)
- [x] Error handling — project permissions, API enablement, quotas
- [x] Static pricing for 20+ Vertex model variants

### 5D: Unified Provider Layer ✅
- [x] Abstract provider interface — CloudProvider base class (validate, list, invoke, costs, health)
- [x] All three providers implement the same interface
- [x] Credential encryption at rest (Vault integration for all providers)
- [x] Connection health monitoring (health_check endpoint for all)
- [x] Real-time model status aggregation (via provider-specific APIs)
- [ ] Credential rotation support — future
- [ ] Cross-provider model comparison dashboard — Phase 6

---

## Phase 6 — Real AI Integration ✅

### 6A: AI-Powered UX ✅
- [x] Wire chat panel to real LLM (auto-selects Claude→GPT→Gemini from connected providers)
- [x] Cmd+K command bar with fast intent parsing (no LLM needed)
- [x] Context-aware — AI knows connected providers, routes through them
- [x] Fallback intent parser when no providers connected
- [ ] Natural language to action — "deploy GPT-4o on Azure" (needs frontend wiring)

### 6B: Intelligent Routing ✅
- [x] Real request routing — route-and-invoke endpoint
- [x] 4 strategies: cost-optimized, latency-optimized, balanced, failover
- [x] Cost-based routing with real pricing data from all providers
- [x] Decision path logging (explainable routing)
- [ ] Latency measurement from real traffic (baseline estimates for now)
- [ ] Routing analytics from real traffic (needs usage tracking)

---

## Phase 7 — Authentication & Security ✅

### 7A: Auth System ✅
- [x] JWT auth (register, login, refresh, logout, /me endpoints)
- [x] bcrypt password hashing
- [x] Redis session management (refresh tokens)
- [x] Auth dependencies: get_current_user, require_admin, require_org_member
- [x] Alembic migration for hashed_password column
- [ ] SSO/SAML integration (Azure AD, Okta) — future
- [ ] Email verification flow — future
- [ ] NextAuth.js frontend integration — future

### 7B: Security Hardening ✅
- [x] All credentials encrypted at rest via Vault (all providers)
- [x] API rate limiting (Redis-backed, 3 tiers: 100/10/20 per min)
- [x] CORS lockdown for production
- [x] Security headers (nosniff, DENY framing, XSS, HSTS, referrer, permissions)
- [x] Request ID on all responses
- [x] Input validation/sanitization on provider credentials
- [x] Audit middleware for sensitive endpoints (auth, connect, invoke)
- [x] SQL injection prevention (SQLAlchemy parameterized — already done)

---

## Phase 8 — Real Compliance & Governance ✅

### 8A: Live Compliance Checks ✅
- [x] AWS: Bedrock logging, IAM overly-permissive, EBS encryption, CloudTrail
- [x] Azure: AI Services network rules, RBAC broad roles, diagnostic settings
- [x] GCP: Vertex AI SA permissions, audit logging, VPC Service Controls
- [x] Framework mapping: SOC2, HIPAA, GDPR, ISO27001 (10 check types)
- [x] Redis-cached results (1hr TTL)
- [ ] Compliance drift detection — future

### 8B: Policy Enforcement
- [ ] Real-time policy evaluation before model deployment — future
- [ ] Spend limit enforcement — future
- [ ] Region restriction enforcement — future
- [ ] Model allowlist/blocklist — future

---

## Phase 9 — Real Cost Intelligence ✅

### 9A: Live Cost Aggregation ✅
- [x] AWS Cost Explorer integration
- [x] Azure Cost Management integration
- [x] GCP Billing integration
- [x] Unified cost normalization across providers
- [x] Redis caching (1hr TTL)
- [ ] Per-team/project cost attribution — needs team mapping
- [ ] Budget alerts (email/webhook) — future

### 9B: Cost Optimization ✅
- [x] Model recommendation engine (cheaper alternatives)
- [x] Cross-provider routing recommendations
- [x] Cost forecasting (linear regression with confidence bounds)
- [x] /recommendations endpoint
- [ ] Reserved capacity recommendations — future
- [ ] Savings report — future

---

## Phase 10 — Production Readiness ✅

### 10A: Deployment ✅
- [x] Production Docker images (multi-stage builds, non-root user, healthchecks)
- [x] Railway backend deployment config (railway.json)
- [x] Vercel frontend deployment config (vercel.json, security headers, API rewrites)
- [x] CI/CD pipeline (GitHub Actions: test→lint→build→deploy)
- [x] Production docker-compose with resource limits
- [x] Vault production config with TLS
- [ ] Domain + SSL setup — needs domain purchase
- [ ] Production PostgreSQL provisioning
- [ ] Production Redis provisioning

### 10B: Monitoring & Observability
- [x] Health check endpoints (already exist)
- [x] Structured logging
- [ ] Error tracking (Sentry) — future
- [ ] API metrics dashboard — future
- [ ] Uptime monitoring — future

### 10C: Polish
- [ ] Loading states for every API call
- [ ] Error boundaries on all pages
- [ ] Mobile-responsive refinements
- [ ] Accessibility audit
- [ ] Performance optimization

---

## Testing Milestones

### Milestone 1: AWS Works (End of Week 1)
Connect Shabari's AWS account → see real Bedrock models → invoke a model → see real costs

### Milestone 2: Azure Works (End of Week 2)
Connect Azure account → see real AI Foundry models → deploy endpoint → track costs

### Milestone 3: GCP Works (End of Week 3)
Connect GCP account → see real Vertex AI models → deploy endpoint → track costs

### Milestone 4: Multi-Cloud (End of Week 4)
All 3 connected → unified dashboard with real data → AI chat works → routing works

### Milestone 5: Secure & Compliant (End of Week 6)
Auth working → real compliance checks → policy enforcement → audit trail

### Milestone 6: Production (End of Week 8-10)
Deployed → monitoring → polished → ready to demo to real prospects

---

## Phase 11 — Onboarding Wizard ✅

### 11A: Onboarding Progress Tracker ✅
- [x] DB migration: `onboarding_progress` table (org_id, current_step, providers, iac_tool, timestamps)
- [x] SQLAlchemy model + Pydantic schemas
- [x] GET/PUT /api/onboarding/progress — persist wizard state per org
- [x] Auto-create progress record on first visit
- [x] Resume support — users can close and come back

### 11B: IaC Template Engine ✅
- [x] AWS templates: Terraform, Pulumi, CloudFormation, Manual
  - IAM user with Bedrock read/invoke, Cost Explorer read, CloudTrail read
  - No admin keys, no wildcard policies, scoped to account
- [x] Azure templates: Terraform, Pulumi, Bicep, Manual
  - Service principal with Cognitive Services User (not Contributor/Owner)
  - Cost Management Reader, resource group scoped
  - Diagnostic logging enabled
- [x] GCP templates: Terraform, Pulumi, Manual
  - Service account with Vertex AI User (not Editor)
  - Billing Viewer, Monitoring Viewer, project-scoped
  - Audit logging for all Vertex AI operations
- [x] POST /api/onboarding/generate-iac — dynamic code generation
- [x] Enterprise security in ALL templates: least privilege, encryption, audit logging, rotation guidance

### 11C: Credential Validation ✅
- [x] POST /api/onboarding/validate — validate pasted credentials
- [x] AWS: STS get-caller-identity + Bedrock list check + Cost Explorer check
- [x] Azure: OAuth2 token acquisition + subscription access check
- [x] GCP: Service account JSON validation + Vertex AI access check
- [x] Auto-updates onboarding progress on successful validation

### 11D: Wizard UI ✅
- [x] 5-step wizard: Welcome → IaC Tool → Generated Code → Validate → Success
- [x] Progress bar + step indicators (reuses existing StepWizard component)
- [x] Provider multi-select with visual cards
- [x] IaC tool selector (filtered by selected providers)
- [x] Code viewer with syntax highlighting, copy button, filename header
- [x] Per-provider credential input forms
- [x] Real-time validation feedback (success/error states)
- [x] Animated success page with dashboard redirect
- [x] State persistence — resume from where you left off

---

## Phase 12 — API Gateway (LiteLLM Integration) ✅

- [x] Embed LiteLLM as the proxy engine
- [x] OpenAI-compatible endpoint (POST /v1/chat/completions)
- [x] Model aliasing and routing strategies (cost, latency, failover)
- [x] Request/response logging with cost attribution
- [x] Per-team/user rate limiting (Redis-backed)
- [x] Auto-failover between providers
- [x] Format translation (OpenAI format → Bedrock/Azure/Vertex)
- [x] Token metering and cost tracking per request
- [x] API key management (create/revoke, bn-xxx format)
- [x] Gateway dashboard with usage charts, logs, code snippets

---

## Phase 13 — AI Agent (Groq-powered) ✅

- [x] Embedded AI copilot in the dashboard (sliding panel)
- [x] Powered by Groq (llama-3.3-70b-versatile) for fast inference
- [x] Org-aware context: knows connected providers, models, costs, compliance status
- [x] Function-calling tools: cost summary, compliance status, provider health, model recommendations, usage stats
- [x] Streaming responses via SSE
- [x] Cmd+K command bar wired to real copilot API
- [x] Quick action buttons (Cost Summary, Compliance Check, Optimize Spending)
- [x] Upsell feature for Enterprise tier

---

## Phase 14 — Engagement & Retention ✅

- [x] In-app notifications system (with read/unread state)
- [x] Notification bell with unread count badge (30s polling)
- [x] Alert rules management (create/edit/delete, budget thresholds)
- [x] Notification preferences (weekly digest, cost alerts, compliance alerts)
- [x] Usage analytics dashboard (overview cards, usage charts, cost breakdowns, trends)
- [x] Weekly digest endpoint
- [x] Pluggable email/webhook delivery (SMTP abstraction)

---

## Phase 15 — Model Details & Playground ✅

- [x] Clickable models on the Models page → opens model detail view
- [x] Model info: provider, pricing/token costs, capabilities, context window, availability
- [x] Usage history for that model across the org
- [x] Built-in playground: chat interface to test models live
- [x] Requests routed through Bonito gateway → customer's cloud (Bedrock/Azure/Vertex)
- [x] Governance rules applied (token limits, budget) even in playground
- [x] Side-by-side multi-model comparison (max 4 models)
- **Goal:** Complete the "connect provider → see models → use them" loop ✅

---

## Phase 16 — Routing Policies ✅

- [x] Visual routing policy builder with strategy cards, model selector, rules panel
- [x] Assign models to named routes (e.g., "production-chat", "internal-coding")
- [x] Primary/fallback model configuration per route
- [x] Routing rules: 5 strategies (cost_optimized, latency_optimized, balanced, failover, ab_test)
- [x] Load balancing across providers
- [x] A/B testing support (% split between models, weights sum to 100)
- [x] Auto-generated API key prefixes (rt-xxx) per route
- [x] Policy test endpoint (dry-run model selection)
- [x] Policy stats endpoint

---

## Phase 17 — Deployment Provisioning

- [ ] Deploy/provision model endpoints on customer's cloud infra from Bonito UI
- [ ] Support AWS Bedrock model access, Azure AI model deployments, GCP Vertex endpoints
- [ ] Configure: instance type, scaling (min/max), throughput
- [ ] IaC generation (Terraform) for each deployment
- [ ] Start/stop/scale endpoints from dashboard
- [ ] Cost estimation before deployment
- [ ] Status monitoring of deployed endpoints

---

## Phase 18 — One-Click Model Activation

- [ ] Enable/activate models directly from Bonito UI (no console-hopping)
- [ ] AWS Bedrock: Call `PutFoundationModelEntitlement` API to request model access
  - Show EULA/terms for models that require acceptance (legal step)
  - Handle instant-enable vs waitlist models differently
  - Requires `bedrock:PutFoundationModelEntitlement` permission (add to IaC templates)
- [ ] Azure OpenAI: Create model deployments via Management API
  - Deploy with sensible defaults (standard tier, auto-scale)
  - Requires "Cognitive Services Contributor" role (upgrade from "User" in IaC templates)
- [ ] GCP Vertex AI: Enable APIs and request quota via Service Usage API
  - Handle quota increase requests where needed
- [ ] UI: "Enable" button on 🔒 models → confirmation dialog → inline status update
- [ ] Update IaC templates to include model management permissions
- [ ] Bulk-enable: select multiple models to activate at once

---

## Current Status
- **Completed:** Phases 1-16 (full platform + model playground + routing policies)
- **Up Next:** Phase 17 (Deployment Provisioning), Phase 18 (One-Click Model Activation)
- **Remaining:** SSO/SAML, production deployment to getbonito.com (Vercel + Railway), real cloud credential testing
