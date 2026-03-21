---
name: manage-providers
description: Connect, verify, and manage cloud AI providers through the Bonito gateway. Supports AWS Bedrock, Azure OpenAI, GCP Vertex AI, OpenAI, Anthropic, and Groq. Trigger with "connect AWS Bedrock", "add a provider", "check my providers", "verify credentials", "list my providers", "set up Azure OpenAI", "add Groq", or "manage my AI providers".
---

# Manage Providers

Connect and manage all your cloud AI providers from one place. This skill handles the full lifecycle — adding new providers, verifying credentials, listing available models, checking health, and removing providers you no longer need.

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                     MANAGE PROVIDERS                             │
├─────────────────────────────────────────────────────────────────┤
│  ALWAYS (works standalone with Bonito API)                       │
│  ✓ Add providers: AWS Bedrock, Azure, GCP, OpenAI, Anthropic   │
│  ✓ Verify connections: test API reachability and auth           │
│  ✓ List models: see what's available on each provider           │
│  ✓ Health checks: monitor provider status and latency           │
│  ✓ Update credentials: rotate keys without downtime             │
│  ✓ Remove providers: clean up unused connections                │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                      │
│  + Monitoring: provider health dashboards, latency tracking     │
│  + Slack: alerts when a provider goes unhealthy                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Getting Started

Just tell me what you need:

- "Connect my AWS Bedrock account"
- "Add Azure OpenAI as a provider"
- "List all my providers"
- "Check if my providers are healthy"
- "What models are available on my OpenAI provider?"
- "Remove the Groq provider"
- "Rotate my Anthropic API key"

I'll walk you through the setup, validate credentials, and confirm the connection.

---

## Connectors (Optional)

Connect your tools to supercharge this skill:

| Connector | What It Adds |
|-----------|--------------|
| **Monitoring** | Provider health dashboards, latency tracking over time, uptime reports |
| **Slack** | Real-time alerts when a provider goes unhealthy or latency spikes |

> **No connectors?** No problem. The Bonito API provides built-in health checks and status monitoring.

---

## Output Format

### Adding a Provider

```markdown
# Provider Connected: [Name]

**Type:** [AWS Bedrock | Azure OpenAI | GCP Vertex AI | OpenAI | Anthropic | Groq]
**Region:** [Region if applicable]
**Status:** ✅ Connected and verified

## Connection Details

| Field | Value |
|-------|-------|
| **Provider ID** | [ID] |
| **Type** | [Provider type] |
| **Region** | [Region] |
| **Endpoint** | [API endpoint] |
| **Created** | [Timestamp] |

## Available Models

| Model | Type | Context Window | Input Cost | Output Cost |
|-------|------|---------------|------------|-------------|
| claude-sonnet-4-20250514 | Chat | 200K | $3.00/M | $15.00/M |
| claude-haiku-3-5 | Chat | 200K | $0.80/M | $4.00/M |

**Total:** [X] models available

## Verification

| Check | Result |
|-------|--------|
| Authentication | ✅ Valid |
| API Reachability | ✅ Responding |
| Model Access | ✅ [X] models accessible |
| Latency | [X]ms |
```

### Listing Providers

```markdown
# Provider Overview

| Provider | Type | Region | Status | Models | Latency |
|----------|------|--------|--------|--------|---------|
| [Name] | AWS Bedrock | us-east-1 | ✅ Healthy | 12 | 85ms |
| [Name] | OpenAI | — | ✅ Healthy | 8 | 120ms |
| [Name] | Groq | — | ⚠️ Degraded | 4 | 350ms |

**Total providers:** [X]
**Total models:** [X]
```

---

## Execution Flow

### Step 1: Identify Provider Type

```
Parse the user's request:
- "Connect AWS Bedrock" → type: aws-bedrock
- "Add Azure OpenAI" → type: azure-openai
- "Set up Vertex AI" → type: gcp-vertex
- "Add OpenAI" → type: openai
- "Connect Anthropic" → type: anthropic
- "Add Groq" → type: groq
- "List providers" → action: list
- "Check health" → action: health-check
```

### Step 2: Gather Credentials

```
Based on provider type, collect required credentials:

AWS Bedrock:
  - AWS Access Key ID
  - AWS Secret Access Key
  - Region (default: us-east-1)
  - Optional: IAM Role ARN for cross-account access

Azure OpenAI:
  - Azure API Key
  - Azure Endpoint URL
  - API Version
  - Deployment names

GCP Vertex AI:
  - Project ID
  - Region (default: us-central1)
  - Service account JSON key

OpenAI:
  - API Key
  - Optional: Organization ID

Anthropic:
  - API Key

Groq:
  - API Key
```

**Security rules:**
- Never log or display raw credentials
- Prompt user to provide via environment variables when possible
- Validate format before sending to API

### Step 3: Create Provider

```
1. Call ~~bonito to create provider with type and credentials
2. Set provider name and optional metadata
3. Configure region and endpoint if applicable
4. Record the returned provider ID
```

### Step 4: Verify Connection

```
1. Test API authentication → valid credentials?
2. Test API reachability → can we reach the endpoint?
3. List available models → what models does this provider offer?
4. Run a test inference → does a simple prompt return a response?
5. Measure latency → baseline response time
```

### Step 5: Report Results

```
1. Display provider details and connection status
2. List all available models with pricing
3. Show verification results
4. Suggest next steps (create an agent, set up routing)
```

---

## Provider-Specific Notes

### AWS Bedrock
- Requires IAM permissions for `bedrock:InvokeModel` and `bedrock:ListFoundationModels`
- Some models need explicit access grants in the AWS console
- Cross-region inference available for supported models
- Supports Anthropic Claude, Meta Llama, Amazon Titan, and more

### Azure OpenAI
- Models are deployed as named deployments — you need the deployment name, not just the model name
- Requires an Azure OpenAI resource with deployed models
- Supports GPT-4o, GPT-4, GPT-3.5-Turbo, and embeddings

### GCP Vertex AI
- Requires a GCP project with Vertex AI API enabled
- Service account needs `aiplatform.endpoints.predict` permission
- Supports Gemini, PaLM, and Anthropic Claude (via Model Garden)

### OpenAI
- Direct API access — simplest to set up
- Supports GPT-4o, GPT-4, GPT-3.5-Turbo, o1, o3, embeddings, and more
- Rate limits depend on your API tier

### Anthropic
- Direct API access to Claude models
- Supports Claude Opus, Sonnet, and Haiku
- Useful as a fallback when Bedrock isn't available in a region

### Groq
- Optimized for fast inference with open-source models
- Supports Llama, Mixtral, and Gemma
- Excellent for low-latency use cases

---

## Tips for Better Provider Management

1. **Start with one provider** — Get it working before adding more
2. **Use IAM roles for AWS** — More secure than access keys
3. **Set up a fallback** — Always have a second provider for redundancy
4. **Check model access** — Some Bedrock models need explicit enablement
5. **Monitor latency** — Provider response times vary by region and load

---

## Related Skills

- **deploy-stack** — Deploy providers along with agents and routing from a config
- **gateway-routing** — Set up routing policies across your providers
- **cost-analysis** — Compare pricing across your connected providers
- **debug-issues** — Troubleshoot when a provider connection fails
