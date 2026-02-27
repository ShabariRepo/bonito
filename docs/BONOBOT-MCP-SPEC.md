# Bonobot MCP Integration — Architecture Specification

> **Status:** RFC / Draft  
> **Author:** Bonito Engineering  
> **Date:** 2026-02-26  
> **Target Release:** v0.9.0

---

## 1. Overview

This document specifies how **Model Context Protocol (MCP)** support is integrated into the Bonobot agent platform. MCP is becoming the universal standard for agent ↔ tool/data interaction, with native support from AWS, GCP, Azure, and the broader AI ecosystem.

### Goals

1. **MCP as a first-class connector type** in Bonito's Resource Connector framework
2. **Agent engine as MCP client**, connecting to MCP servers (local stdio or remote HTTP/streamable-HTTP)
3. **Per-agent scoping** — each Bonobot can have multiple MCP server connections
4. **Governance-first** — all MCP interactions go through Bonito's security layer (audit trail, budget tracking, tool policy enforcement)
5. **Zero-config cloud templates** for AWS, GCP, and Azure MCP servers

### Non-Goals (v1)

- Bonito acting as an MCP **server** (exposing agent capabilities to external MCP clients)
- MCP resource/prompt primitives (only `tools/list` and `tools/call` in v1)
- MCP sampling support

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Bonito Platform                       │
│                                                              │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────────┐  │
│  │  Admin UI │───▶│  MCP Server  │    │   Agent Engine     │  │
│  │  (CRUD)   │    │  Registry    │    │                    │  │
│  └──────────┘    │  (DB model)  │◀───│  ┌──────────────┐ │  │
│                  └──────────────┘    │  │  MCP Client   │ │  │
│                                      │  │  Manager      │ │  │
│                                      │  └──────┬───────┘ │  │
│                                      └─────────┼─────────┘  │
│                                                │              │
│  ┌─────────────────────────────────────────────┤              │
│  │           Governance Layer                   │              │
│  │  • Tool policy enforcement                  │              │
│  │  • Audit trail logging                      │              │
│  │  • Budget tracking                          │              │
│  │  • Rate limiting                            │              │
│  └─────────────────────────────────────────────┤              │
└────────────────────────────────────────────────┼──────────────┘
                                                 │
                    ┌────────────────────────────┼────────────┐
                    │          MCP Servers        │            │
                    │                             ▼            │
                    │  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
                    │  │  stdio  │  │  HTTP/   │  │  Cloud   │ │
                    │  │  local  │  │  SSE     │  │  MCP     │ │
                    │  │ process │  │  remote  │  │ services │ │
                    │  └─────────┘  └─────────┘  └─────────┘ │
                    │  (awslabs/     (custom)     (Vertex AI, │
                    │   mcp, etc.)                 Bedrock)   │
                    └─────────────────────────────────────────┘
```

---

## 3. Data Model

### 3.1 `agent_mcp_servers` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `agent_id` | UUID (FK → agents) | Owning agent |
| `org_id` | UUID (FK → organizations) | Org for isolation |
| `name` | VARCHAR(255) | Human-readable server name |
| `transport_type` | VARCHAR(10) | `stdio` or `http` |
| `endpoint_config` | JSONB | Transport-specific config (see §3.2) |
| `auth_config` | JSONB | Authentication config (see §3.3) |
| `enabled` | BOOLEAN | Whether this server is active |
| `discovered_tools` | JSONB | Cached tool list from last discovery |
| `last_connected_at` | TIMESTAMP | Last successful connection time |
| `created_at` | TIMESTAMP | Record creation time |
| `updated_at` | TIMESTAMP | Last update time |

### 3.2 `endpoint_config` Schema

**For `stdio` transport:**
```json
{
  "command": "npx",
  "args": ["-y", "@aws/mcp-server-s3"],
  "env": {
    "AWS_REGION": "us-east-1"
  },
  "cwd": "/opt/mcp-servers"
}
```

**For `http` transport:**
```json
{
  "url": "https://mcp.example.com/sse",
  "headers": {
    "X-Custom-Header": "value"
  }
}
```

### 3.3 `auth_config` Schema

```json
{
  "type": "bearer_token",
  "token": "encrypted:xxxxx"
}
```

Supported auth types:
- `none` — no authentication
- `bearer_token` — Bearer token in Authorization header
- `api_key` — API key in custom header
- `oauth2` — OAuth 2.0 client credentials flow (future)

---

## 4. MCP Client Architecture

### 4.1 Connection Lifecycle

```
Agent Session Start
       │
       ▼
