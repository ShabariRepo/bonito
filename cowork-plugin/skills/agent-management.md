# Agent Management

Bonito provides two agent types for building AI-powered applications.

## Agent Types

### BonBon (Single-Model Agent)

A BonBon is a single-model agent with a system prompt. It's the simplest way to deploy an AI assistant.

**Use when:** You need a focused agent on one model — customer support, code review, content generation.

```json
{
  "name": "support-agent",
  "type": "bonbon",
  "model": "gpt-4o",
  "system_prompt": "You are a helpful customer support agent for Acme Corp."
}
```

**BonBon Tiers:**
- **Free Tier**: Uses cost-optimized models (GPT-3.5, Haiku, Llama)
- **Standard Tier**: Uses mid-range models (GPT-4o-mini, Sonnet)
- **Premium Tier**: Uses top-tier models (GPT-4o, Opus, Gemini Ultra)

The tier affects which model is used when you don't specify one explicitly.

### Bonobot (Multi-Model Orchestrator)

A Bonobot can route subtasks to different models based on complexity, cost, or capability.

**Use when:** You need intelligent routing — complex queries go to GPT-4o, simple ones to Haiku.

```json
{
  "name": "smart-router",
  "type": "bonobot",
  "model": "claude-sonnet-4-20250514",
  "system_prompt": "You are an AI orchestrator that routes tasks efficiently."
}
```

**Bonobot capabilities:**
- Analyzes incoming queries for complexity
- Routes to the optimal model per subtask
- Can use multiple models in a single conversation
- Supports tool use and function calling

## Creating Agents

Use the `create_agent` tool:

```
create_agent(
  project_id="proj_abc123",
  name="my-agent",
  model="gpt-4o",
  system_prompt="You are helpful.",
  agent_type="bonbon"
)
```

## Executing Agents

Send messages to an agent:

```
execute_agent(
  agent_id="agent_xyz789",
  message="How do I reset my password?"
)
```

## System Prompts

Best practices for system prompts:
- Be specific about the agent's role and boundaries
- Include examples of expected behavior
- Specify the output format if needed
- Keep prompts under 2000 tokens for best performance

## Knowledge Base Integration

Agents can be connected to knowledge bases for RAG:
1. Create a knowledge base (`create_knowledge_base`)
2. Upload documents to it (via dashboard)
3. Link it to an agent in the agent configuration

This lets agents answer questions grounded in your specific documents.
