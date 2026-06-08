# Bonito MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that wraps the **Bonito AI Platform** REST API. Use it from Claude Desktop, Cursor, or any MCP-compatible client to manage your multi-provider AI infrastructure.

## Features

- **Provider Management** – Connect and verify AWS Bedrock, Azure OpenAI, GCP Vertex AI, OpenAI, Anthropic, and Groq
- **Model Management** – List, sync, and activate models across providers
- **Unified Gateway** – Send chat completions through Bonito's OpenAI-compatible gateway
- **Projects** – List and create projects (containers for agents, KBs, budgets)
- **Agent Management** – Create and execute BonBon and Bonobot agents
- **Knowledge Bases** – Create KBs, upload inline documents, and link KBs to agents for RAG
- **Cost & Observability** – Track costs per provider and view gateway logs

Total: 22 tools (was 18 before the 2026-06-07 audit pass).

## Audit notes (2026-06-07)

Tools added in the latest audit pass: `list_projects`, `create_project`, `upload_to_kb`, `link_kb_to_agent`. Without these, KBs were inert (no way to load docs via MCP) and agents couldn't be scoped to projects (which the post-Phase 1 create_agent flow requires).

Still missing from this MCP surface relative to the live platform — flag for the next pass:

- Access-token CRUD (`bp-` and `bj-` create/list/revoke)
- Image generation (`POST /v1/images/generations`)
- Video generation (`POST /v1/videos` + status + content)
- Agent-to-agent connections (`connect_agents` — handoff / escalation / data_feed / trigger)
- Agent updates (`update_agent`)
- Tier-aware model listing (current `list_models` is unfiltered)
- Origami tool surface (16 tools) is intentionally separate; do NOT mirror into MCP without product review.

## Quick Start

### Install from source

```bash
git clone https://github.com/ShabariRepo/bonito.git
cd bonito/mcp-server
pip install -e .
```

### Set your API key

```bash
export BONITO_API_KEY="your-bonito-api-key"
```

### Run (stdio – for Claude Desktop)

```bash
bonito-mcp
```

### Run (SSE – for network clients)

```bash
bonito-mcp --transport sse --port 8080
```

## Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "bonito": {
      "command": "bonito-mcp",
      "env": {
        "BONITO_API_KEY": "your-bonito-api-key"
      }
    }
  }
}
```

## Docker

```bash
docker build -t bonito-mcp .
docker run -e BONITO_API_KEY="your-key" -p 8080:8080 bonito-mcp
```

## Available Tools

| Tool | Description |
|------|-------------|
| `list_providers` | List connected AI providers |
| `connect_provider` | Connect a new provider |
| `verify_provider` | Verify provider credentials |
| `list_models` | List models (with filters) |
| `sync_models` | Sync models from providers |
| `activate_model` | Activate a model for the gateway |
| `chat_completion` | Send a chat completion request |
| `list_gateway_keys` | List gateway API keys |
| `create_gateway_key` | Create a new gateway key |
| `gateway_usage` | View usage statistics |
| `list_agents` | List agents in a project |
| `create_agent` | Create a BonBon or Bonobot agent |
| `execute_agent` | Execute an agent |
| `get_agent` | Get agent details |
| `list_knowledge_bases` | List knowledge bases |
| `create_knowledge_base` | Create a knowledge base |
| `get_costs` | Get cost breakdown by provider |
| `get_gateway_logs` | View gateway request logs |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BONITO_API_KEY` | Yes | – | Your Bonito API key |
| `BONITO_API_URL` | No | `https://api.getbonito.com` | API base URL |

## License

MIT