┌──────────────┐     ┌───────────────────┐
│ Load agent's │────▶│ For each enabled  │
│ MCP servers  │     │ MCP server:       │
└──────────────┘     │                   │
                     │ 1. Connect        │
                     │ 2. Initialize     │
                     │ 3. tools/list     │
                     │ 4. Cache tools    │
                     └───────────────────┘
                              │
                              ▼
                     ┌───────────────────┐
                     │ Merge MCP tools   │
                     │ into agent's tool │
                     │ definitions       │
                     └───────────────────┘
                              │
                              ▼
                     ┌───────────────────┐
                     │ Agent loop runs   │──┐
                     │ (LLM ↔ tools)     │  │ On MCP tool call:
                     └───────────────────┘  │ tools/call → MCP server
                              │             │ Apply governance
                              ▼             │
                     ┌───────────────────┐◀─┘
                     │ Session ends      │
                     │ Close connections │
                     └───────────────────┘
```

### 4.2 Tool Namespacing

MCP tools are namespaced to avoid collisions with built-in tools:

```
mcp_{server_name}_{tool_name}
```

Example: An MCP server named "aws-s3" with tool "list_buckets" becomes `mcp_aws_s3_list_buckets` in the agent's tool list.

### 4.3 Connection Pooling

- **stdio transports:** One subprocess per agent session. Process is killed when session ends.
- **HTTP transports:** Shared `httpx.AsyncClient` pool per MCP server. Connection reuse across sessions.
- **Timeout:** 30s connect, 60s read for HTTP. 10s startup for stdio.

### 4.4 Error Handling

| Scenario | Behavior |
|----------|----------|
| MCP server unreachable | Log warning, skip server, agent runs with remaining tools |
| Tool call timeout | Return error result to LLM, continue loop |
| Auth failure (401/403) | Return error, mark server as `needs_reauth` |
| Server process crash (stdio) | Attempt single reconnect, then skip |

---

## 5. Security & Governance

### 5.1 Tool Policy Integration

MCP tools are subject to the **same tool policy** as built-in tools:

- **Mode `none`:** MCP tools blocked (default)
- **Mode `allowlist`:** Only explicitly listed MCP tools allowed (by namespaced name)
- **Mode `denylist`:** All MCP tools allowed except denied ones
- **Mode `all`:** All MCP tools allowed

### 5.2 Audit Trail

Every MCP tool call generates an audit log entry:

```json
{
  "action": "agent_tool_call",
  "resource_type": "mcp_tool",
  "resource_id": "mcp_aws_s3_list_buckets",
  "details": {
    "mcp_server_id": "uuid",
    "mcp_server_name": "aws-s3",
    "tool_name": "list_buckets",
    "arguments": { "bucket_prefix": "data-" },
    "execution_time_ms": 245,
    "parent_execution": "audit-uuid"
  }
}
```

### 5.3 Budget Tracking

MCP tool calls do not consume LLM tokens directly, but:
- The LLM turns that generate MCP tool calls are tracked normally
- MCP tool execution time is tracked in audit logs
- Future: per-MCP-server cost tracking for paid APIs

### 5.4 Secrets Management

- Auth tokens are stored encrypted in `auth_config`
- Tokens are never logged or returned in API responses
- `auth_config` is redacted in GET responses (returns `{ "type": "bearer_token", "configured": true }`)

---

## 6. API Endpoints

### 6.1 MCP Server CRUD

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/agents/{agent_id}/mcp-servers` | Register MCP server |
| `GET` | `/api/agents/{agent_id}/mcp-servers` | List MCP servers |
| `GET` | `/api/agents/{agent_id}/mcp-servers/{server_id}` | Get server details + tools |
| `PUT` | `/api/agents/{agent_id}/mcp-servers/{server_id}` | Update config |
| `DELETE` | `/api/agents/{agent_id}/mcp-servers/{server_id}` | Remove server |
| `POST` | `/api/agents/{agent_id}/mcp-servers/{server_id}/test` | Test connection |

