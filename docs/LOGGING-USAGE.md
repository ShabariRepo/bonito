# Bonito Logging System Usage Guide

This guide covers how to use the comprehensive logging and observability system in the Bonito platform.

## Overview

The Bonito logging system provides:
- **Hierarchical Logging**: Organized by `org_id` → `log_type` → `event_type`
- **External Integrations**: Forward logs to Datadog, Splunk, CloudWatch, and more
- **Rich Querying**: Filter, search, and analyze logs through the web interface
- **Export Capabilities**: Export logs in CSV, JSON formats
- **Real-time Processing**: High-performance async logging with batching

## Log Schema

Every log entry follows this hierarchical structure:

```json
{
  "org_id": "uuid",                    // Customer (top level)
  "log_type": "gateway|agent|auth|admin|kb|deployment|billing",
  "event_type": "request|error|login|...",  // Specific event
  "severity": "debug|info|warn|error|critical",
  "timestamp": "2024-02-19T17:30:00Z",
  "trace_id": "uuid",                  // For request tracing
  "user_id": "uuid",                   // Who performed the action
  "resource_id": "uuid",               // What was acted upon
  "resource_type": "model|agent|kb|...",
  "action": "create|read|update|delete|execute|search",
  "metadata": {},                      // Event-specific data
  "duration_ms": 250,                  // Operation duration
  "cost": 0.045,                       // Cost in USD
  "message": "Human readable description"
}
```

## Using the Logging Service

### Basic Logging in Backend Services

```python
from app.services.log_service import log_service

# Basic log emission
await log_service.emit(
    org_id=org_id,
    log_type="gateway",
    event_type="request",
    severity="info",
    user_id=user_id,
    metadata={
        "model": "gpt-4o",
        "provider": "openai",
        "tokens": 1500
    },
    duration_ms=2500,
    cost=0.045,
    message="Completed chat completion request"
)
```

### Convenience Methods

The logging service provides convenience methods for common scenarios:

```python
# Gateway requests
await log_service.emit_gateway_request(
    org_id=org_id,
    user_id=user_id,
    model="gpt-4o",
    provider="openai",
    status="success",
    duration_ms=2500,
    cost=0.045,
    input_tokens=1200,
    output_tokens=300
)

# Authentication events
await log_service.emit_auth_event(
    org_id=org_id,
    event_type="login",
    user_id=user_id,
    success=True,
    metadata={"ip_address": "192.168.1.100"}
)

# Admin actions
await log_service.emit_admin_action(
    org_id=org_id,
    admin_user_id=admin_user_id,
    event_type="user_invite",
    target_user_id=new_user_id,
    metadata={"email": "newuser@company.com"}
)

# Knowledge base operations
await log_service.emit_kb_event(
    org_id=org_id,
    event_type="search",
    user_id=user_id,
    kb_id=kb_id,
    duration_ms=150,
    metadata={"query": "search terms", "results_count": 5}
)

# Agent operations
await log_service.emit_agent_event(
    org_id=org_id,
    event_type="execute",
    user_id=user_id,
    agent_id=agent_id,
    duration_ms=5000,
    cost=0.12,
    metadata={"tools_used": ["search", "calculator"]}
)
```

## Web Interface

### Viewing Logs

1. Navigate to `/logs` in the dashboard
2. Use filters to narrow down results:
   - **Log Type**: gateway, agent, auth, admin, kb, deployment, billing
   - **Event Type**: request, error, login, etc.
   - **Severity**: debug, info, warn, error, critical
   - **Date Range**: Filter by time period
   - **Search**: Full-text search in messages and metadata

3. Sort and paginate through results
4. View detailed information including:
   - Timestamp and duration
   - User and resource information
   - Cost and performance metrics
   - Structured metadata

### Exporting Logs

1. Apply filters to select desired logs
2. Click "Export CSV" or "Export JSON"
3. Monitor export job progress
4. Download completed exports

### Managing Integrations

1. Navigate to `/logs/integrations`
2. Click "Add Integration" to create new external destinations
3. Configure supported integrations:
   - **Datadog**: Requires API key
   - **Splunk**: Requires HEC token and host
   - **AWS CloudWatch**: Requires AWS credentials and log group

4. Test integrations to verify connectivity
5. Enable/disable integrations as needed

## API Usage

### Querying Logs

