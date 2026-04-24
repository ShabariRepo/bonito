# Bonito Critical Paths — Logging & Helios Integration Plan

## Purpose

Maps every critical request path in Bonito, identifies logging gaps, and prioritizes instrumentation work for Helios integration. Helios (running on NVIDIA Orin) ingests structured NDJSON events from GCS and provides self-healing via Kimi K2.5 analysis → Claude review → GitHub PR pipeline.

## Existing Infrastructure

| Component | Status | Notes |
|-----------|--------|-------|
| LogService (async buffer) | **Live** | 2s/100-event flush, 10K buffer, fan-out to integrations |
| Log emitters (gateway/auth/agent/kb) | **Live** | `emit_gateway_event()`, `emit_auth_event()`, etc. |
| AuditMiddleware | **Live** | Fires on sensitive paths, records user/org/action/latency |
| JSONFormatter | **Live** | Structured JSON with request_id, UTC timestamps |
| GCS Log Sink (`gcs_log_sink.py`) | **Live** | NDJSON output, Helios-compatible, object finalize notifications |
| Log Emit Middleware (`log_emit.py`) | **Live** | HTTP request/response events in Sentry-compatible format |
| Request ID Middleware | **Live** | UUID per request, propagated in X-Request-ID header |
| Frontend ErrorBoundary | **Stub** | TODO: wire to error monitoring (no Sentry/Helios SDK) |
| Frontend structured logging | **Missing** | Only `console.error()` calls |
| Distributed tracing (frontend→backend) | **Missing** | No request ID propagation from frontend |

## Helios Touchpoints (Existing)

| File | What it does |
|------|-------------|
| `backend/app/middleware/log_emit.py` | Emits HTTP events in Sentry format for Helios ingestion |
| `backend/app/core/gcs_log_sink.py` | NDJSON sink with predictable paths for Helios object finalize notifications |

Helios consumes from `gs://bonito-logs-prod` at path pattern `logs/YYYY/MM/DD/HH/*.ndjson`.

---

## Critical Path Inventory

### Path 1: Gateway — `/v1/chat/completions`

**Priority: P0 (highest revenue path)**

| Step | File | Line | What happens |
|------|------|------|-------------|
| API key auth | `api/routes/gateway.py` | 88-109 | Validates `bn-`/`rt-` prefix, rate limit via Redis |
| Body size check | `api/routes/gateway.py` | 158-163 | Rejects >1MB (413) |
| Usage quota | `api/routes/gateway.py` | 169-176 | `usage_tracker.track_gateway_request()` (429 if exceeded) |
| KB injection | `api/routes/gateway.py` | 179, 233-235 | Optional X-Bonito-Knowledge-Base header |
| Policy enforcement | `api/routes/gateway.py` | 206 | Model allow-list, spend cap, org restrictions |
| LiteLLM routing | `services/gateway.py` | 337-446 | Credential load from Vault, router build, provider dispatch |
| Streaming response | `api/routes/gateway.py` | 256-395 | Chunk accumulation, token counting, cost calc |
| Cost logging | `api/routes/gateway.py` | 370-384 | GatewayRequest DB record |
| Failover | `api/routes/gateway.py` | 1046-1133 | Rate limit 429 / 5xx → retry on equivalent model |

**Logging gaps:**
| Gap | Severity | Current | Should be |
|-----|----------|---------|-----------|
| Cost calculation failures | **HIGH** | DEBUG | WARNING — billing blind spots |
| LiteLLM failover transitions | **HIGH** | Not logged | INFO with from_model, to_model, reason |
| Streaming errors on client disconnect | **MEDIUM** | ERROR in finally (may be lost) | Emit to GCS sink before response closes |
| Token estimation fallbacks | **LOW** | DEBUG | INFO with estimation_method field |

---

### Path 2: Auth — Login / Register / SSO

**Priority: P0 (security-critical)**

| Step | File | Line | What happens |
|------|------|------|-------------|
| Registration | `api/routes/auth.py` | 119-181 | Invite code → password validation → user/org create → email verify |
| Login | `api/routes/auth.py` | ~222 | Credential check → JWT (30min) + refresh (7d) → Redis session |
| SAML SSO | `api/routes/sso.py` | 99-149 | Assertion validation → user provisioning → token redirect |
| Token refresh | `services/auth_service.py` | — | Mutex-protected, HS256 |

