# 🐟 Bonito CLI

Unified multi-cloud AI management from your terminal.

Bonito gives enterprise AI teams a single CLI to manage models, costs, and workloads across AWS Bedrock, Azure OpenAI, Google Vertex AI, and more.

## Install

```bash
pip install bonito-cli
```

## Quick Start

```bash
bonito auth login            # Authenticate
bonito models list           # Browse 381+ models across 3 clouds
bonito chat -m gpt-4o        # Start chatting
bonito kb create --name docs # Create a knowledge base
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

## Knowledge Base (RAG)

```bash
bonito kb create --name "Product Docs"         # Create a KB
bonito kb upload <kb-id> report.pdf notes.md   # Upload documents
bonito kb search <kb-id> "How to configure?"   # Semantic search
bonito kb info <kb-id>                         # Stats & details
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
