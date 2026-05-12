# Bonito Platform - Complete Setup Walkthrough

> From zero to fully operational: providers, RAG, agents, orchestrator, widget, CLI, code review, and MCP.

**Platform:** [getbonito.com](https://getbonito.com)  
**API Base:** `https://api.getbonito.com`  
**CLI:** `pip install bonito-cli` (v0.4.0)

---

## Table of Contents

1. [Account Setup](#1-account-setup)
2. [Adding Providers](#2-adding-providers)
3. [Knowledge Bases (RAG)](#3-knowledge-bases-rag)
4. [Creating Agents (Bonobot)](#4-creating-agents-bonobot)
5. [Orchestrator Agent](#5-orchestrator-agent)
6. [BonBon Widget](#6-bonbon-widget)
7. [Bonobot API](#7-bonobot-api)
8. [bonito-cli](#8-bonito-cli)
9. [GitHub Code Review](#9-github-code-review)
10. [MCP Integration](#10-mcp-integration)
11. [Gateway API Keys & Routing](#11-gateway-api-keys--routing)

---

## 1. Account Setup

### Sign Up (Web)

1. Go to [getbonito.com](https://getbonito.com)
2. Click **Get Started** or **Sign Up**
3. Enter email + password (or use GitHub/Google OAuth)
4. Verify your email
5. You land on the **Dashboard** with your org auto-created

### Sign Up (CLI)

```bash
pip install bonito-cli
bonito auth login --email you@company.com --password YourPassword
bonito auth whoami   # Verify: shows email, org, role
bonito auth status   # Check API connectivity
```

### Environment Variables (CLI)

```bash
export BONITO_API_KEY="bn-your-api-key-here"
export BONITO_API_URL="https://api.getbonito.com"
```

Config is stored in `~/.bonito/config.json` and `~/.bonito/credentials.json`.

---

## 2. Adding Providers

Navigate to **Dashboard > Providers** on the platform, or use the CLI.

Bonito supports 6 providers. You can add as many as you need -- the platform routes between them automatically.

### AWS Bedrock

**What you need:**
- IAM Access Key ID
- IAM Secret Access Key
- Region (default: `us-east-1`)

**Platform:** Click **Add Provider** > select **AWS Bedrock** > enter credentials.

**CLI:**
```bash
bonito providers add aws \
  --access-key AKIAIOSFODNN7EXAMPLE \
  --secret-key wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY \
  --region us-east-1
```

**API:**
```bash
curl -X POST https://api.getbonito.com/api/providers/connect \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_type": "aws",
    "credentials": {
      "access_key_id": "AKIAIOSFODNN7EXAMPLE",
      "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
      "region": "us-east-1"
    }
  }'
```

**IAM Requirements:** Your IAM user/role needs `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`, and `bedrock:ListFoundationModels` permissions. You may also need to enable model access in the AWS Bedrock console (Marketplace subscriptions for Claude, Llama, etc.).

---

### Azure OpenAI / AI Foundry

Azure has two modes:

#### Mode 1: Azure OpenAI (API Key)

**What you need:**
- API Key (from Azure OpenAI resource)
- Endpoint URL (e.g. `https://your-resource.openai.azure.com`)

**Platform:** Add Provider > **Azure** > Mode: **OpenAI** > enter API key + endpoint.

```bash
curl -X POST https://api.getbonito.com/api/providers/connect \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_type": "azure",
    "credentials": {
      "azure_mode": "openai",
      "api_key": "your-azure-openai-key",
      "endpoint": "https://your-resource.openai.azure.com"
    }
  }'
```

#### Mode 2: Azure AI Foundry (Service Principal)

**What you need:**
- Tenant ID
- Client ID (App Registration)
- Client Secret
- Subscription ID
- Resource Group
- Endpoint (optional -- Bonito can auto-provision)

```bash
curl -X POST https://api.getbonito.com/api/providers/connect \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_type": "azure",
    "credentials": {
      "azure_mode": "foundry",
      "tenant_id": "your-tenant-id",
      "client_id": "your-client-id",
      "client_secret": "your-client-secret",
      "subscription_id": "your-subscription-id",
      "resource_group": "your-resource-group",
      "endpoint": "https://your-foundry-endpoint.azure.com"
    }
  }'
```

---

### GCP Vertex AI

**What you need:**
- GCP Project ID
- Service Account JSON (the full JSON key file content)
- Region (default: `us-central1`)

**Platform:** Add Provider > **GCP** > paste Project ID + service account JSON.

**CLI:**
```bash
bonito providers add gcp \
  --project-id my-gcp-project \
  --service-account-json /path/to/service-account.json \
  --region us-central1
```

**API:**
```bash
curl -X POST https://api.getbonito.com/api/providers/connect \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_type": "gcp",
    "credentials": {
      "project_id": "my-gcp-project",
      "service_account_json": "{\"type\":\"service_account\",\"project_id\":\"...\", ...}",
      "region": "us-central1"
    }
  }'
```

**IAM Requirements:** Service account needs `aiplatform.endpoints.predict` and `aiplatform.models.list` roles (or `Vertex AI User` role).

---

### OpenAI

**What you need:**
- API Key (starts with `sk-`)
- Organization ID (optional)

**Platform:** Add Provider > **OpenAI** > paste API key.

**CLI:**
```bash
bonito providers add openai --api-key sk-your-key-here
```

**API:**
```bash
curl -X POST https://api.getbonito.com/api/providers/connect \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_type": "openai",
    "credentials": {
      "api_key": "sk-your-openai-key",
      "organization_id": "org-optional"
    }
  }'
```

---

### Anthropic

**What you need:**
- API Key (starts with `sk-ant-`)

**Platform:** Add Provider > **Anthropic** > paste API key.

**API:**
```bash
curl -X POST https://api.getbonito.com/api/providers/connect \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_type": "anthropic",
    "credentials": {
      "api_key": "sk-ant-your-anthropic-key"
    }
  }'
```

---

### Groq

**What you need:**
- API Key (from console.groq.com)

**Platform:** Add Provider > **Groq** > paste API key.

**API:**
```bash
curl -X POST https://api.getbonito.com/api/providers/connect \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_type": "groq",
    "credentials": {
      "api_key": "gsk_your-groq-key"
    }
  }'
```

**Available Groq models:** DeepSeek R1 70B, Qwen 2.5 Coder 32B, Mixtral 8x7B, Gemma 2 9B, and more. Groq is the cheapest option for open-source models.

---

### Managed Mode (No Credentials)

For some providers, Bonito offers **managed inference** -- you use Bonito's own credentials and pay via your Bonito billing. No cloud account needed.

```bash
curl -X POST https://api.getbonito.com/api/providers/connect \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_type": "openai",
    "credentials": {
      "managed": true
    }
  }'
```

### Verify Provider Connection

**Platform:** After adding, the provider shows a status indicator (green = active, red = error).

**CLI:**
```bash
bonito providers list           # List all connected providers
bonito providers test <id>      # Test connectivity
```

---

## 3. Knowledge Bases (RAG)

Navigate to **Dashboard > Knowledge Base** on the platform.

Knowledge Bases let you give your agents access to your documents. Bonito handles chunking, embedding, and retrieval. The AI provider never touches your files directly -- Bonito injects relevant context into the prompt at inference time. This means one KB works across all providers.

### Option A: Bonito-Managed Storage (Upload)

For files you upload directly to Bonito.

**Platform:**
1. Go to **Knowledge Base** page
2. Click **Create Knowledge Base**
3. Name: e.g. `product-docs`
4. Source Type: **Bonito Managed**
5. (Optional) Adjust chunking: chunk size (default 512), overlap (default 50)
6. Click **Create**
7. Click into the KB, then **Upload Files** -- drag and drop PDFs, TXT, MD, DOCX, CSV, JSON, HTML

**CLI:**
```bash
bonito kb create --name "product-docs"
bonito kb upload <kb-id> report.pdf notes.md handbook.docx
bonito kb info <kb-id>    # Check document count, status
```

**API:**
```bash
# Create KB
curl -X POST https://api.getbonito.com/api/knowledge-bases \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "product-docs",
    "description": "Product documentation and FAQs",
    "source_type": "upload",
    "chunk_size": 512,
    "chunk_overlap": 50
  }'

# Upload a file
curl -X POST https://api.getbonito.com/api/knowledge-bases/<kb-id>/upload \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -F "file=@report.pdf"
```

---

### Option B: AWS S3 Bucket

Connect your own S3 bucket. Bonito syncs files from it.

**What you need:**
- Bucket name
- AWS region
- Access Key ID + Secret (with `s3:GetObject`, `s3:ListBucket` permissions)
- (Optional) Path prefix to limit which folder Bonito reads

**Platform:**
1. Create Knowledge Base > Source Type: **AWS S3**
2. Fill in bucket name, region, credentials
3. Click **Create**
4. Click **Sync** to pull files from the bucket

**API:**
```bash
curl -X POST https://api.getbonito.com/api/knowledge-bases \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "s3-docs",
    "source_type": "s3",
    "source_config": {
      "bucket": "my-company-docs",
      "region": "us-east-1",
      "access_key_id": "AKIA...",
      "secret_access_key": "...",
      "prefix": "knowledge-base/"
    },
    "sync_schedule": "0 */6 * * *"
  }'
```

The `sync_schedule` is a cron expression -- `0 */6 * * *` means sync every 6 hours.

---

### Option C: GCP Cloud Storage

**What you need:**
- Bucket name
- GCP Project ID
- Service Account JSON (with `storage.objects.list` and `storage.objects.get`)
- (Optional) Path prefix

**Platform:**
1. Create Knowledge Base > Source Type: **GCP Storage**
2. Enter bucket name, project ID, service account JSON
3. Click **Create** then **Sync**

**API:**
```bash
curl -X POST https://api.getbonito.com/api/knowledge-bases \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "gcs-docs",
    "source_type": "gcs",
    "source_config": {
      "bucket": "my-company-docs",
      "project_id": "my-gcp-project",
      "service_account_json": "{...}",
      "prefix": "docs/"
    }
  }'
```

---

### Option D: Azure Blob Storage

**What you need:**
- Storage account name
- Container name
- Connection string or SAS token
- (Optional) Path prefix

**Platform:**
1. Create Knowledge Base > Source Type: **Azure Blob**
2. Enter storage account, container, connection string
3. Click **Create** then **Sync**

**API:**
```bash
curl -X POST https://api.getbonito.com/api/knowledge-bases \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "azure-docs",
    "source_type": "azure_blob",
    "source_config": {
      "storage_account": "mystorageaccount",
      "container": "documents",
      "connection_string": "DefaultEndpointsProtocol=https;AccountName=...",
      "prefix": "kb/"
    }
  }'
```

---

### Search a Knowledge Base

```bash
# CLI
bonito kb search <kb-id> "How do I configure SSO?"

# API
curl -X POST https://api.getbonito.com/api/knowledge-bases/<kb-id>/search \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I configure SSO?", "top_k": 5}'
```

### Embedding Configuration

| Field | Default | Description |
|-------|---------|-------------|
| `embedding_model` | `auto` | Bonito picks the best available model from your providers |
| `embedding_dimensions` | `768` | Vector dimensions (768-4096) |
| `chunk_size` | `512` | Tokens per chunk (100-2048) |
| `chunk_overlap` | `50` | Overlap between chunks (0-200) |

---

## 4. Creating Agents (Bonobot)

Navigate to **Dashboard > Agents** on the platform.

Bonobot agents are AI agents that can use your providers, access your knowledge bases, and maintain conversation sessions.

### Step 1: Create a Project

Projects organize your agents.

**Platform:** Go to **Agents** page > **Create Project** > enter name + optional budget.

**CLI:**
```bash
bonito projects create --name "Customer Support" --budget 100.00
```

**API:**
```bash
curl -X POST https://api.getbonito.com/api/bonobot/projects \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer Support",
    "description": "Support agents for our customers",
    "monthly_budget": 100.00
  }'
```

### Step 2: Create an Agent

**Platform:**
1. Click into your project
2. Click **Create Agent**
3. Fill in:
   - **Name:** e.g. `support-bot`
   - **System Prompt:** The agent's personality and instructions
   - **Model:** Pick from your connected providers (e.g. `gpt-4o`, `claude-3-5-sonnet`, `deepseek-r1-distill-llama-70b`)
   - **Max Turns:** Conversation length limit (default 50)
   - **Temperature:** 0.0-2.0 (default 0.7)
4. Click **Create**

**CLI:**
```bash
bonito agents create \
  --project <project-id> \
  --name "Support Bot" \
  --prompt "You are a helpful customer support agent for Acme Corp. Be concise and friendly." \
  --model gpt-4o \
  --max-turns 50
```

**API:**
```bash
curl -X POST https://api.getbonito.com/api/bonobot/agents \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "<project-id>",
    "name": "Support Bot",
    "system_prompt": "You are a helpful customer support agent for Acme Corp.",
    "model_id": "gpt-4o",
    "model_config": {"temperature": 0.7},
    "max_turns": 50
  }'
```

> **Note:** The agent API uses strict input validation (`extra=forbid`). Sending unrecognized fields will return a `422 Unprocessable Entity` error. Use `model_id` (not `model`) and put tuning parameters like `temperature` inside `model_config`.

### Step 3: Link Knowledge Bases to Agent

This gives the agent access to specific documents for RAG.

**Platform:**
1. Go to **Knowledge Base** page
2. Click on a KB
3. In the **Agent Access** section, toggle which agents can use this KB

**API:**
```bash
curl -X POST https://api.getbonito.com/api/knowledge-bases/<kb-id>/agents \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "<agent-id>"
  }'
```

Now when the agent receives a message, Bonito automatically:
1. Searches the linked KBs for relevant chunks
2. Injects those chunks into the prompt context
3. Sends to whichever AI provider the agent is configured to use

### Step 4: Test Your Agent

**CLI:**
```bash
bonito agents execute <agent-id> "How do I reset my password?"
```

**API:**
```bash
curl -X POST https://api.getbonito.com/api/bonobot/chat \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "<agent-id>",
    "message": "How do I reset my password?"
  }'
```

---

## 5. Orchestrator Agent

An orchestrator is a special agent that routes user conversations to specialized sub-agents. Think of it as a receptionist that directs you to the right department.

### How It Works

1. User talks to the **Orchestrator**
2. Orchestrator analyzes the request
3. Routes to the appropriate sub-agent (support, billing, technical, etc.)
4. Sub-agent handles the conversation
5. Results flow back through the orchestrator

### Setting Up an Orchestrator

**Step 1:** Create your specialized agents first (see Section 4):
- `support-bot` (handles customer questions)
- `billing-bot` (handles payment/invoice questions)
- `technical-bot` (handles API/integration questions)

**Step 2:** Create the orchestrator agent with a routing prompt:

```bash
curl -X POST https://api.getbonito.com/api/bonobot/agents \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "<project-id>",
    "name": "Orchestrator",
    "system_prompt": "You are a routing agent for Acme Corp. Analyze each user message and route to the appropriate department:\n\n- For general questions, product info, or how-to: route to support-bot\n- For billing, payments, invoices, or subscription issues: route to billing-bot\n- For API integration, technical errors, or developer questions: route to technical-bot\n\nAlways greet the user warmly and let them know you are connecting them to the right specialist.",
    "model_id": "gpt-4o",
    "max_turns": 100
  }'
```

**Step 3:** Set up agent connections (link sub-agents to the orchestrator):

**Platform:**
1. Go to the orchestrator agent's settings
2. Under **Connections**, add each sub-agent
3. Define routing rules or let the orchestrator's prompt handle it

**CLI:**
```bash
bonito agents connections <orchestrator-id>  # View connections
```

**API:**
```bash
curl -X POST https://api.getbonito.com/api/agents/<orchestrator-id>/connections \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "target_agent_id": "<sub-agent-id>",
    "connection_type": "handoff",
    "label": "Route to support"
  }'
```

Valid `connection_type` values: `handoff`, `escalation`, `data_feed`, `trigger`.

> **Note:** The connection API uses strict validation (`extra=forbid`). Unknown fields return `422`. The `target_agent_id` and `connection_type` are top-level fields (not nested inside a `config` object).

**Step 4:** The orchestrator is now the single entry point. Users talk to it, and it delegates.

### Orchestrator as BonBon Widget

The orchestrator is ideal as your website's chat widget (see Section 6). Visitors get one entry point that intelligently routes to specialized agents behind the scenes.

---

## 6. BonBon Widget

BonBon is Bonito's embeddable chat widget. Drop it on any website to let visitors talk to your Bonobot agents.

### Deploy on Your Website

**Step 1:** Get your agent ID from the platform (Dashboard > Agents > click agent > copy ID)

**Step 2:** Add this script to your website's HTML (before `</body>`):

```html
<script>
  window.bonbonConfig = {
    agentId: "YOUR-AGENT-ID",
    apiKey: "bn-your-api-key",
    theme: "dark",           // "dark" or "light"
    position: "bottom-right", // "bottom-right" or "bottom-left"
    title: "Chat with us",
    subtitle: "AI-powered support",
    primaryColor: "#6366f1"
  };
</script>
<script src="https://getbonito.com/bonbon.js" async></script>
```

**Step 3:** The widget appears as a floating chat bubble. Visitors click to open and start chatting.

### BonBon Templates

Bonito provides pre-built agent templates for common use cases:

**Platform:** Dashboard > Agents > **BonBon Templates** tab > pick a template > customize > deploy.

Available templates include customer support, FAQ bot, onboarding assistant, and more.

### Customization Options

| Option | Type | Description |
|--------|------|-------------|
| `agentId` | string | Required. Your Bonobot agent ID |
| `apiKey` | string | Required. Your Bonito API key |
| `theme` | string | `"dark"` or `"light"` |
| `position` | string | `"bottom-right"` or `"bottom-left"` |
| `title` | string | Widget header title |
| `subtitle` | string | Widget header subtitle |
| `primaryColor` | string | Hex color for accent |
| `greeting` | string | First message shown to visitors |
| `placeholder` | string | Input placeholder text |

---

## 7. Bonobot API

Use the Bonobot API to integrate agents into your own applications.

### Chat (Single Message)

```bash
curl -X POST https://api.getbonito.com/api/bonobot/chat \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "<agent-id>",
    "message": "What are your business hours?",
    "session_id": "optional-session-id-for-continuity"
  }'
```

Response:
```json
{
  "response": "Our business hours are Monday-Friday, 9 AM to 5 PM EST.",
  "session_id": "sess_abc123",
  "model_used": "gpt-4o",
  "provider": "openai",
  "tokens": { "input": 245, "output": 32 },
  "cost": 0.0031
}
```

### Streaming Chat

```bash
curl -X POST https://api.getbonito.com/api/bonobot/chat \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "<agent-id>",
    "message": "Explain quantum computing",
    "stream": true
  }'
```

### Session Management

```bash
# List sessions for an agent
curl https://api.getbonito.com/api/bonobot/agents/<agent-id>/sessions \
  -H "Authorization: Bearer $BONITO_API_KEY"

# Get messages in a session
curl https://api.getbonito.com/api/bonobot/agents/<agent-id>/sessions/<session-id>/messages \
  -H "Authorization: Bearer $BONITO_API_KEY"
```

### OpenAI-Compatible Gateway

Bonito exposes an OpenAI-compatible `/v1/chat/completions` endpoint. Drop in as a replacement for any OpenAI SDK:

```bash
curl -X POST https://api.getbonito.com/v1/chat/completions \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [
      {"role": "system", "content": "You are helpful."},
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

This works with any model from any connected provider. Bonito routes to the right provider automatically.

**Python (OpenAI SDK):**
```python
from openai import OpenAI

client = OpenAI(
    api_key="bn-your-bonito-key",
    base_url="https://api.getbonito.com/v1"
)

response = client.chat.completions.create(
    model="gpt-4o",  # or claude-3-5-sonnet, deepseek-r1, etc.
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

---

## 8. bonito-cli

### Install

```bash
pip install bonito-cli
```

### Authentication

```bash
bonito auth login                    # Interactive login
bonito auth login --email you@co     # Email-based
bonito auth whoami                   # Check current user
bonito auth status                   # API connectivity check
bonito auth logout                   # Sign out
```

### Key Commands

```bash
# Providers
bonito providers list                # See connected providers
bonito providers add aws ...         # Add a provider
bonito providers test <id>           # Test connectivity

# Models
bonito models list                   # Browse all available models
bonito models list --provider aws    # Filter by provider
bonito models search "claude"        # Search models
bonito models enable <model-id>      # Activate a model

# Interactive Chat
bonito chat -m gpt-4o               # Chat with a model
bonito chat --compare gpt-4o --compare claude-3-5-sonnet  # Compare side-by-side

# Knowledge Bases
bonito kb create --name "docs"       # Create KB
bonito kb upload <id> file1.pdf      # Upload files
bonito kb search <id> "query"        # Semantic search
bonito kb info <id>                  # Stats and status

# Agents
bonito projects list                 # List projects
bonito projects create --name "X"    # Create project
bonito agents create --project <id> --name "Bot" --prompt "..." --model gpt-4o
bonito agents execute <id> "Hello!"  # Chat with agent
bonito agents sessions <id>          # List conversations
bonito agents messages <id> <sess>   # View chat history

# Gateway
bonito gateway status                # Gateway health
bonito gateway usage --days 7        # Usage last 7 days
bonito gateway logs --limit 20       # Recent API logs
bonito gateway keys list             # API keys
bonito gateway keys create --name "Production"

# Analytics
bonito analytics overview            # Cost and usage summary
bonito analytics costs --days 30     # Cost breakdown

# Routing Policies
bonito policies list                 # Active policies
bonito policies create --name "Cost Saver" --strategy cost_optimized
```

### JSON Output

All commands support `--json` for scripting:

```bash
bonito models list --json | jq '.[].display_name'
bonito analytics overview --json > report.json
```

---

## 9. GitHub Code Review

Bonito's GitHub App provides AI-powered code reviews on pull requests with Silicon Valley character personas (Gilfoyle, Dinesh, Erlich, Jian-Yang, etc.).

### Setup

**Step 1:** Go to **Dashboard > Code Review** on the platform.

**Step 2:** Click **Install GitHub App** -- this redirects to GitHub to install the Bonito Code Review app on your repositories.

**Step 3:** Select which repos to enable (or all repos).

**Step 4:** Back on the Bonito dashboard, configure:
- **Persona:** Choose your reviewer personality (default, gilfoyle, dinesh, etc.)
- **Tier:** Free (5 reviews/month) or Pro (unlimited)

**Step 5:** Open a PR! Bonito automatically reviews it and posts comments.

### What You Get

- **PR Comments:** Detailed code review with severity markers (critical, warning, suggestion, info)
- **Snapshot Link:** Key code blocks are extracted and viewable on the Bonito platform at `/snapshots/<review-id>`
- **Persona Flavor:** Gilfoyle will insult your code. Dinesh will be passive-aggressive. Default is professional.

### View Reviews on Platform

**Dashboard > Code Review** shows:
- All reviewed PRs
- Review status and snapshot counts
- Click any review to see the full analysis + key code snapshots

---

## 10. MCP Integration

Bonito exposes an MCP (Model Context Protocol) server, allowing MCP-compatible clients (Claude Desktop, Cursor, etc.) to use Bonito as a tool provider.

### Setup with Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "bonito": {
      "command": "npx",
      "args": ["-y", "bonito-mcp"],
      "env": {
        "BONITO_API_KEY": "bn-your-api-key",
        "BONITO_API_URL": "https://api.getbonito.com"
      }
    }
  }
}
```

### Available MCP Tools

Once connected, MCP clients can:
- **List models** across all your providers
- **Chat** with any model through Bonito's routing
- **Search knowledge bases** for relevant documents
- **Execute agents** (Bonobot)
- **Check usage** and costs

### Setup with Cursor

Add to Cursor's MCP settings:

```json
{
  "bonito": {
    "command": "npx",
    "args": ["-y", "bonito-mcp"],
    "env": {
      "BONITO_API_KEY": "bn-your-api-key"
    }
  }
}
```

---

## 11. Gateway API Keys & Routing

### Create API Keys

**Platform:** Dashboard > Gateway > **API Keys** > Create Key

**CLI:**
```bash
bonito gateway keys create --name "Production App"
bonito gateway keys list
```

**API:**
```bash
curl -X POST https://api.getbonito.com/api/gateway/keys \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production App",
    "rate_limit": 120,
    "allowed_models": {
      "models": ["gpt-4o", "claude-3-5-sonnet"],
      "providers": ["openai", "anthropic"]
    }
  }'
```

Each key can have:
- **Rate limit** (requests/minute, 1-10000)
- **Model allowlist** (restrict which models this key can access)
- **Team ID** (for per-team tracking)

### Routing Strategies

Configure how Bonito routes requests across providers:

| Strategy | Description |
|----------|-------------|
| `cost-optimized` | Route to the cheapest provider that has the requested model |
| `latency-optimized` | Route to the fastest provider based on recent latency data |
| `balanced` | Balance between cost and latency |
| `failover` | Try primary provider, fall back to others on failure |

**Set strategy:**
```bash
bonito gateway config set routing_strategy cost-optimized
```

### Fallback Models

Configure automatic fallback when a model is unavailable:

```bash
curl -X PATCH https://api.getbonito.com/api/gateway/config \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "fallback_models": {
      "gpt-4o": ["claude-3-5-sonnet", "gemini-1.5-pro"],
      "claude-3-5-sonnet": ["gpt-4o", "deepseek-r1"]
    }
  }'
```

If `gpt-4o` fails, Bonito automatically tries `claude-3-5-sonnet`, then `gemini-1.5-pro`.

---

## Quick Reference: Full Setup Checklist

- [ ] **Sign up** at getbonito.com
- [ ] **Add at least 1 provider** (Groq is free and fast for testing)
- [ ] **Create a Knowledge Base** and upload documents
- [ ] **Create a Project** to organize your agents
- [ ] **Create an Agent** with system prompt + model + linked KBs
- [ ] **Test the agent** via CLI or API
- [ ] **Deploy BonBon widget** on your website (optional)
- [ ] **Create API keys** for your applications
- [ ] **Install GitHub App** for code reviews (optional)
- [ ] **Set up MCP** for Claude Desktop/Cursor (optional)
- [ ] **Configure routing** and fallback strategies

---

*Last updated: 2026-03-25*
