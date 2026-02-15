# 🐟 Bonito CLI

**Unified multi-cloud AI management from your terminal.**

Bonito gives enterprise AI teams a single CLI to manage models, costs, and workloads across AWS Bedrock, Azure OpenAI, and Google Vertex AI — instead of juggling `aws bedrock`, `az cognitiveservices`, and `gcloud ai`.

## Install

```bash
pip install bonito-cli
```

## Quick Start

```bash
# Authenticate
bonito auth login

# List connected cloud providers
bonito providers list

# Browse 300+ models across all providers
bonito models list
bonito models list --search "claude"

# Chat with any model
bonito chat -m <model-id> "What is quantum computing?"

# Interactive chat
bonito chat

# View deployments
bonito deployments list

# Check gateway logs
bonito gateway logs
```

## Commands

| Command | Description |
|---------|------------|
| `bonito auth` | 🔐 Authentication & API keys |
| `bonito providers` | ☁️ Cloud provider management |
| `bonito models` | 🤖 AI model catalogue |
| `bonito deployments` | 🚀 Deployment management |
| `bonito chat` | 💬 Interactive AI chat |
| `bonito gateway` | 🌐 API gateway management |
| `bonito policies` | 🎯 Routing policies |
| `bonito analytics` | 📊 Usage analytics & costs |

## Features

- **Multi-cloud** — AWS Bedrock, Azure OpenAI, Google Vertex AI in one tool
- **Interactive chat** — Talk to any model with `/model`, `/temp`, `/export` commands
- **Compare models** — `bonito chat --compare model1 --compare model2 "prompt"`
- **Routing policies** — Cost-optimized, failover, A/B testing
- **JSON output** — `--json` flag on every command for CI/CD automation
- **Rich terminal UI** — Beautiful tables, progress bars, and formatted output

## Configuration

```bash
# Environment variables (override config file)
export BONITO_API_KEY=your-api-key
export BONITO_API_URL=https://your-instance.example.com

# Or use config file (~/.bonito/config.json)
bonito auth login --email you@company.com
```

## Requirements

- Python 3.10+
- A [Bonito](https://getbonito.com) account

## License

MIT
