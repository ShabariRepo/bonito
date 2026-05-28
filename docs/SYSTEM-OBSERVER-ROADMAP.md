# System Observer Roadmap

## Overview

Two-layer observability system: mechanical instrumentation (Layer 1) + AI-powered health observer (Layer 2). Layer 1 is the foundation — structured logs with resource IDs on every agent/KB/gateway event. Layer 2 is a Bonito-internal scheduled agent that reads those logs, reasons about health, and surfaces anomalies.

---

## Layer 1: Agent Engine Instrumentation

**Goal:** Wire `emit_agent_event` into the actual agent execution path so every lifecycle event lands in both PostgreSQL and GCS with proper `resource_id` (agent UUID).

**Status:** `emit_agent_event()` exists in `log_emitters.py` but is never called. GCS sink now supports `resource_id`, `resource_type`, `feature` tags (done 2026-05-27). Missing: call sites in the engine.

### Events to emit

| Event | Where to hook | feature tag | Key metadata |
|-------|--------------|-------------|--------------|
| `execution_start` | `agent_engine.py` — top of execute | `execution` | agent_id, agent_name, model_id, trigger (api/schedule/delegation) |
| `tool_use` | `agent_engine.py` — tool dispatch | `tool_use` | agent_id, tool_name, tool_type (builtin/mcp/http), duration_ms, success |
| `tool_denied` | `agent_engine.py` — tool policy check | `tool_use` | agent_id, tool_name, denial_reason |
| `kb_search` | `_tool_search_kb()` | `kb_search` | agent_id, kb_id, query (truncated), result_count, threshold |
| `delegation_start` | `_tool_invoke_agent()` | `delegation` | parent_agent_id, target_agent_id, connection_type |
| `delegation_complete` | `_tool_invoke_agent()` return | `delegation` | parent_agent_id, target_agent_id, duration_ms, success |
| `execution_complete` | `agent_engine.py` — end of execute | `execution` | agent_id, duration_ms, total_tokens, cost, tool_calls_count |
| `execution_error` | `agent_engine.py` — exception handler | `execution` | agent_id, error_type, error_message, traceback (truncated) |
| `rate_limited` | `_check_rate_limit()` | `hpa` | agent_id, current_rpm, limit, queued (bool) |
| `scale_event` | `agent_scaling.py` | `hpa` | agent_id, direction (up/down), replica_count, utilization_pct |
| `schedule_trigger` | `scheduler.py` — cron fire | `scheduler` | agent_id, schedule_id, cron_expression |
| `memory_write` | `agent_memory.py` — store | `memory` | agent_id, memory_type, key (truncated) |
| `memory_recall` | `agent_memory.py` — search | `memory` | agent_id, query (truncated), result_count |

### Files to modify

1. `backend/app/services/agent_engine.py` — main execution loop, tool dispatch, error handler
2. `backend/app/services/agent_scaling.py` — scale up/down events
3. `backend/app/services/agent_scheduler.py` — cron trigger
4. `backend/app/services/agent_memory.py` — memory read/write
5. `backend/app/api/routes/bonobot_agents.py` — execution entry point (request-level context)

### Estimated effort: 1-2 sessions

---

## Layer 2: System Observer Agent

**Goal:** A Bonito-internal agent per org that wakes up on schedule, reads recent logs, and produces structured health assessments. Not visible to customers, not controllable, doesn't count toward agent limits.

### Architecture

```
┌─────────────────────────────────────────────────┐
│  Scheduler (existing cron infra, Phase 8)       │
│  Fires every 6h per active org                  │
└──────────────────┬──────────────────────────────┘
                   │
                   v
┌─────────────────────────────────────────────────┐
│  System Observer Runner                          │
│                                                  │
│  1. Query platform_logs WHERE org_id = X         │
│     AND created_at > last_run_at                 │
│                                                  │
│  2. Compute aggregates:                          │
│     - Error rate per agent (%)                   │
│     - p50/p95/p99 latency per agent              │
│     - Cost per 1K tokens per agent               │
│     - Queue depth / overflow events              │
│     - Failed tool calls by type                  │
│     - Auth failures (PAT/JWT/gateway key)        │
│     - KB search hit rate (results > 0 / total)   │
│     - Compliance check failures                  │
│                                                  │
│  3. Send to LLM (Haiku or Groq):                │
│     System prompt: structured health analysis    │
│     Input: aggregated metrics JSON               │
│     Output: structured findings JSON             │
│                                                  │
│  4. Persist findings:                            │
│     - agent_health_reports table (new)           │
│     - emit to system log type in GCS             │
│     - Update Agent Health dashboard badges       │
│                                                  │
│  5. Alert if critical:                           │
│     - Webhook (existing delivery infra)          │
│     - Email (existing delivery infra)            │
│     - Slack (existing delivery infra)            │
└─────────────────────────────────────────────────┘
```

