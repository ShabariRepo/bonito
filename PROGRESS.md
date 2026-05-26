# Bonito — Progress Tracker

_Last updated: 2026-05-25_

## Recently Completed

### Phase 19: Agent HPA Autoscaling ✅ (2026-05-25)

**Branch:** `feat/agent-hpa` | **PR:** #43048

Agent-level horizontal pod autoscaling — Phase 1 virtual scaling. Dynamically raises effective RPM in Redis when utilization crosses threshold.

**What was built:**
- [x] Migration 043 — `autoscale_enabled`, `autoscale_config`, `primary_agent_id`, `replica_index` columns on agents; `agent_scaling_events` table
- [x] `agent_autoscaler.py` service — reactive scale-up in `_check_rate_limit`, background scale-down loop (30s, advisory lock 839272)
- [x] Modified `_check_rate_limit` in `agent_engine.py` — returns `(remaining, effective_rpm, scaling_active)` tuple
- [x] 4 API endpoints: `GET /agents/{id}/scaling`, `GET /agents/{id}/scaling/events`, `POST /agents/{id}/scaling/configure`, `POST /agents/{id}/scaling/manual`
- [x] Feature gate: `agent_hpa` — Enterprise+ only
- [x] CLI: `bonito agents scaling status|configure|events|manual`
- [x] YAML: `scaling` block in `bonito.yaml` agent config via `deploy.py`
- [x] Frontend: HPA documentation section on `/docs` page
- [x] SecurityMetadata response includes `effective_rpm` and `scaling_active`
- [x] Wired into FastAPI lifespan (`start_autoscaler` / `stop_autoscaler`)

**Load test results (100 tickets, Bulletproof-style):**
| Metric | Result |
|--------|--------|
| Hallucinations | 0 |
| Routing accuracy | 96.3% |
| Scaling events | 5 (10→20→40→50 RPM + scale-down) |
| Quality degradation | None |
| Successful | 59/100 (41 rate-limited at max 50 RPM cap) |

**What's NOT built yet (Phase 2):**
- [ ] Physical replicas — clone agent rows with load balancer
- [ ] Session affinity for replicas
- [ ] Graceful drain on scale-down
- [ ] Cross-provider replica routing (replica 1 → Vertex, replica 2 → Bedrock)
- [ ] Request queuing for rate-limited tickets (see below)

### Request Queuing (Planned — Phase 19b)

41/100 tickets were dropped (429) during the load test because they exceeded the max scaled RPM (50). These requests currently fail immediately. A queuing layer would hold them and retry when capacity frees up.

**Status:** Not yet built. Design TBD — see active discussion.

---

## Previously Completed (2026-05-25)

- [x] KB delete fix — raw SQL deletes to avoid pgvector OID error
- [x] KB vector dimension fix — migration 041, 768→1024 dims for Titan V2
- [x] Alembic multiple heads fix — merge migration 042
- [x] pgvector greenlet_spawn fix — `checkout` event instead of `connect`
- [x] Ingestion error handler fix — `db.rollback()` before status update
- [x] GCS fast-fail — immediate failure without GCS credentials
- [x] Embedding timeout — 30s→90s for Bedrock under rate limiting
- [x] KB search quality fix — threshold 0.7→0.5, `MODEL_MAX_DIMENSIONS` clamping
- [x] Gateway Vault fallback — `_get_provider_secrets()` with Vault → encrypted DB chain
- [x] Gateway duplicate provider fix — keyed by provider UUID, not type
- [x] External orchestration / Breadcrumbs tracing — `parent_agent_id` on execute
- [x] Agent Health dashboard — `/admin/agent-health` with model health checks

## What's Planned

- [ ] **Request queuing** — hold rate-limited requests and retry (Phase 19b)
- [ ] **Physical replicas** — clone agents with load balancer (Phase 2 HPA)
- [ ] SOC-2 Type II certification
- [ ] Smart routing (complexity-aware model selection)
- [ ] VPC Gateway Agent (enterprise self-hosted data plane)
- [ ] Additional providers (Cohere, Mistral, custom endpoints)
- [ ] Advanced audit log export & SIEM integration
- [ ] VectorBoost: wire compression into KB ingestion
- [ ] Vault org-namespacing: `providers/{org_id}/{provider_id}` paths
