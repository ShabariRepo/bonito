---
name: debug-issues
description: Troubleshoot gateway errors, provider failures, agent issues, and routing problems. Check logs, verify connections, test endpoints, and diagnose root causes. Trigger with "why is my agent failing", "debug gateway", "check provider status", "test my setup", "something is broken", "agent not responding", "getting errors", "diagnose my issue", or "troubleshoot".
---

# Debug Issues

Diagnose and fix problems with your Bonito gateway, providers, agents, and routing. This skill systematically checks each layer of your infrastructure, identifies the root cause, and guides you to a fix.

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                       DEBUG ISSUES                               │
├─────────────────────────────────────────────────────────────────┤
│  ALWAYS (works standalone with Bonito API)                       │
│  ✓ Gateway health: API status, connectivity, authentication     │
│  ✓ Provider checks: credential validity, API reachability       │
│  ✓ Agent diagnostics: config errors, model availability         │
│  ✓ Routing tests: policy resolution, failover behavior          │
│  ✓ Log analysis: recent errors, patterns, error rates           │
│  ✓ Guided fixes: step-by-step resolution for common issues      │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                      │
│  + Monitoring: error dashboards, latency graphs, historical data│
│  + Slack: notify team about incidents and resolutions            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Getting Started

Describe the problem:

- "My support agent isn't responding"
- "Getting 401 errors on the gateway"
- "Why is latency so high?"
- "Bedrock requests are failing"
- "Routing isn't falling back to OpenAI"
- "Test my entire setup"
- "Something broke after I changed the routing config"

I'll run diagnostics, identify the root cause, and walk you through the fix.

---

## Connectors (Optional)

Connect your tools to supercharge this skill:

| Connector | What It Adds |
|-----------|--------------|
| **Monitoring** | Historical error rates, latency trends, traffic patterns for deeper analysis |
| **Slack** | Post incident reports and resolution steps to your team channel |

> **No connectors?** No problem. The Bonito API provides logs, health checks, and diagnostic endpoints.

---

## Output Format

```markdown
# Diagnostic Report

**Issue:** [User's reported problem]
**Status:** 🔴 Issue Found | 🟡 Degraded | 🟢 All Clear
**Root Cause:** [Brief description]

---

## System Health

| Component | Status | Details |
|-----------|--------|---------|
| Gateway API | ✅ Healthy | Responding in 45ms |
| Authentication | ✅ Valid | API key verified |
| Provider: Bedrock | 🔴 Down | 503 — Service unavailable |
| Provider: OpenAI | ✅ Healthy | Responding in 120ms |
| Agent: support-bot | 🔴 Error | Upstream provider failure |
| Routing: production | ⚠️ Degraded | Failover active |

---

## Error Log (Recent)

| Timestamp | Component | Error | Count |
|-----------|-----------|-------|-------|
| [Time] | aws-bedrock | 503 Service Unavailable | 47 |
| [Time] | support-bot | Upstream provider timeout | 47 |
| [Time] | routing | Failover triggered: bedrock → openai | 1 |

---

## Root Cause Analysis

**What happened:**
[Clear explanation of the issue chain]

**Why it happened:**
[Underlying cause — provider outage, misconfiguration, expired credentials, etc.]

**Impact:**
[What was affected — which agents, endpoints, users]

---

## Fix

### Immediate Action
1. [Step to resolve the acute issue]
2. [Verification step]

### Preventive Action
1. [Step to prevent recurrence]
2. [Configuration change or monitoring addition]

---

## Verification

After applying the fix:

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| [Check name] | [Expected result] | [Actual result] | ✅/🔴 |
```

---

## Execution Flow

### Step 1: Understand the Problem

```
Parse the user's report:
- Specific error message? → Start with that component
- General "it's broken"? → Run full diagnostic sweep
- Specific agent? → Start with agent health check
- Specific provider? → Start with provider check
- Performance issue? → Start with latency analysis
```

### Step 2: Gateway Health Check

```
1. Check Bonito API status via ~~bonito
   - Is the gateway reachable?
   - Is authentication valid?
   - What's the response latency?

2. If gateway is down:
   - Check API URL configuration
   - Verify API key is valid and not expired
   - Check network connectivity
   - → Report gateway-level issue
```

