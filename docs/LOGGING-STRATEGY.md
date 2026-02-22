# Bonito Platform Logging & Observability Strategy

## Overview

Bonito's logging system provides hierarchical, structured observability across the entire platform with support for external integration destinations. It operates as an internal event bus that captures, stores, aggregates, and forwards platform events to enterprise logging tools.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Application Layer                        │
│  Gateway │ Auth │ Agents │ KB │ Admin │ Deployments │ Billing   │
└────────────────────────┬────────────────────────────────────────┘
                         │ emit()
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Log Service (async)                        │
│                                                                 │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Buffered │→ │  DB Writer   │  │  Integration Dispatcher  │  │
│  │  Queue   │→ │ (batch flush)│  │  (fan-out to providers)  │  │
│  └──────────┘  └──────────────┘  └──────────────────────────┘  │
└──────────────────────┬─────────────────────┬────────────────────┘
                       │                     │
              ┌────────▼────────┐    ┌───────▼────────────────┐
              │   PostgreSQL    │    │  External Destinations  │
              │  platform_logs  │    │  ┌─────────────────┐   │
              │  log_aggregates │    │  │ Datadog         │   │
              │  log_exports    │    │  │ Splunk HEC      │   │
              │  log_integrations│   │  │ CloudWatch      │   │
              └─────────────────┘    │  │ Elasticsearch   │   │
                                     │  │ Webhook         │   │
                                     │  │ Cloud Storage   │   │
                                     │  └─────────────────┘   │
                                     └────────────────────────┘
```

## Hierarchy

The logging hierarchy enables efficient querying at every level:

```
org_id (tenant isolation)
  └── log_type (feature area)
        ├── gateway      — API proxy requests, rate limits, key usage
        ├── auth         — login, logout, token refresh, SSO, password reset
        ├── agent        — execution start/complete/error, tool use
        ├── kb           — document upload, search, delete
        ├── admin        — user invite, role change, config change
        ├── deployment   — model deploy, scale, status change
        ├── billing      — cost alerts, usage thresholds
        └── compliance   — policy violations, governance events
              └── event_type (specific event)
                    ├── request, response, error, timeout
                    ├── login_success, login_failed, token_refresh
                    ├── agent_start, agent_complete, agent_error
                    └── ...
                          └── severity (debug, info, warn, error, critical)
                                └── metadata (JSONB — event-specific structured data)
```

## Data Model

### `platform_logs` — Primary event table
- **Partitioning consideration**: For high-volume orgs, time-based partitioning on `created_at` is recommended
- **Indexes**: Composite indexes on (org_id, log_type, created_at), (org_id, severity, created_at), GIN index on metadata JSONB
- **Retention**: Configurable per org (default 90 days), enforced by background job

### `log_integrations` — External destination config
- Per-org integration configurations
- Credentials stored in Vault at `log-integrations/{integration_id}`
- Supports enable/disable, test connectivity, last status tracking

### `log_export_jobs` — Async export tracking
- Supports CSV, JSON, Parquet export formats
- Progress tracking with percentage
- Time-limited download URLs

### `log_aggregations` — Pre-computed stats
- Daily and hourly buckets for dashboard performance
- Updated asynchronously after log emission
- Unique constraint prevents duplicate aggregation rows

## Log Service Design

### Core API
```python
await log_service.emit(
    org_id=uuid,
    log_type="gateway",        # Feature area
    event_type="request",      # Specific event
    severity="info",           # debug|info|warn|error|critical
    user_id=uuid,              # Optional: acting user
    resource_id=uuid,          # Optional: affected resource
    resource_type="model",     # Optional: resource type
    action="execute",          # Optional: CRUD action
    message="Processed request to gpt-4",
    metadata={"model": "gpt-4", "tokens": 150, "latency_ms": 230},
    duration_ms=230,
    cost=0.0045,
    trace_id=uuid,             # Optional: correlation ID
)
```

### Non-blocking Execution
1. `emit()` is fire-and-forget — adds to an in-memory buffer
2. Background task flushes buffer every 2 seconds or when 100 events accumulate
3. DB writes use batch INSERT for efficiency
4. Integration dispatch happens after DB write, in parallel per destination
5. Failures are logged but never propagate to the caller

### Batching Strategy
```
emit() → Buffer (deque, maxlen=10000)
              │
              ├── Flush trigger: 100 events OR 2 seconds elapsed
              │
              ▼
         Batch INSERT into platform_logs
              │
              ▼
         Fan-out to enabled integrations (per org)