```bash
POST /api/logs/query
Content-Type: application/json

{
  "filters": {
    "log_types": ["gateway", "auth"],
    "severities": ["error", "critical"],
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-01-31T23:59:59Z",
    "search": "timeout"
  },
  "limit": 100,
  "offset": 0,
  "sort_by": "created_at",
  "sort_order": "desc"
}
```

### Trace-based Queries

```bash
GET /api/logs/trace/{trace_id}
```

Returns all logs associated with a specific trace ID for distributed tracing.

### Creating Export Jobs

```bash
POST /api/logs/export
Content-Type: application/json

{
  "filters": {
    "log_types": ["gateway"],
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-01-31T23:59:59Z"
  },
  "export_format": "csv",
  "include_metadata": true,
  "email_when_complete": true
}
```

### Managing Integrations

```bash
# Create integration
POST /api/logs/integrations
Content-Type: application/json

{
  "name": "Production Datadog",
  "integration_type": "datadog",
  "config": {
    "site": "datadoghq.com",
    "service": "bonito",
    "tags": ["env:prod"]
  },
  "credentials": {
    "api_key": "your-datadog-api-key"
  },
  "enabled": true
}

# Test integration
POST /api/logs/integrations/{id}/test

# List integrations
GET /api/logs/integrations
```

## Log Types and Events

### Gateway (`log_type: "gateway"`)
- `request`: API requests through the gateway
- `error`: Gateway errors and failures  
- `rate_limit`: Rate limiting events
- `provider_failover`: Provider failover events

### Authentication (`log_type: "auth"`)
- `login`: User login attempts
- `logout`: User logout events
- `token_refresh`: Token refresh operations
- `sso_auth`: SSO authentication events
- `failed_auth`: Failed authentication attempts

### Admin (`log_type: "admin"`)
- `user_invite`: User invitation events
- `role_change`: Role and permission changes
- `config_change`: System configuration changes
- `policy_update`: Policy modifications

### Knowledge Base (`log_type: "kb"`)
- `upload`: Document upload events
- `search`: Knowledge base searches
- `delete`: Document deletion events
- `ingestion`: Document processing events

### Agent (`log_type: "agent"`)
- `execute`: Agent execution events
- `tool_use`: Tool usage within agents
- `error`: Agent execution errors

### Deployment (`log_type: "deployment"`)
- `create`: Deployment creation
- `update`: Deployment updates
- `delete`: Deployment deletion
- `status_change`: Deployment status changes

### Billing (`log_type: "billing"`)
- `usage_calculation`: Usage calculations
- `invoice_generation`: Invoice generation  
- `cost_alert`: Cost alerts and notifications

## Performance Considerations

The logging system is designed for high performance:

- **Async Processing**: Never blocks main request flow
- **Batching**: Groups log entries for efficient database writes
- **Circuit Breakers**: Protects against external integration failures
- **Indexed Queries**: Optimized database indexes for common query patterns
- **Aggregation Tables**: Pre-computed statistics for dashboard performance

## Troubleshooting

### Common Issues

1. **Logs not appearing**: Check if log service is properly imported and called
2. **Integration test failures**: Verify credentials and network connectivity
3. **High latency**: Check if external integrations are experiencing issues
4. **Missing metadata**: Ensure metadata is JSON serializable

### Debugging

```python
import logging
logger = logging.getLogger(__name__)

# Enable debug logging for the log service
logging.getLogger("app.services.log_service").setLevel(logging.DEBUG)
```

## Migration from Legacy Logging

If migrating from existing logging patterns:

1. **Gateway Requests**: Already bridged automatically
2. **Custom Logs**: Replace with `log_service.emit()` calls
3. **External Forwarding**: Configure integrations instead of custom forwarding
4. **Analytics**: Use new query APIs instead of direct database queries

## Best Practices

1. **Use Appropriate Severity Levels**:
   - `debug`: Detailed diagnostic information
   - `info`: General operational messages
   - `warn`: Warning conditions that don't stop operation
   - `error`: Error conditions that may affect operation
   - `critical`: Critical conditions that require immediate attention

2. **Include Relevant Metadata**: Add structured data that helps with debugging and analysis

3. **Use Trace IDs**: Link related operations across services

4. **Monitor Performance**: Use duration_ms and cost fields for performance tracking

5. **Consistent Event Types**: Use standardized event type names across services

For more information, see the [Architecture Document](LOGGING-STRATEGY.md).