**Logging gaps:**
| Gap | Severity | Current | Should be |
|-----|----------|---------|-----------|
| Failed login attempt details | **HIGH** | emit_auth_event (basic) | Add IP, user_agent, failure_reason for brute-force detection |
| Registration invite code redemption | **MEDIUM** | Not logged separately | INFO with invite_code_id, email |
| SSO provider errors | **MEDIUM** | WARNING (generic) | Structured with provider_type, saml_error_code |
| Email send failures | **LOW** | Silently caught | WARNING with email, error_type |

---

### Path 3: Agent Execution — Bonobot

**Priority: P0 (core product feature)**

| Step | File | Line | What happens |
|------|------|------|-------------|
| Rate limit | `services/agent_engine.py` | 129 | Redis per-agent request count |
| Budget enforcement | `services/agent_engine.py` | 132 | Hard spend limit (402 if exceeded) |
| Input sanitization | `services/agent_engine.py` | 135 | Prompt injection pattern matching |
| Audit log | `services/agent_engine.py` | 138-144 | Non-blocking DB write |
| MCP server connect | `services/agent_engine.py` | 154 | Initialize tool servers |
| Context assembly | `services/agent_engine.py` | 160 | History + system prompt + tools + KB context |
| Agent loop | `services/agent_engine.py` | 163 | LLM inference → tool exec → reply (max depth 3) |
| Memwright store | `services/agent_engine.py` | 169-177 | Session memory persistence |

**Logging gaps:**
| Gap | Severity | Current | Should be |
|-----|----------|---------|-----------|
| Tool execution counts per session | **HIGH** | Not tracked | INFO summary at session end |
| Approval queue expiration | **HIGH** | Status updated, no log/notification | WARNING + alert channel dispatch |
| Prompt injection detection hits | **MEDIUM** | Sanitized silently | WARNING with pattern_matched, input_hash |
| MCP server connection failures | **MEDIUM** | Non-fatal, unclear logging | WARNING with server_name, error |
| Budget approaching threshold | **LOW** | Only fires at limit | WARNING at 80% of budget |

---

### Path 4: Knowledge Base / RAG

**Priority: P1**

| Step | File | Line | What happens |
|------|------|------|-------------|
| Document parse | `services/kb_ingestion.py` | 32-182 | PDF/DOCX/HTML/CSV/TXT extraction |
| Text chunking | `services/kb_ingestion.py` | 185-302 | Recursive split, configurable chunk_size + overlap |
| Embedding generation | `services/kb_ingestion.py` | 305-425 | GCP/OpenAI/Bedrock, batch of 20, 30s timeout |
| pgvector store | `services/agent_memory_service.py` | 82-89 | UPDATE with vector type cast |
| Vector search | `services/agent_memory_service.py` | 96-151 | Cosine similarity, fallback to text search |

**Logging gaps:**
| Gap | Severity | Current | Should be |
|-----|----------|---------|-----------|
| Embedding timeouts | **HIGH** | ERROR (generic) | ERROR with kb_id, doc_id, batch_index, timeout_seconds |
| Silent fallback to text search | **HIGH** | WARNING (vague) | WARNING with query_hash, fallback_reason, result_count |
| PDF page extraction failures | **MEDIUM** | WARNING per page | WARNING with doc_id, page_number, error_type |
| Embedding model selection | **LOW** | Not logged | INFO with selected_model, available_models |

---

### Path 5: Provider Credentials — Vault

**Priority: P1**

| Step | File | Line | What happens |
|------|------|------|-------------|
| get_secrets() | `core/vault.py` | 39-80 | Path-based cache, HTTP GET, retry with exponential backoff |
| put_secrets() | `core/vault.py` | 87-100 | HTTP POST, cache invalidation |
| Credential loading | `services/gateway.py` | 337-391 | Per-provider Vault fetch, managed key env fallback |
| Credential validation | `api/routes/providers.py` | 156-200 | Real cloud provider validation |

**Logging gaps:**
| Gap | Severity | Current | Should be |
|-----|----------|---------|-----------|
| Vault retry attempts | **HIGH** | Not individually logged | WARNING per retry with attempt_number, delay_seconds |
| Missing managed provider master keys | **HIGH** | ERROR (no alert) | CRITICAL — should trigger Helios alert |
| Provider credential load failures | **MEDIUM** | WARNING (continues silently) | WARNING with provider_id, provider_type, error |
| Vault unreachable at startup | **MEDIUM** | RuntimeError raised | CRITICAL with retry_count, total_wait_seconds |