```

## Integration Architecture

### Supported Destinations

| Provider | Protocol | Implementation | Status |
|----------|----------|----------------|--------|
| Datadog | HTTP API (v2/logs) | Full | ✅ |
| Splunk | HEC (HTTP Event Collector) | Full | ✅ |
| AWS CloudWatch | boto3 put_log_events | Full | ✅ |
| Elasticsearch | HTTP bulk API | Stub | 🔲 |
| Azure Monitor | Ingestion API | Stub | 🔲 |
| Google Cloud Logging | Client library | Stub | 🔲 |
| Webhook | Generic HTTP POST | Full | ✅ |
| S3/GCS/Azure Blob | Batch file upload | Stub | 🔲 |

### Credential Security
- Integration credentials stored in Vault at path `log-integrations/{id}`
- Credentials never returned in API responses (write-only)
- Config (non-sensitive) stored in JSONB column
- AES-GCM encrypted fallback in DB when Vault unavailable

### Test Connectivity
Each integration supports a `test()` method that:
1. Sends a test log event to the destination
2. Validates credentials and configuration
3. Returns success/failure with diagnostic message
4. Updates `last_test_status` and `last_test_at` on the integration record

## API Design

### Log Querying
```
GET /api/logs?log_type=gateway&severity=error&from=2026-01-01&to=2026-02-01&page=1&page_size=50
```
- Scoped to user's org automatically
- Supports all hierarchy levels as filters
- Full-text search on message field
- Date range filtering with ISO 8601

### Log Statistics
```
GET /api/logs/stats?range=7d&granularity=hourly
```
- Returns volume by type, severity over time
- Powered by pre-computed aggregations table
- Falls back to live query for custom ranges

### Integration Management
```
POST   /api/log-integrations          — create
GET    /api/log-integrations          — list (credentials masked)
PUT    /api/log-integrations/{id}     — update
DELETE /api/log-integrations/{id}     — delete
POST   /api/log-integrations/{id}/test — test connectivity
```

### Export
```
GET /api/logs/export?format=csv&log_type=auth&from=2026-01-01
```
- Creates async export job
- Returns job ID for polling
- Download URL when complete

## Instrumentation Points

### Gateway (log_type: "gateway")
- Every proxied request: model, tokens, latency, status, cost
- Rate limit hits, key validation failures
- Bridges existing `gateway_requests` table data

### Auth (log_type: "auth")
- Login success/failure (with IP, user agent)
- Logout, token refresh
- SSO events, password reset
- Email verification

### Agents (log_type: "agent")
- Session start, complete, error
- Tool invocations with results
- Token usage per turn

### Knowledge Base (log_type: "kb")
- Document upload, processing complete
- Search queries with result counts
- Document deletion

### Admin (log_type: "admin")
- User invitations, role changes
- Organization config changes
- Integration create/update/delete

## Frontend

### Log Viewer (`/logs`)
- Real-time log stream with auto-refresh
- Filterable by all hierarchy levels
- Severity-colored rows (debug=gray, info=blue, warn=amber, error=red, critical=purple)
- Expandable rows showing full metadata
- Export button (CSV/JSON)

### Integration Management (`/settings/integrations`)
- Card-based UI for each integration type
- Create/edit modal with type-specific config fields
- Test connectivity button with live status
- Enable/disable toggle

### Log Stats Dashboard
- Volume over time chart (line/bar)
- Breakdown by severity (pie/donut)
- Breakdown by type (stacked bar)
- Top errors table

## Performance Considerations

1. **Buffer prevents DB pressure**: Logs are batched, not written one-by-one
2. **Aggregation table**: Dashboard stats served from pre-computed data
3. **Composite indexes**: Queries always hit covering indexes
4. **GIN index on metadata**: Supports efficient JSONB queries
5. **Async integration dispatch**: External calls never block the request path
6. **Connection pooling**: Reuses DB connections via SQLAlchemy async pool

## Future Enhancements

- [ ] Time-based table partitioning for platform_logs (by month)
- [ ] Configurable per-org retention policies with auto-cleanup
- [ ] Real-time log streaming via WebSocket
- [ ] Log-based alerting rules (e.g., "alert when error rate > 5%")
- [ ] Correlation/tracing view (group events by trace_id)
- [ ] Sampling for high-volume debug logs
