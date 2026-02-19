# Bonito Logging and Observability Strategy

## Overview

This document outlines the comprehensive logging and observability system for the Bonito enterprise AI control plane. The system is designed to provide hierarchical, queryable, and exportable logs with seamless integration to external industry-standard observability tools.

## Architecture Principles

1. **Hierarchical Organization**: Logs are organized in a customer → feature area → event type hierarchy
2. **Non-Blocking**: Logging never blocks the main application flow
3. **Scalable**: Designed for high-throughput environments with batching and async processing
4. **Extensible**: Support for multiple external integrations
5. **Compliant**: Meets enterprise audit and compliance requirements

## Log Schema

### Hierarchical Structure

```
org_id (top level) → log_type (feature area) → event_type → metadata
```

### Core Schema

```json
{
  "org_id": "uuid",                    // Customer ID (top level)
  "log_type": "gateway|agent|auth|admin|kb|deployment|billing",  // Feature area
  "event_type": "string",              // Specific event within the feature area
  "severity": "debug|info|warn|error|critical",
  "timestamp": "ISO-8601",
  "trace_id": "uuid",                  // For distributed tracing
  "user_id": "uuid",                   // Actor who performed the action
  "resource_id": "uuid",               // Resource being acted upon
  "resource_type": "model|agent|project|group|kb|deployment|policy",
  "action": "create|read|update|delete|execute|search",
  "metadata": {},                      // Event-specific structured data
  "duration_ms": 0,                    // For timed operations
  "cost": 0.0                         // For billable operations
}
```

### Event Types by Log Type

#### Gateway (`log_type: "gateway"`)
- `request` - API requests through the gateway
- `error` - Gateway errors and failures
- `rate_limit` - Rate limiting events
- `provider_failover` - Provider failover events

#### Agent (`log_type: "agent"`)
- `execute` - Agent execution events
- `tool_use` - Tool usage within agents
- `error` - Agent execution errors

#### Auth (`log_type: "auth"`)
- `login` - User login events
- `logout` - User logout events
- `token_refresh` - Token refresh events
- `sso_auth` - SSO authentication events
- `failed_auth` - Failed authentication attempts

#### Admin (`log_type: "admin"`)
- `user_invite` - User invitations
- `role_change` - Role and permission changes
- `config_change` - System configuration changes
- `policy_update` - Policy updates

#### Knowledge Base (`log_type: "kb"`)
- `upload` - Document uploads
- `search` - Knowledge base searches
- `delete` - Document deletions
- `ingestion` - Document processing events

#### Deployment (`log_type: "deployment"`)
- `create` - Deployment creation
- `update` - Deployment updates
- `delete` - Deployment deletions
- `status_change` - Deployment status changes

#### Billing (`log_type: "billing"`)
- `usage_calculation` - Usage calculations
- `invoice_generation` - Invoice generation
- `cost_alert` - Cost alerts and notifications

## Database Schema

### Tables

#### `platform_logs`
Primary logging table with monthly partitioning strategy:
- Partitioned by `created_at` (monthly)
- Indexed on `(org_id, log_type, created_at)`
- TTL policy: 13 months retention
- JSON metadata column for flexible event-specific data

#### `log_integrations`
Per-organization external integrations:
- Encrypted credential storage
- Integration-specific configuration
- Health monitoring and status tracking

#### `log_export_jobs`
Async export job tracking:
- Export format (CSV, JSON)
- Status tracking (pending, running, completed, failed)
- Progress monitoring

### Indexing Strategy

1. **Primary Queries**:
   - `(org_id, log_type, created_at)` - Main query path
   - `(org_id, user_id, created_at)` - User activity queries
   - `(org_id, resource_id, created_at)` - Resource-specific logs

2. **Trace Queries**:
   - `(trace_id)` - Distributed tracing
   - `(org_id, trace_id)` - Scoped trace queries

## Core Services

### Log Service (`app/services/log_service.py`)

The central logging service with the following key methods:

```python
async def emit(
    org_id: UUID,
    log_type: str,
    event_type: str,
    severity: str,
    user_id: Optional[UUID] = None,
    resource_id: Optional[UUID] = None,
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    metadata: Optional[Dict] = None,
    duration_ms: Optional[int] = None,
    cost: Optional[float] = None,
    trace_id: Optional[UUID] = None
) -> None
```

**Features**:
- Async/non-blocking design
- Batching for high throughput (configurable batch size and flush interval)
- Automatic retry logic for failed writes
- Circuit breaker for external integrations

### Integration Service (`app/services/log_integrations.py`)

Manages external log destinations with support for:

#### Tier 1 Integrations (Fully Implemented)
1. **Datadog** - HTTP API to logs endpoint
2. **Splunk** - HTTP Event Collector (HEC)
3. **AWS CloudWatch** - boto3 SDK