### Step 3: Provider Diagnostics

```
For each connected provider:
1. Check provider health via ~~bonito
   - Is the provider API reachable?
   - Are credentials still valid?
   - What's the error rate (last hour)?

2. If provider is unhealthy:
   - Test with a minimal inference request
   - Check for known outages (provider status page)
   - Verify IAM permissions (AWS) or API quotas (OpenAI)
   - Check if specific models are affected vs all models
   - → Report provider-level issue with specific error
```

### Step 4: Agent Diagnostics

```
For affected agents:
1. Get agent configuration via ~~bonito
   - Is the agent config valid?
   - Does the referenced model exist?
   - Is the referenced provider healthy?

2. Test agent directly:
   - Send a simple test message
   - Check response or error details
   - If knowledge base attached → test retrieval
   - If MCP tools attached → test tool availability

3. If agent is failing:
   - Is it a model issue? (provider down)
   - Is it a config issue? (bad system prompt, missing KB)
   - Is it a routing issue? (can't resolve model)
   - → Report agent-level issue with root cause
```

### Step 5: Routing Diagnostics

```
For affected routing policies:
1. Get routing config via ~~bonito
   - Are all referenced providers/models valid?
   - Is the failover chain properly ordered?

2. Test routing resolution:
   - Where does a test request route to?
   - Does failover trigger correctly?
   - Is the routing policy active?

3. If routing is broken:
   - Missing provider reference?
   - Circular dependency?
   - All providers in the chain unhealthy?
   - → Report routing-level issue
```

### Step 6: Log Analysis

```
Pull recent logs via ~~bonito:
1. Filter by time range (last 1h, or around reported issue time)
2. Filter by component (provider, agent, routing)
3. Identify error patterns:
   - Sudden spike? → Provider outage or deployment change
   - Gradual increase? → Rate limiting or resource exhaustion
   - Intermittent? → Network flakiness or timeout thresholds
4. Count errors by type to find the dominant issue
```

### Step 7: Present Diagnosis and Fix

```
1. Summarize what's wrong (clear, non-technical language)
2. Explain why (root cause)
3. Provide step-by-step fix
4. Include verification steps
5. Suggest preventive measures
```

---

## Common Issues and Fixes

### Authentication Failures (401/403)
- **Cause:** Expired or invalid API key
- **Fix:** Regenerate API key, update configuration
- **Prevention:** Set up key rotation reminders

### Provider Timeouts (504/Timeout)
- **Cause:** Provider overloaded, network issues, or model cold start
- **Fix:** Retry, or failover to alternate provider
- **Prevention:** Configure failover routing, set appropriate timeouts

### Model Not Found (404)
- **Cause:** Model name typo, model not enabled on provider, or model deprecated
- **Fix:** Verify model name, enable model access in provider console
- **Prevention:** Use model aliases, pin to stable model versions

### Rate Limiting (429)
- **Cause:** Too many requests for your API tier
- **Fix:** Reduce request rate, upgrade tier, or spread across providers
- **Prevention:** Configure load balancing, implement request queuing

### Agent Config Errors
- **Cause:** Invalid system prompt, missing knowledge base reference, bad tool config
- **Fix:** Review and correct agent configuration
- **Prevention:** Validate configs before deploying

### Routing Loops
- **Cause:** Circular references in routing policy
- **Fix:** Review routing chain, remove circular dependencies
- **Prevention:** Use the deploy-stack skill which validates dependencies

---

## Tips for Faster Debugging

1. **Include the error message** — "It's broken" is harder to debug than "I'm getting a 503"
2. **Note when it started** — "It worked yesterday" narrows the search
3. **Check one layer at a time** — Gateway → Provider → Agent → Routing
4. **Test with curl** — Bypass your application to isolate the issue
5. **Check provider status pages** — Sometimes it's not your fault

---

## Related Skills

- **manage-providers** — Reconnect or reconfigure providers after fixing issues
- **gateway-routing** — Fix or reconfigure routing policies
- **deploy-stack** — Redeploy infrastructure after making fixes
- **cost-analysis** — Check if errors are causing cost spikes (retry storms)