### Data model

**New table: `system_observer_reports`**

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK | |
| run_at | DateTime(tz) | When this observer run executed |
| period_start | DateTime(tz) | Start of the observation window |
| period_end | DateTime(tz) | End of the observation window |
| summary | JSONB | Top-level health summary |
| agent_findings | JSONB | Per-agent health details |
| governance_findings | JSONB | Compliance/access/policy findings |
| anomalies | JSONB | Flagged anomalies with severity |
| alert_sent | Boolean | Whether alerts were dispatched |
| model_used | String(50) | Which LLM was used for analysis |
| tokens_used | Integer | Cost tracking for the observer itself |
| created_at | DateTime(tz) | |

### What the LLM analyzes (system prompt)

The observer LLM receives pre-aggregated metrics (not raw logs) and is asked to:

1. **Agent health** — flag agents with error rate > 5%, p95 > 10s, cost anomalies (2x+ deviation from 7d average)
2. **Stuck agents** — agents with `execution_start` but no `execution_complete` in window
3. **Model availability** — agents using deprecated/unroutable models (cross-ref with model sync data)
4. **Tool failures** — tools with > 20% failure rate, denied tool calls that might indicate misconfigured policies
5. **Cost anomalies** — per-agent cost spikes, org total spend trending above forecast
6. **Access patterns** — unusual PAT usage, failed auth spikes, cross-project access attempts
7. **KB health** — low search hit rates (might indicate stale embeddings), failed ingestion
8. **Queue health** — overflow events, queue depth trending up, drain rate declining

Output format is structured JSON with severity levels: `healthy`, `warning`, `critical`.

### Key design decisions

- **One observer per org** — sees all projects, agents, and resources. Broader view, lower cost.
- **Scheduled, not continuous** — wakes every 6h via existing scheduler infra. No persistent process.
- **Haiku/Groq only** — cheap model for structured analysis. ~500 tokens in, ~300 out per run. Cost: ~$0.001/run.
- **Pre-aggregated input** — observer gets metrics, not raw logs. Keeps context small and focused.
- **Not customer-visible** — `is_system: true` flag on agent. Excluded from `list_agents`, canvas, agent limits.
- **Writes to `system` log type** — findings go to `{org_id}/system/` in GCS for Helios.
- **Uses existing delivery infra** — webhook/email/Slack from Phase 8 scheduler.

### API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin/observer/reports` | List recent observer reports (platform admin) |
| GET | `/api/admin/observer/reports/{org_id}` | Reports for specific org |
| GET | `/api/observer/health` | Current org health summary (customer-facing) |
| POST | `/api/admin/observer/trigger/{org_id}` | Force an observer run (platform admin) |

### Frontend

- **Agent Health dashboard** (`/admin/agent-health`) — already exists, observer findings feed into health badges
- **New: Org Health widget** in customer Settings — overall health score, last observer run, top findings
- **New: Alert configuration** — which channels get observer alerts (webhook URL, email, Slack)

### Estimated effort: 2-3 sessions

---

## Implementation order

| Phase | What | Depends on | Files |
|-------|------|-----------|-------|
| **L1.1** | Wire `emit_agent_event` into agent engine execution loop | GCS sink done | `agent_engine.py` |
| **L1.2** | Wire tool_use, kb_search, delegation events | L1.1 | `agent_engine.py` |
| **L1.3** | Wire scaling, scheduler, memory events | L1.1 | `agent_scaling.py`, `agent_scheduler.py`, `agent_memory.py` |
| **L2.1** | Migration: `system_observer_reports` table | — | `045_add_system_observer.py` |
| **L2.2** | Observer runner: query + aggregate + LLM call | L1.1, L2.1 | `services/system_observer.py` |
| **L2.3** | Schedule observer via existing cron infra | L2.2 | `services/agent_scheduler.py`, `main.py` lifespan |
| **L2.4** | API endpoints for reports + trigger | L2.2 | `routes/admin.py` or new `routes/observer.py` |
| **L2.5** | Customer-facing health endpoint + Settings widget | L2.4 | `routes/observer.py`, `settings/page.tsx` |
| **L2.6** | Alert dispatch on critical findings | L2.2 | `services/system_observer.py` |

---

## Open questions

1. **Observer frequency** — 6h default, but should Enterprise/Scale get configurable intervals (1h, 2h)?
2. **Historical retention** — how long to keep observer reports? 90d like logs, or longer for compliance audit trail?
3. **Customer-facing** — how much of the observer's findings should customers see? Full report or just health badges?
4. **Multi-region** — when VPC Gateway Agent ships, does each region get its own observer or does the central one aggregate?
5. **Helios integration** — should the observer feed findings to Helios (on the Orin) for the self-healing loop, or does Helios run its own analysis from raw GCS logs?