#### Tier 2 Integrations (Stub Implementation)
4. **Elasticsearch/OpenSearch** - HTTP API
5. **Azure Monitor** - Ingestion API
6. **Google Cloud Logging** - Client library
7. **Generic Webhook** - HTTP POST to custom endpoints
8. **Cloud Storage** - S3/GCS/Azure Blob batch export

#### Integration Configuration
Each integration supports:
- Per-org configuration
- Encrypted credential storage using Vault
- Health checks and status monitoring
- Retry logic and error handling
- Rate limiting and batching

### Query Service

Provides efficient log querying capabilities:
- Time-range queries with pagination
- Multi-dimensional filtering (org, log_type, severity, etc.)
- Full-text search on metadata
- Aggregation queries for dashboards

## API Endpoints

### Log Query API
```
GET /api/logs
  ?org_id=uuid
  &log_type=gateway,agent
  &event_type=request,error
  &severity=error,critical
  &start_date=2024-01-01T00:00:00Z
  &end_date=2024-01-31T23:59:59Z
  &user_id=uuid
  &resource_id=uuid
  &limit=100
  &offset=0
```

### Export API
```
POST /api/logs/export
{
  "filters": { ... },
  "format": "csv|json",
  "delivery": "download|email|integration"
}
```

### Integration Management
```
POST /api/log-integrations
PUT /api/log-integrations/{id}
GET /api/log-integrations
DELETE /api/log-integrations/{id}
POST /api/log-integrations/{id}/test
```

### Analytics API
```
GET /api/logs/stats
  ?metric=volume,errors,top_users
  &groupby=hour,day,week
  &org_id=uuid
```

## Instrumentation Strategy

### Existing Code Integration

The system will instrument key flows in the existing codebase:

1. **Gateway Service**:
   - Bridge existing `GatewayRequest` logs to new system
   - Log provider failovers and rate limiting
   - Track request routing decisions

2. **Auth Events**:
   - Login/logout events
   - Token operations
   - SSO authentication flows

3. **Agent Operations**:
   - Agent execution lifecycle
   - Tool usage and results
   - Error conditions and failures

4. **Knowledge Base**:
   - Document upload and processing
   - Search queries and results
   - RAG retrieval operations

5. **Admin Actions**:
   - User management operations
   - Policy and configuration changes
   - System administration events

### Implementation Pattern

```python
from app.services.log_service import log_service

# Within existing service methods
await log_service.emit(
    org_id=org_id,
    log_type="gateway",
    event_type="request",
    severity="info",
    user_id=user_id,
    metadata={
        "model": request.model,
        "provider": provider,
        "tokens": usage.total_tokens
    },
    duration_ms=elapsed_ms,
    cost=calculated_cost
)
```

## Data Retention and Archival

### Retention Policy
- **Hot Storage**: 3 months in primary database
- **Warm Storage**: 10 months in compressed format
- **Cold Storage**: Long-term archival to object storage
- **Purge**: Complete deletion after regulatory requirements

### Compliance Features
- Immutable audit trail
- Data export capabilities for compliance audits
- Role-based access control for log access
- Retention policy enforcement

## Performance Considerations

### High-Throughput Design
- Async logging with configurable batching
- Connection pooling for external integrations
- Circuit breakers to prevent cascading failures
- Background processing for non-critical operations

### Scalability
- Database partitioning by time
- Horizontal scaling of log processing workers
- Caching for frequently accessed data
- Efficient indexing strategy

### Monitoring
- Service health metrics
- Log ingestion rate monitoring
- External integration status
- Error rate and latency tracking

## Security

### Data Protection
- Encryption at rest and in transit
- PII detection and masking
- Secure credential management via Vault
- Access logging and audit trails

### Access Control
- Organization-scoped data access
- Role-based permissions for log access
- API key authentication for exports
- Rate limiting on query endpoints

## Migration Strategy

### Phase 1: Foundation
- Deploy database schema
- Implement core log service
- Basic instrumentation of gateway

### Phase 2: Integration
- Implement Tier 1 external integrations
- Add instrumentation for auth and admin events
- Deploy query and export APIs

### Phase 3: Enhancement
- Add Tier 2 integrations
- Implement advanced analytics
- Deploy frontend interface

### Phase 4: Optimization
- Performance tuning and optimization
- Advanced features (alerting, anomaly detection)
- Full compliance feature set

## Monitoring and Alerting

The logging system itself will be monitored for:
- Log ingestion rate and latency
- External integration health
- Database performance metrics
- Error rates and system health

Critical alerts will be configured for:
- Log ingestion failures
- External integration outages
- Unusual log patterns or volumes
- System performance degradation

This comprehensive strategy ensures that Bonito provides enterprise-grade logging and observability capabilities while maintaining high performance and reliability.