---

### Path 6: Cost Tracking

**Priority: P1**

| Step | File | Line | What happens |
|------|------|------|-------------|
| Token counting | `api/routes/gateway.py` | 331-346 | Streaming accumulation → litellm fallback |
| Cost lookup | `api/routes/gateway.py` | 350-362 | litellm.cost_per_token() with provider prefix |
| Request logging | `api/routes/gateway.py` | 370-384 | GatewayRequest record (org, model, tokens, cost, latency) |
| Aggregation | `services/cost_service.py` | 50-162 | Per-provider fetch, model/service breakdown |

**Logging gaps:**
| Gap | Severity | Current | Should be |
|-----|----------|---------|-----------|
| Zero-cost records | **HIGH** | DEBUG (invisible) | WARNING with model, token_count, reason |
| Provider data fetch failures in aggregation | **MEDIUM** | WARNING (per provider) | WARNING + metadata for Helios correlation |
| Token counting method used | **LOW** | Not logged | DEBUG with method (streaming/litellm_counter/estimate) |

---

### Path 7: Memwright — Session Memory

**Priority: P2**

| Step | File | Line | What happens |
|------|------|------|-------------|
| Budget determination | `services/memwright_service.py` | 57-65 | Model pattern matching (zero for flash/mini/kimi/haiku) |
| Instance get/create | `services/memwright_service.py` | — | LRU cache (256 max), SQLite on thread pool |
| recall() | `services/memwright_service.py` | 83-114 | Query + format as context string |
| store() | `services/memwright_service.py` | 116+ | User message + truncated assistant response |

**Logging gaps:**
| Gap | Severity | Current | Should be |
|-----|----------|---------|-----------|
| LRU eviction events | **MEDIUM** | Not logged | INFO with evicted_key, cache_size |
| Store failures | **LOW** | WARNING (non-fatal) | WARNING with session_id, error_type |
| Recall latency | **LOW** | Not logged | DEBUG with session_id, latency_ms, result_count |

---

### Path 8: Frontend (All Critical Flows)

**Priority: P1**

| Flow | Key Files | Current Error Handling |
|------|-----------|----------------------|
| Login/Register | `(auth)/login/page.tsx`, `(auth)/register/page.tsx` | Try/catch → toast, human-friendly error mapping |
| SSO Callback | `auth/sso/callback/page.tsx` | URL fragment parse → error state with "Back to Login" |
| Gateway Keys | `gateway/keys/page.tsx` | Fetch errors logged to console only, no toast |
| Agent Canvas | `agents/[projectId]/page.tsx` | Toast on creation errors, node drag silently fails |
| KB Management | `knowledge-base/page.tsx` | Fetch errors → console.error only, no user feedback |
| Provider Setup | `providers/page.tsx` | Revalidate has good error handling, disconnect is silent |
| Playground | `playground/page.tsx` | Errors shown as chat messages with warning prefix |

**Frontend logging gaps (all HIGH):**
| Gap | Impact |
|------|--------|
| No structured logging | Can't correlate frontend errors to backend request IDs |
| No error tracking SDK | ErrorBoundary has a TODO for Sentry — should point to Helios |
| Silent failures (KB fetch, key creation, node drag) | Users don't know something broke |
| No request ID propagation | Can't trace frontend action → backend log → GCS → Helios |

---

## Prioritized Implementation Plan

### Phase 1: Backend logging gaps (P0 paths) — HIGH IMPACT

| # | Task | Path | Effort |
|---|------|------|--------|
| 1 | Promote cost calc failures from DEBUG → WARNING with model/token context | Gateway | Small |
| 2 | Log LiteLLM failover transitions (from_model, to_model, reason, latency) | Gateway | Small |
| 3 | Add IP + user_agent + failure_reason to auth event emissions | Auth | Small |
| 4 | Log tool execution summary at agent session end | Agent | Medium |
| 5 | Add approval queue expiration WARNING + alert dispatch | Agent | Medium |
| 6 | Log prompt injection detection hits with pattern + input hash | Agent | Small |

### Phase 2: Backend logging gaps (P1 paths) — RELIABILITY

