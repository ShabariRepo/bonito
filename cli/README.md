# 🐟 Bonito CLI

Unified multi-cloud AI management from your terminal.

Bonito gives enterprise AI teams a single CLI to manage models, costs, and workloads across AWS Bedrock, Azure OpenAI, Google Vertex AI, and more.

## Install

```bash
pip install bonito-cli
```

## Quick Start

```bash
bonito auth login                           # Authenticate
bonito models list                          # Browse 381+ models across 3 clouds
bonito projects create --name "My Project" # Create a project
bonito agents create --project <id> --name "Assistant" --prompt "You are a helpful AI assistant"
bonito agents execute <agent-id> "Hello!"  # Execute agent
bonito chat -m gpt-4o                      # Interactive chat
bonito kb create --name docs               # Create a knowledge base
```

## Commands

| Command | Description |
|---------|-------------|
| `bonito auth` | 🔐 Authentication & account management |
| `bonito providers` | ☁️ Cloud provider management (AWS/Azure/GCP) |
| `bonito models` | 🤖 AI model catalogue — list, search, enable |
| `bonito chat` | 💬 Interactive AI chat with compare mode |
| `bonito gateway` | 🌐 API gateway — keys, logs, config |
| `bonito policies` | 🎯 Routing policies — cost/latency/quality optimization |
| `bonito analytics` | 📊 Usage analytics, costs, trends, digest |
| `bonito deployments` | 🚀 Model deployment management |
| `bonito kb` | 📚 Knowledge base (RAG) — documents, search, sync |
| `bonito agents` | 🤖 Bonobot agents — create, execute, manage sessions |
| `bonito projects` | 📁 Agent projects — organize and manage agents |
| `bonito groups` | 👥 Agent groups — RBAC and permissions |
| `bonito sso` | 🔐 SAML Single Sign-On — configure and manage SSO |

## Bonobot Agents

Create and manage AI agents with persistent conversations and automation:

```bash
# Create a project
bonito projects create --name "Customer Support" --budget 100.00

# Create an agent
bonito agents create --project <project-id> --name "Support Bot" \
  --prompt "You are a helpful customer support agent" \
  --model gpt-4o --max-turns 50

# Execute the agent
bonito agents execute <agent-id> "How do I reset my password?"

# Manage sessions
bonito agents sessions <agent-id>               # List conversations
bonito agents messages <agent-id> <session-id> # View conversation history

# Agent connections and triggers
bonito agents connections <agent-id>            # View agent connections
bonito agents triggers <agent-id>               # View automated triggers
```

## Knowledge Base (RAG)

```bash
bonito kb create --name "Product Docs"         # Create a KB
bonito kb upload <kb-id> report.pdf notes.md   # Upload documents
bonito kb search <kb-id> "How to configure?"   # Semantic search
bonito kb info <kb-id>                         # Stats & details
```

## SAML Single Sign-On

Configure enterprise SSO for your organization:

```bash
bonito sso setup --provider okta               # Interactive SSO setup
bonito sso test                                # Test configuration
bonito sso enable                              # Enable SSO login
bonito sso enforce --breakglass-admin <user>   # Enforce SSO-only (disable passwords)
bonito sso status --email user@company.com     # Check SSO status
```

## JSON Output

All commands support `--json` for scripting and CI/CD:

```bash
bonito models list --json | jq '.[] | .display_name'
bonito analytics overview --json > report.json
```

## Configuration

Config stored in `~/.bonito/`:
- Override with `BONITO_API_KEY` and `BONITO_API_URL` environment variables

## Development

```bash
cd cli/
pip install -e .
bonito --version
```

## License

MIT
