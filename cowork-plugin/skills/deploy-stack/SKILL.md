---
name: deploy-stack
description: Deploy AI infrastructure from a bonito.yaml configuration file. Creates providers, agents, knowledge bases, and routing policies in one shot. Trigger with "deploy my AI stack", "set up Bonito", "deploy bonito.yaml", "create my infrastructure", "provision my AI setup", "deploy from config", or "set up my AI infrastructure".
---

# Deploy Stack

Deploy your entire AI infrastructure from a single `bonito.yaml` configuration file. This skill reads your config, validates it, and creates all resources — providers, agents, knowledge bases, and routing policies — in the correct dependency order.

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                       DEPLOY STACK                               │
├─────────────────────────────────────────────────────────────────┤
│  ALWAYS (works standalone with Bonito API)                       │
│  ✓ Parse bonito.yaml: validate schema and dependencies          │
│  ✓ Create providers: connect cloud AI services with credentials │
│  ✓ Create knowledge bases: upload docs, configure RAG           │
│  ✓ Create agents: BonBon agents and Bonobot orchestrators       │
│  ✓ Configure routing: failover, cost-optimized, A/B testing     │
│  ✓ Verify deployment: health check every created resource       │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                      │
│  + GitHub: read bonito.yaml from repos, track deploy commits    │
│  + Slack: send deployment success/failure notifications         │
│  + Monitoring: push deployment events to dashboards             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Getting Started

Tell me to deploy your stack:

- "Deploy my AI infrastructure from bonito.yaml"
- "Set up Bonito with this config"
- "Create my infrastructure — here's my bonito.yaml"
- "Deploy from my config file"
- "Provision everything in bonito.yaml"

You can paste the YAML directly, point me to a file, or if GitHub is connected, I'll pull it from your repo.

---

## Connectors (Optional)

Connect your tools to supercharge this skill:

| Connector | What It Adds |
|-----------|--------------|
| **GitHub** | Read bonito.yaml from repos, track deployment commits, review config changes in PRs |
| **Slack** | Deployment success/failure notifications to your team channel |
| **Monitoring** | Push deployment events to Datadog, Grafana, or other dashboards |

> **No connectors?** No problem. Paste your bonito.yaml or describe what you want and the Bonito API handles everything.

---

## Output Format

```markdown
# Deployment Report

**Config:** bonito.yaml
**Started:** [Timestamp]
**Status:** ✅ Complete | ⚠️ Partial | ❌ Failed

---

## Resources Created

### Providers ([X] created)

| Provider | Type | Region | Status | Models Available |
|----------|------|--------|--------|-----------------|
| [Name] | AWS Bedrock | us-east-1 | ✅ Connected | 12 models |
| [Name] | Azure OpenAI | eastus | ✅ Connected | 8 models |

### Knowledge Bases ([X] created)

| Name | Documents | Chunks | Embedding Model | Status |
|------|-----------|--------|-----------------|--------|
| [Name] | [Count] | [Count] | [Model] | ✅ Indexed |

### Agents ([X] created)

| Agent | Type | Model | Knowledge Base | Endpoint |
|-------|------|-------|---------------|----------|
| [Name] | BonBon | claude-sonnet | [KB name] | /v1/agents/[id] |
| [Name] | Bonobot | gpt-4o | — | /v1/agents/[id] |

### Routing Policies ([X] created)

| Policy | Strategy | Models | Fallback |
|--------|----------|--------|----------|
| [Name] | cost-optimized | [List] | [Model] |
| [Name] | failover | [Primary] → [Secondary] | [Tertiary] |

---

## Verification

| Resource | Health Check | Latency |
|----------|-------------|---------|
| [Name] | ✅ Healthy | 120ms |
| [Name] | ✅ Healthy | 85ms |

---

## Next Steps
- [Suggested follow-up actions]
- [Links to test endpoints]
```

---

## Execution Flow

### Step 1: Parse Configuration

```
Read bonito.yaml and extract:
1. Providers — cloud AI services to connect
2. Knowledge bases — documents and embedding configs
3. Agents — BonBon agents and Bonobot orchestrators
4. Routing — policies, aliases, and fallback chains
5. Settings — organization defaults, region preferences
```

Validate the config:
- Required fields present for each resource type
- Provider types are supported (aws-bedrock, azure-openai, gcp-vertex, openai, anthropic, groq)
- Agent model references resolve to valid providers
- Routing policies reference valid models and providers
- No circular dependencies

### Step 2: Resolve Dependency Order

```
Build deployment graph:
1. Providers first (agents and routing depend on them)
2. Knowledge bases second (agents may reference them)
3. Agents third (may depend on providers + knowledge bases)
4. Routing policies last (reference providers and models)
```

### Step 3: Create Providers

```
For each provider in config:
1. Call ~~bonito to create provider with credentials
2. Verify connection — test API reachability
3. List available models on the provider
4. Record provider ID for downstream resources
```

**If credentials are missing:**
- Prompt user for required credentials
- Never store or log raw API keys
- Validate before proceeding

### Step 4: Create Knowledge Bases

```
For each knowledge base in config:
1. Create knowledge base via ~~bonito
2. Upload referenced documents
3. Wait for indexing to complete
4. Verify document count and chunk count
```

### Step 5: Create Agents

```
For each agent in config:
1. Resolve model → provider mapping
2. Create agent with system prompt, model, and settings
3. Attach knowledge base if specified
4. Configure MCP tools if specified
5. Verify agent responds to test prompt
```

### Step 6: Configure Routing

```
For each routing policy in config:
1. Create routing policy with strategy type
2. Add model targets with weights/priorities
3. Set fallback chain
4. Verify routing resolves correctly
```

### Step 7: Verify Deployment

```
For every created resource:
1. Run health check endpoint
2. Measure response latency
3. Flag any warnings or errors
4. Generate deployment report
```

---

## Config Format Reference

```yaml
# bonito.yaml
organization: my-company

providers:
  - name: aws-primary
    type: aws-bedrock
    region: us-east-1
  - name: openai-fallback
    type: openai

knowledge_bases:
  - name: support-faq
    documents: ./docs/faq/
    embedding_model: text-embedding-3-small

agents:
  - name: support-bot
    type: bonbon
    model: anthropic/claude-sonnet
    provider: aws-primary
    knowledge_base: support-faq
    system_prompt: "You are a helpful customer support agent."

routing:
  - name: production
    strategy: failover
    targets:
      - provider: aws-primary
        model: anthropic/claude-sonnet
        priority: 1
      - provider: openai-fallback
        model: gpt-4o
        priority: 2
```

---

## Tips for Better Deployments

1. **Start with providers** — Make sure credentials are ready before deploying
2. **Use environment variables** — Reference secrets via env vars, not inline
3. **Test incrementally** — Deploy one provider first, verify, then add more
4. **Version your config** — Keep bonito.yaml in git for rollback capability

---

## Related Skills

- **manage-providers** — Deep dive into provider setup and verification
- **create-agent** — Detailed agent configuration beyond what the config covers
- **gateway-routing** — Fine-tune routing policies after deployment
- **debug-issues** — Troubleshoot if any deployment step fails