### 6.2 Request/Response Examples

**POST /api/agents/{agent_id}/mcp-servers**
```json
{
  "name": "aws-s3",
  "transport_type": "stdio",
  "endpoint_config": {
    "command": "npx",
    "args": ["-y", "@aws/mcp-server-s3"],
    "env": { "AWS_REGION": "us-east-1" }
  },
  "auth_config": { "type": "none" },
  "enabled": true
}
```

**GET /api/agents/{agent_id}/mcp-servers/{server_id}**
```json
{
  "id": "uuid",
  "agent_id": "uuid",
  "name": "aws-s3",
  "transport_type": "stdio",
  "endpoint_config": { "command": "npx", "args": [...] },
  "auth_config": { "type": "none", "configured": false },
  "enabled": true,
  "discovered_tools": [
    {
      "name": "list_buckets",
      "description": "List S3 buckets",
      "input_schema": { "type": "object", "properties": {} }
    }
  ],
  "last_connected_at": "2026-02-26T10:00:00Z",
  "created_at": "2026-02-26T09:00:00Z"
}
```

**POST /api/agents/{agent_id}/mcp-servers/{server_id}/test**
```json
{
  "status": "connected",
  "tools_discovered": 12,
  "tools": [
    { "name": "list_buckets", "description": "List S3 buckets" },
    { "name": "get_object", "description": "Get an S3 object" }
  ],
  "latency_ms": 320
}
```

---

## 7. Pre-built Cloud MCP Templates

### 7.1 AWS MCP Template

Pre-configured for `awslabs/mcp` server suite:

| Template | Server | Tools |
|----------|--------|-------|
| AWS S3 | `@aws/mcp-server-s3` | list_buckets, get_object, put_object, ... |
| AWS Bedrock KB | `@aws/mcp-server-bedrock-kb` | retrieve, retrieve_and_generate |
| AWS DynamoDB | `@aws/mcp-server-dynamodb` | get_item, put_item, query, scan |
| AWS Lambda | `@aws/mcp-server-lambda` | invoke_function, list_functions |
| AWS CloudWatch | `@aws/mcp-server-cloudwatch-logs` | get_log_events, filter_log_events |

### 7.2 GCP MCP Template

| Template | Endpoint | Tools |
|----------|----------|-------|
| Vertex AI Search | `gcloud beta services mcp` endpoint | search, retrieve |

### 7.3 Azure MCP Template

> **Note:** `Azure/azure-mcp` was archived February 2026. MCP support has moved into Azure AI Foundry and Semantic Kernel. Templates will be updated when stable endpoints are available.

| Template | Status | Notes |
|----------|--------|-------|
| Azure AI Foundry | Placeholder | Use Semantic Kernel MCP client integration |

---

## 8. Frontend Integration

### 8.1 MCP Servers Tab

New tab in the agent detail panel (alongside Chat, Configure, Sessions, Metrics):

- **Server list** with status indicators (connected/disconnected/error)
- **Add MCP Server** form with transport type selector
- **Template picker** for cloud MCP servers
- **Tool discovery** view — expandable list of discovered tools per server
- **Enable/disable toggle** per server

### 8.2 Tool Policy UI Update

The tool policy configuration UI is extended to show MCP tools alongside built-in tools, allowing admins to include/exclude specific MCP tools.

---

## 9. Implementation Plan

### Phase 1: Core (This PR)
- [x] DB model + migration
- [x] MCP client module (stdio + HTTP)
- [x] Agent engine integration
- [x] CRUD API endpoints
- [x] Frontend MCP Servers tab
- [x] Cloud MCP templates
- [x] Tests

### Phase 2: Future
- [ ] MCP resource primitives (file access, data retrieval)
- [ ] MCP prompt primitives
- [ ] OAuth 2.0 auth flow for MCP servers
- [ ] MCP server health monitoring dashboard
- [ ] Per-MCP-server cost tracking
- [ ] Bonito as MCP server (expose agent capabilities)

---

## 10. References

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk)
- [AWS MCP Servers](https://github.com/awslabs/mcp)
- [GCP Vertex AI MCP](https://cloud.google.com/vertex-ai/docs/mcp)
- [Azure AI Foundry](https://learn.microsoft.com/en-us/azure/ai-studio/)