| # | Task | Path | Effort |
|---|------|------|--------|
| 7 | Enrich embedding timeout logs with kb_id, doc_id, batch_index | KB/RAG | Small |
| 8 | Log vector search fallback-to-text with query context | KB/RAG | Small |
| 9 | Log individual Vault retry attempts with attempt_number | Vault | Small |
| 10 | Promote missing master key from ERROR → CRITICAL (Helios alert trigger) | Vault | Small |
| 11 | Add zero-cost record detection (WARNING when cost=0 but tokens>0) | Cost | Small |

### Phase 3: Frontend observability — FULL PICTURE

| # | Task | Path | Effort |
|---|------|------|--------|
| 12 | Add request ID propagation (X-Request-ID header from frontend) | All | Medium |
| 13 | Replace console.error with structured log helper | All | Medium |
| 14 | Wire ErrorBoundary to Helios (POST to GCS sink or Helios API) | All | Medium |
| 15 | Add toast notifications for silent failures (KB fetch, key create, node drag) | UI | Medium |

### Phase 4: Helios integration — SELF-HEALING

| # | Task | Path | Effort |
|---|------|------|--------|
| 16 | Define Helios alert rules for P0 events (gateway errors >5%, auth failures, Vault unreachable) | Helios | Medium |
| 17 | Configure fix pipeline triggers (heal_action: analyze_and_fix) for known patterns | Helios | Medium |
| 18 | Set up GCS object finalize notifications → Helios watch mode | Infra | Medium |
| 19 | Connect Helios alert channels (Slack/Discord/WhatsApp) | Helios | Small |
| 20 | Test end-to-end: Bonito error → GCS → Helios detect → Kimi fix → Claude review → PR | All | Large |

---

## Helios Alert Rules (Proposed)

| Rule | log_type | Pattern | Threshold | Heal Action |
|------|----------|---------|-----------|-------------|
| Gateway error spike | gateway | `severity:error` | >5% of requests in 5min | `analyze_and_fix` |
| Auth brute force | auth | `event_type:login_failed` | >10 per IP in 5min | Alert only (HITL) |
| Vault unreachable | gateway | `vault_retry` | >3 retries in 1min | Alert + auto-switch to env fallback |
| Embedding timeout | kb | `embedding_timeout` | >2 in 10min | Alert only |
| Cost anomaly | gateway | `cost > 0.10/request` | Single event | Alert only |
| Zero-cost records | gateway | `cost:0 AND tokens>0` | >5 in 1hr | `analyze_and_fix` |
| Missing master key | gateway | `master_key_missing` | Single event | Alert (CRITICAL) |
| Agent budget exceeded | agent | `budget_exceeded` | Single event | Alert only |
| Provider failover | gateway | `failover_triggered` | >3 in 5min | Alert + suggest provider health check |

---

## Connectivity: Helios ↔ Bonito

**Current state:**
- Tailscale is installed but **not running** on this machine
- SSH key exists for Tailscale IP `100.101.54.46` (the Orin)
- Helios repo at `/Users/appa/Desktop/code/helios/` — Go project, not yet deployed

**To complete the loop:**
1. Start Tailscale on this machine (`tailscale up`)
2. Verify SSH to `100.101.54.46` (Orin)
3. Deploy Helios on Orin (`docker compose up` or bare Go binary)
4. Configure GCS credentials on Orin for `bonito-logs-prod` bucket
5. Add Kimi + Groq API keys to `configs/monitor.yaml`
6. Point Helios GCS reader at `logs/YYYY/MM/DD/HH/*.ndjson`
7. Verify event flow: Bonito → GCS → Helios → Dashboard

---

## Related Docs

- [LOGGING-STRATEGY.md](./LOGGING-STRATEGY.md) — Log service architecture, integration destinations, API design
- [LOGGING-USAGE.md](./LOGGING-USAGE.md) — How to use the logging system
- [Helios HELIOS.md](../../helios/bonito-healer/HELIOS.md) — Helios spec and component details
- [Helios ARCHITECTURE.md](../../helios/bonito-healer/ARCHITECTURE.md) — Full architecture diagram
- [SOC2-ROADMAP.md](./SOC2-ROADMAP.md) — Compliance requirements that depend on logging
- [KNOWN-ISSUES.md](./KNOWN-ISSUES.md) — Active issues that logging should catch
