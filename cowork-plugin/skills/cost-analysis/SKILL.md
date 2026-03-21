---
name: cost-analysis
description: Analyze AI spending across providers, identify expensive models, recommend cheaper alternatives, and optimize routing for cost savings. Trigger with "what am I spending", "cost breakdown", "optimize my AI costs", "which models cost the most", "AI spending report", "reduce my AI costs", "cost analysis", or "show me my usage".
---

# Cost Analysis

Understand and optimize your AI spending across all connected providers. This skill pulls usage data, breaks down costs by model, agent, and provider, identifies expensive patterns, and recommends concrete actions to reduce costs without sacrificing quality.

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                      COST ANALYSIS                               │
├─────────────────────────────────────────────────────────────────┤
│  ALWAYS (works standalone with Bonito API)                       │
│  ✓ Usage data: requests, tokens, and costs by model             │
│  ✓ Provider breakdown: spending per cloud provider              │
│  ✓ Agent breakdown: which agents cost the most                  │
│  ✓ Model comparison: cost per token across providers            │
│  ✓ Trend analysis: daily/weekly/monthly spend over time         │
│  ✓ Recommendations: cheaper models, routing optimizations       │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                      │
│  + Slack: cost threshold alerts to your team channel            │
│  + Monitoring: spending dashboards in Datadog or Grafana        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Getting Started

Ask about your costs naturally:

- "What am I spending on AI?"
- "Break down my costs by provider"
- "Which models cost the most?"
- "How can I reduce my AI spending?"
- "Show me usage for the last 30 days"
- "Compare my spending this month vs last month"
- "Which agent is the most expensive?"

I'll pull your usage data and give you a clear picture with actionable recommendations.

---

## Connectors (Optional)

Connect your tools to supercharge this skill:

| Connector | What It Adds |
|-----------|--------------|
| **Slack** | Automated alerts when spending exceeds thresholds |
| **Monitoring** | Persistent cost dashboards, budget tracking, anomaly detection |

> **No connectors?** No problem. The Bonito API tracks all usage and costs through the gateway.

---

## Output Format

```markdown
# AI Cost Analysis

**Period:** [Start date] — [End date]
**Total Spend:** $[Amount]
**Total Requests:** [Count]
**Total Tokens:** [Count] ([Input]M input / [Output]M output)

---

## Spending by Provider

| Provider | Requests | Tokens | Cost | % of Total |
|----------|----------|--------|------|------------|
| AWS Bedrock | [Count] | [Count] | $[Amount] | [X]% |
| OpenAI | [Count] | [Count] | $[Amount] | [X]% |
| Groq | [Count] | [Count] | $[Amount] | [X]% |
| **Total** | **[Count]** | **[Count]** | **$[Amount]** | **100%** |

## Spending by Model

| Model | Provider | Requests | Avg Tokens | Cost | $/1K Requests |
|-------|----------|----------|------------|------|--------------|
| claude-sonnet | Bedrock | [Count] | [Count] | $[Amount] | $[Amount] |
| gpt-4o | OpenAI | [Count] | [Count] | $[Amount] | $[Amount] |
| llama-3-70b | Groq | [Count] | [Count] | $[Amount] | $[Amount] |

## Spending by Agent

| Agent | Model | Requests | Cost | % of Total |
|-------|-------|----------|------|------------|
| support-bot | claude-sonnet | [Count] | $[Amount] | [X]% |
| code-reviewer | gpt-4o | [Count] | $[Amount] | [X]% |

## Cost Trend

| Period | Requests | Cost | Change |
|--------|----------|------|--------|
| This week | [Count] | $[Amount] | [+/-X]% |
| Last week | [Count] | $[Amount] | — |
| This month | [Count] | $[Amount] | [+/-X]% |
| Last month | [Count] | $[Amount] | — |

---

## Optimization Recommendations

### 🟢 Quick Wins (Immediate savings)

1. **[Recommendation]**
   - Current: [What's happening now]
   - Suggested: [What to change]
   - Estimated savings: $[Amount]/month ([X]%)

2. **[Recommendation]**
   - Current: [What's happening now]
   - Suggested: [What to change]
   - Estimated savings: $[Amount]/month ([X]%)

### 🟡 Medium-Term (Requires testing)

1. **[Recommendation]**
   - Impact: [Description]
   - Effort: [Low/Medium/High]

### 🔴 Strategic (Requires architecture changes)

1. **[Recommendation]**
   - Impact: [Description]
   - Effort: [Low/Medium/High]

---

## Potential Monthly Savings: $[Amount] ([X]% reduction)
```

---

## Execution Flow

### Step 1: Determine Analysis Scope

```
Parse the user's request:
- "What am I spending?" → Full overview, current month
- "Costs by provider" → Provider breakdown
- "Most expensive models" → Model ranking
- "Compare months" → Trend analysis
- "Optimize costs" → Recommendations focus
- "Last 7 days" → Custom date range
```

### Step 2: Pull Usage Data

```
Query ~~bonito for usage analytics:
1. Get total requests, tokens, and costs for the period
2. Break down by provider
3. Break down by model
4. Break down by agent
5. Get daily time series for trend analysis
```

### Step 3: Analyze Patterns

```
Identify cost patterns:
1. Which models account for the most spending?
2. Are there agents using expensive models for simple tasks?
3. Is usage concentrated or spread across providers?
4. Are there traffic spikes at certain times?
5. Is token usage efficient (short prompts vs long)?
```

### Step 4: Generate Recommendations

```
Based on patterns, recommend:

Model substitution:
- If agent uses Opus for simple tasks → suggest Haiku or Sonnet
- If agent uses GPT-4o for classification → suggest GPT-4o-mini
- If high-volume agent → suggest Groq for speed + cost savings

Routing optimization:
- If one provider is more expensive → route to cheaper alternative
- If traffic is bursty → suggest cached responses for common queries
- If quality varies → A/B test cheaper models

Architecture changes:
- If agents repeat similar queries → suggest caching layer
- If token counts are high → suggest prompt optimization
- If knowledge base queries dominate → optimize retrieval (fewer chunks)
```

### Step 5: Present Report

```
1. Lead with the headline number (total spend)
2. Show breakdowns (provider, model, agent)
3. Highlight trends (growing/shrinking spend)
4. Present recommendations ordered by impact
5. Quantify potential savings
```

---

## Analysis Variations

### Quick Check
"What am I spending?" — Total spend, top 3 models, top 3 agents, one quick recommendation.

### Deep Dive
"Give me a full cost analysis" — Complete breakdown across all dimensions with trends and full recommendations.

### Comparison
"Compare this month to last month" — Side-by-side analysis with growth rates and new cost drivers.

### Optimization Focus
"How do I reduce costs?" — Skip the overview, focus entirely on actionable recommendations with estimated savings.

---

## Tips for Better Cost Management

1. **Check costs weekly** — Small changes compound; catch them early
2. **Right-size your models** — Not every query needs the most powerful model
3. **Use routing policies** — Cost-optimized routing picks the cheapest model that meets quality thresholds
4. **Monitor token usage** — Long system prompts eat budget on every request
5. **Cache common queries** — If users ask similar questions, cache the responses

---

## Related Skills

- **gateway-routing** — Set up cost-optimized routing based on analysis findings
- **manage-providers** — Add cheaper providers to expand your options
- **debug-issues** — Investigate if high costs are caused by retry loops or errors
- **deploy-stack** — Redeploy with optimized configuration
