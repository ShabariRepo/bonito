---
name: gateway-routing
description: Configure routing policies for the Bonito AI gateway — cost-optimized routing, failover chains, A/B testing, model aliases, and cross-region inference. Trigger with "set up failover", "route requests", "configure routing", "add a fallback model", "cross-region inference", "create a model alias", "A/B test models", "set up load balancing", or "configure gateway routing".
---

# Gateway Routing

Configure intelligent request routing across your AI providers. This skill handles failover chains, cost-optimized routing, A/B testing, model aliases, and cross-region inference — so your AI infrastructure is resilient, cost-effective, and performant.

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                     GATEWAY ROUTING                              │
├─────────────────────────────────────────────────────────────────┤
│  ALWAYS (works standalone with Bonito API)                       │
│  ✓ Failover chains: auto-switch when a provider goes down       │
│  ✓ Cost-optimized: route to cheapest model that meets quality   │
│  ✓ A/B testing: split traffic between models for comparison     │
│  ✓ Model aliases: map friendly names to specific deployments    │
│  ✓ Cross-region: route to nearest or fastest region             │
│  ✓ Load balancing: distribute traffic across providers          │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                      │
│  + Monitoring: traffic dashboards, latency graphs, error rates  │
│  + Slack: alerts on failover events, routing changes            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Getting Started

Describe the routing you need:

- "Set up failover from Bedrock to OpenAI"
- "Route to the cheapest model for each request"
- "A/B test Claude Sonnet vs GPT-4o with 50/50 split"
- "Create a model alias 'fast' that maps to Groq Llama"
- "Set up cross-region inference for low latency"
- "Load balance across my three providers"
- "Add a fallback for when OpenAI is down"

I'll configure the routing policy, verify it works, and show you how traffic will flow.

---

## Connectors (Optional)

Connect your tools to supercharge this skill:

| Connector | What It Adds |
|-----------|--------------|
| **Monitoring** | Real-time traffic dashboards, latency percentiles, error rate tracking |
| **Slack** | Alerts on failover events, routing policy changes, traffic anomalies |

> **No connectors?** No problem. The Bonito API provides built-in routing status and basic traffic metrics.

---

## Output Format

```markdown
# Routing Policy: [Policy Name]

**Strategy:** [Failover | Cost-Optimized | A/B Test | Round-Robin | Weighted]
**Status:** ✅ Active

---

## Routing Table

### Failover Chain
| Priority | Provider | Model | Region | Status |
|----------|----------|-------|--------|--------|
| 1 (Primary) | AWS Bedrock | claude-sonnet | us-east-1 | ✅ Healthy |
| 2 (Fallback) | OpenAI | gpt-4o | — | ✅ Healthy |
| 3 (Last resort) | Groq | llama-3-70b | — | ✅ Healthy |

### OR: A/B Test Split
| Variant | Provider | Model | Traffic | Requests | Avg Latency |
|---------|----------|-------|---------|----------|-------------|
| A | Bedrock | claude-sonnet | 50% | [Count] | [X]ms |
| B | OpenAI | gpt-4o | 50% | [Count] | [X]ms |

### OR: Cost-Optimized
| Tier | Max Cost | Model | Provider |
|------|----------|-------|----------|
| Budget | $0.50/M | llama-3-8b | Groq |
| Standard | $3.00/M | claude-sonnet | Bedrock |
| Premium | $15.00/M | claude-opus | Bedrock |

---

## Model Aliases

| Alias | Resolves To | Provider |
|-------|-------------|----------|
| `fast` | llama-3-70b | Groq |
| `smart` | claude-sonnet | Bedrock |
| `best` | claude-opus | Bedrock |

---

## Traffic Flow

​```
Request → Gateway → [Strategy Logic] → Provider
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
          Primary    Fallback   Last Resort
          (Bedrock)  (OpenAI)    (Groq)
​```

---

## Verification

| Test | Result |
|------|--------|
| Primary route | ✅ Responding (85ms) |
| Failover trigger | ✅ Switches in <500ms |
| Fallback route | ✅ Responding (120ms) |
```

