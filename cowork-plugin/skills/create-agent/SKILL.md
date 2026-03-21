---
name: create-agent
description: Create and configure BonBon agents or Bonobot orchestrators with system prompts, models, MCP tools, and RAG knowledge bases. Trigger with "create an agent", "deploy a chatbot", "set up a support bot", "build an orchestrator", "make a BonBon", "create a Bonobot", "configure an AI agent", or "deploy an agent".
---

# Create Agent

Create AI agents that run on the Bonito gateway. This skill handles both simple BonBon agents (single-model, task-focused) and complex Bonobot orchestrators (multi-agent, tool-using). Configure system prompts, model selection, knowledge bases, and MCP tool integrations.

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                       CREATE AGENT                               │
├─────────────────────────────────────────────────────────────────┤
│  ALWAYS (works standalone with Bonito API)                       │
│  ✓ BonBon agents: single-model agents with system prompts      │
│  ✓ Bonobot orchestrators: multi-agent coordination              │
│  ✓ Model selection: pick from any connected provider            │
│  ✓ Knowledge bases: attach RAG for grounded responses           │
│  ✓ MCP tools: give agents access to external capabilities      │
│  ✓ Testing: verify agent responds correctly before deploying    │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                      │
│  + GitHub: version agent configs, review changes in PRs         │
│  + Slack: notify team when agents are created or updated        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Getting Started

Describe the agent you want:

- "Create a customer support agent using Claude on Bedrock"
- "Build an orchestrator that routes between support and billing agents"
- "Deploy a chatbot with our FAQ knowledge base"
- "Set up a coding assistant with GitHub tools"
- "Make a BonBon agent that handles order lookups"
- "Create a Bonobot that coordinates research and writing"

I'll help you configure the model, system prompt, tools, and knowledge base — then deploy it.

---

## Connectors (Optional)

Connect your tools to supercharge this skill:

| Connector | What It Adds |
|-----------|--------------|
| **GitHub** | Store agent configs in repos, track changes, review in PRs |
| **Slack** | Notify team when agents are created, updated, or go unhealthy |

> **No connectors?** No problem. The Bonito API handles agent creation, deployment, and management directly.

---

## Output Format

```markdown
# Agent Created: [Agent Name]

**Type:** [BonBon | Bonobot]
**Model:** [Model name via Provider]
**Status:** ✅ Deployed and responding

---

## Configuration

| Field | Value |
|-------|-------|
| **Agent ID** | [ID] |
| **Name** | [Name] |
| **Type** | [BonBon / Bonobot] |
| **Model** | [Model] |
| **Provider** | [Provider name] |
| **Endpoint** | /v1/agents/[id]/chat |
| **Created** | [Timestamp] |

## System Prompt

> [The system prompt, truncated if long]

## Knowledge Base [If Attached]

| Field | Value |
|-------|-------|
| **Name** | [KB name] |
| **Documents** | [Count] |
| **Chunks** | [Count] |
| **Retrieval** | Top-[K] chunks per query |

## MCP Tools [If Configured]

| Tool | Description |
|------|-------------|
| [Tool name] | [What it does] |

## Sub-Agents [If Bonobot]

| Agent | Role | Model |
|-------|------|-------|
| [Name] | [Role description] | [Model] |

---

## Test Results

| Test | Input | Response | Status |
|------|-------|----------|--------|
| Basic greeting | "Hello" | [Response preview] | ✅ |
| Domain query | [Test question] | [Response preview] | ✅ |
| Tool use | [Tool trigger] | [Response preview] | ✅ |

---

## Usage

### cURL
​```bash
curl -X POST https://api.getbonito.com/v1/agents/[id]/chat \
  -H "Authorization: Bearer $BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'
​```

### Python
​```python
import bonito
client = bonito.Client()
response = client.agents.chat("[id]", message="Hello!")
​```
```

---

## Execution Flow

### Step 1: Determine Agent Type

```
Parse the user's request:
- Simple task, single model → BonBon agent
- Multi-step, coordination, tool-heavy → Bonobot orchestrator
- "chatbot", "support bot", "assistant" → BonBon
- "orchestrator", "coordinator", "multi-agent" → Bonobot

If unclear, ask:
- "Do you need a single-purpose agent or a multi-agent orchestrator?"
```

### Step 2: Select Model and Provider

```
1. List available providers via ~~bonito
2. List models available across providers
3. Recommend model based on use case:
   - Customer support → Claude Sonnet (good balance)
   - Complex reasoning → Claude Opus or GPT-4o
   - High volume, simple → Claude Haiku or Groq Llama
   - Code generation → Claude Sonnet or GPT-4o
4. Confirm model and provider with user
```

### Step 3: Configure System Prompt

```
If user provides a system prompt → use it directly
If user describes the agent's role:
  1. Generate a system prompt based on description
  2. Include: role definition, tone, boundaries, output format
  3. Present draft to user for approval
  4. Iterate until they're satisfied
```

**System prompt best practices:**
- Start with role and purpose
- Define tone and personality
- Set boundaries (what the agent should NOT do)
- Specify output format preferences
- Include relevant context about the organization

### Step 4: Attach Knowledge Base (Optional)

```
If user wants RAG:
1. Check for existing knowledge bases via ~~bonito
2. If exists → attach by ID
3. If new:
   a. Create knowledge base
   b. Upload documents (files, URLs, or text)
   c. Wait for indexing
   d. Configure retrieval settings (top-K, similarity threshold)
4. Attach knowledge base to agent
```

### Step 5: Configure MCP Tools (Optional)

```
If user wants tool access:
1. List available MCP tool servers
2. Select tools relevant to the agent's purpose
3. Configure tool permissions and parameters
4. Attach tools to agent config
```

### Step 6: Create and Deploy

```
1. Assemble agent configuration
2. Call ~~bonito to create agent
3. Wait for agent to initialize
4. Get agent endpoint URL
5. Record agent ID
```

### Step 7: Test and Verify

```
1. Send a basic greeting → verify response
2. Send a domain-specific query → verify relevance
3. If tools attached → trigger tool use → verify execution
4. If KB attached → ask a KB question → verify retrieval
5. Report test results to user
```

---

## Agent Types

### BonBon Agent
A single-model agent designed for focused tasks. Think of it as a specialized chatbot.

**Best for:**
- Customer support bots
- Internal Q&A assistants
- Code review helpers
- Content generation endpoints
- Data lookup interfaces

**Configuration:**
- One model from one provider
- Optional system prompt
- Optional knowledge base
- Optional MCP tools

### Bonobot Orchestrator
A multi-agent coordinator that delegates tasks to specialized sub-agents. Think of it as a manager that routes work to the right team member.

**Best for:**
- Complex workflows spanning multiple domains
- Agents that need different models for different tasks
- Systems that route between specialized agents
- Workflows requiring sequential or parallel agent calls

**Configuration:**
- Orchestration model (the "manager")
- List of sub-agents with roles
- Routing logic (when to call which agent)
- Shared context and handoff rules

---

## Tips for Better Agents

1. **Start simple** — A BonBon agent with a good system prompt goes far
2. **Be specific in system prompts** — Vague prompts get vague results
3. **Test with real queries** — Use actual user questions, not toy examples
4. **Iterate the prompt** — Expect 2-3 rounds of refinement
5. **Right-size the model** — Don't use Opus for FAQ lookups

---

## Related Skills

- **deploy-stack** — Deploy agents as part of a full infrastructure config
- **manage-providers** — Set up providers before creating agents that use them
- **gateway-routing** — Route traffic across multiple agents
- **debug-issues** — Troubleshoot when an agent isn't responding correctly
