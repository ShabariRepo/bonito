# Bonito AI Platform – Overview

Bonito is a **multi-provider AI infrastructure platform** that unifies access to major AI providers through a single API gateway. Instead of managing separate API keys, SDKs, and billing for each provider, Bonito lets you connect them all and route requests intelligently.

## Supported Providers

| Provider | Models | Key Strengths |
|----------|--------|---------------|
| **OpenAI** | GPT-4o, GPT-4, GPT-3.5 | General purpose, function calling |
| **Anthropic** | Claude Opus, Sonnet, Haiku | Long context, safety, coding |
| **AWS Bedrock** | Claude, Titan, Llama, Mistral | Enterprise, VPC, compliance |
| **Azure OpenAI** | GPT-4, GPT-3.5 (Azure-hosted) | Enterprise SLAs, data residency |
| **GCP Vertex AI** | Gemini, PaLM, Claude | Google Cloud integration |
| **Groq** | Llama, Mixtral (on LPU) | Ultra-low latency inference |

## Core Features

### Unified Gateway
OpenAI-compatible API endpoint (`/v1/chat/completions`). Drop-in replacement — change your base URL, keep your code.

### Intelligent Routing
Route requests based on cost, latency, capability, or availability. Automatic failover if a provider goes down.

### Agent Framework
- **BonBon**: Single-model agents with system prompts and tool use
- **Bonobot**: Multi-model orchestrators that route subtasks to the best model

### Cost Management
Real-time cost tracking across all providers. Set budgets, get alerts, optimize spend.

### Knowledge Bases
Upload documents and connect them to agents for RAG (Retrieval-Augmented Generation).

## Architecture

```
Your App → Bonito Gateway → [Routing Engine] → Provider A / B / C
                                ↑
                          Routing Policy
                       (cost / latency / custom)
```

## API Base URL

All API calls go to: `https://api.getbonito.com`

The gateway endpoint is: `https://api.getbonito.com/v1/chat/completions`

## Authentication

All requests require a Bearer token: `Authorization: Bearer $BONITO_API_KEY`

Generate keys in the Bonito dashboard or via the `create_gateway_key` API.

## Links

- **Dashboard**: https://getbonito.com
- **Docs**: https://getbonito.com/docs
- **GitHub**: https://github.com/ShabariRepo/bonito