---

## Execution Flow

### Step 1: Determine Routing Strategy

```
Parse the user's request:
- "Set up failover" → strategy: failover
- "Route to cheapest" → strategy: cost-optimized
- "A/B test" → strategy: ab-test
- "Load balance" → strategy: round-robin / weighted
- "Model alias" → action: create-alias
- "Cross-region" → strategy: geo-routing
```

### Step 2: Gather Requirements

```
For failover:
  - Primary provider and model
  - Fallback provider(s) and model(s)
  - Failure detection criteria (timeout, error codes)
  - Maximum failover latency

For cost-optimized:
  - Quality threshold (minimum acceptable model tier)
  - Budget constraints
  - Which models are acceptable substitutes

For A/B testing:
  - Model A and Model B (and their providers)
  - Traffic split percentage
  - Duration of the test
  - Success metrics (latency, quality, cost)

For model aliases:
  - Alias name
  - Target model and provider
  - Optional: version pinning
```

### Step 3: Validate Providers

```
1. List connected providers via ~~bonito
2. Verify requested models are available on those providers
3. Check provider health — don't route to unhealthy providers
4. Confirm pricing for cost-optimized routing
```

### Step 4: Create Routing Policy

```
1. Call ~~bonito to create routing policy
2. Set strategy type and parameters
3. Add model targets with priorities/weights
4. Configure failover thresholds
5. Set health check intervals
6. Record policy ID
```

### Step 5: Create Model Aliases (If Requested)

```
1. Define alias name → target model mapping
2. Register alias via ~~bonito
3. Verify alias resolves correctly
4. Test request through alias
```

### Step 6: Verify Routing

```
1. Send test request → verify it routes to primary
2. Simulate primary failure → verify failover triggers
3. For A/B → send multiple requests → verify split ratio
4. For cost-optimized → send varied requests → verify tier selection
5. Measure failover latency
6. Report routing verification results
```

---

## Routing Strategies

### Failover
Route to primary. If it fails, try the next in the chain.

**Use when:** You need high availability and can't tolerate downtime.

**Configuration:**
- Ordered list of providers/models by priority
- Failure detection: timeout (ms), error codes, consecutive failures
- Recovery: how long before retrying the primary

### Cost-Optimized
Route each request to the cheapest model that meets quality requirements.

**Use when:** You want to minimize costs while maintaining a quality floor.

**Configuration:**
- Model tiers ordered by cost
- Quality threshold for each tier
- Request classification rules (simple → cheap, complex → premium)

### A/B Testing
Split traffic between two (or more) model configurations.

**Use when:** Evaluating a new model, comparing providers, or testing prompt changes.

**Configuration:**
- Variants with traffic percentages
- Test duration
- Metrics to compare (latency, token usage, user satisfaction)

### Round-Robin / Weighted
Distribute traffic evenly or by weight across providers.

**Use when:** Load balancing across providers with similar capabilities.

**Configuration:**
- Provider list with optional weights
- Session affinity (sticky routing per user, or not)

### Geo-Routing
Route to the nearest or lowest-latency region.

**Use when:** Serving global users and minimizing latency.

**Configuration:**
- Region-provider mapping
- Latency thresholds
- Fallback for regions without a local provider

---

## Tips for Better Routing

1. **Always have a fallback** — No provider has 100% uptime
2. **Test failover regularly** — Don't wait for a real outage to discover it doesn't work
3. **Start simple** — Failover with 2 providers covers most needs
4. **Monitor after deploying** — Routing changes can shift costs and latency
5. **Pin model versions** — Avoid surprises when providers update models

---

## Related Skills

- **manage-providers** — Set up providers before configuring routing across them
- **cost-analysis** — Analyze costs to inform cost-optimized routing decisions
- **deploy-stack** — Deploy routing policies as part of a full infrastructure config
- **debug-issues** — Troubleshoot when routing isn't behaving as expected
