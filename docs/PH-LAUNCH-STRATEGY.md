# Product Hunt Launch Strategy — Bonito CLI

**Status:** Pre-launch (PH account created, CLI live on PyPI v0.6.1)
**Target:** Top 5 Product of the Day
**Product:** `bonito-cli` — deploy AI infrastructure from one YAML file
**Install:** `pip install bonito-cli`
**PyPI:** https://pypi.org/project/bonito-cli/
**Platform:** https://getbonito.com

---

## Why Launch the CLI (not the platform)

- PH audience is developers — they want `pip install` not "schedule a demo"
- Terminal GIFs are compelling and scroll-stopping on PH
- Zero signup friction — install and try it in 30 seconds
- Showcase YAMLs make the value tangible immediately (`bonito deploy -f bonito.yaml`)
- The platform becomes the natural upsell, not the pitch
- CLI already has full API parity (v0.6.1): providers, agents, gateway, routing, KB, secrets, deploy
- Developer tools consistently outperform SaaS dashboards on PH

## Timing

### Best Days
- **Tuesday, Wednesday, or Thursday** — highest traffic, most voters
- Avoid Monday (people catching up) and Friday (weekend dropoff)
- PH day resets at **12:01 AM PT** — schedule launch for exactly that time

### When to Pull the Trigger
- [ ] CLI README on PyPI is polished with clear install + quickstart
- [ ] Terminal GIF/video is ready (60-90 seconds showing real workflow)
- [ ] 3-4 showcase YAML files are public in the repo
- [ ] Free tier signup works (relax invite-only for PH day or auto-approve)
- [ ] Support capacity for launch day (respond to every comment within 1 hour)

## Launch Assets Needed

### 1. Tagline (60 chars max)
Options:
- "Deploy AI agents across any cloud from one YAML file"
- "pip install bonito-cli — manage all your AI providers"
- "One CLI to connect, route, and deploy AI everywhere"

### 2. Description (260 chars max)
"bonito-cli lets you connect AI providers (AWS, Azure, GCP, OpenAI, Anthropic, Groq, OpenRouter), deploy governed agents, set up routing policies, and manage your entire AI stack — all from a single YAML file. pip install bonito-cli and you're running in 30 seconds."

### 3. Topics/Categories
- Developer Tools
- Artificial Intelligence
- Command Line Tools
- Open Source

### 4. Terminal Demo (60-90 seconds)

This is the hero asset. Record a real terminal session showing:

```
# Install (5s)
pip install bonito-cli

# Login (5s)
bonito auth login

# Show what's available (5s)
bonito --help

# Connect a provider (10s)
bonito providers connect openai --api-key sk-...

# List available models (5s)
bonito models list

# Deploy a full showcase from YAML (15s)
cat showcase.yaml  # show the file briefly
bonito deploy -f showcase.yaml
# output: provider connected, agent created, routing policy set, KB uploaded

# Test the agent (10s)
bonito agents execute <agent-id> "Summarize our Q1 security incidents"
# streaming response comes back

# Check costs (5s)
bonito costs summary

# Gateway curl (10s)
curl -H "Authorization: Bearer bn-..." https://api.getbonito.com/v1/chat/completions \
  -d '{"model": "gpt-4o", "messages": [{"role": "user", "content": "hello"}]}'
# response streams back

# CTA (5s)
# "7 providers. 300+ models. One CLI. pip install bonito-cli"
```

Tools: asciinema or VHS (Charm) for the terminal recording, then convert to GIF/MP4.

### 5. Screenshots (4-5)
- Terminal: `bonito deploy -f showcase.yaml` output
- Terminal: `bonito models list` showing models across providers
- Terminal: `bonito agents execute` with streaming response
- Dashboard: what it looks like when you log into getbonito.com after CLI setup
- YAML file: the showcase YAML itself (clean, readable)

### 6. Showcase YAML Files

These are the killer asset. Each one should be a complete, copy-paste-and-go file:

**showcase-quickstart.yaml** — Connect OpenAI + deploy a simple agent
```yaml
provider:
  type: openai
  credentials:
    api_key: ${OPENAI_API_KEY}

agent:
  name: "My First Bonito Agent"
  model_id: gpt-4o
  system_prompt: "You are a helpful assistant."
  tools:
    mode: none
```

**showcase-multi-provider.yaml** — Connect 3 providers + routing policy
```yaml
providers:
  - type: openai
    credentials: { api_key: ${OPENAI_API_KEY} }
  - type: anthropic
    credentials: { api_key: ${ANTHROPIC_API_KEY} }
  - type: groq
    credentials: { api_key: ${GROQ_API_KEY} }

routing:
  name: "cost-optimized"
  strategy: cost
  primary_model: groq/llama-3.3-70b
  fallback_models:
    - openai/gpt-4o-mini
    - anthropic/claude-3-5-haiku
```

**showcase-support-agent.yaml** — Full governed agent with KB + tools
```yaml
provider:
  type: openai
  credentials: { api_key: ${OPENAI_API_KEY} }

knowledge_base:
  documents:
    - path: ./docs/support-guide.md
    - path: ./docs/faq.md

agent:
  name: "Support Bot"
  model_id: gpt-4o
  system_prompt: "You are a support agent. Use the knowledge base to answer questions accurately. Cite sources."
  tools:
    mode: allowlist
    allowed: [kb_search]
  model_config:
    temperature: 0.3
    max_tokens: 1024
```

**showcase-enterprise.yaml** — Multi-cloud with failover, compliance, cost tracking
```yaml
providers:
  - type: aws
    credentials:
      access_key_id: ${AWS_ACCESS_KEY}
      secret_access_key: ${AWS_SECRET_KEY}
      region: us-east-1
  - type: azure
    credentials:
      azure_mode: foundry
      tenant_id: ${AZURE_TENANT}
      client_id: ${AZURE_CLIENT}
      client_secret: ${AZURE_SECRET}
      subscription_id: ${AZURE_SUB}
  - type: gcp
    credentials:
      project_id: ${GCP_PROJECT}
      service_account_json: ${GCP_SA_KEY}

routing:
  name: "enterprise-failover"
  strategy: failover
  primary_model: aws/us.anthropic.claude-sonnet-4-20250514-v1:0
  fallback_models:
    - azure/gpt-4o
    - gcp/gemini-2.0-flash

agents:
  - name: "Tier 1 Support"
    model_id: aws/us.anthropic.claude-sonnet-4-20250514-v1:0
    system_prompt: "Enterprise support agent with access to internal KB."
    tools:
      mode: allowlist
      allowed: [kb_search, http]
      http_allowlist: ["https://internal-api.company.com/*"]
```

### 7. First Comment (by maker)

"Hey PH! I'm Shabari. I built bonito-cli because I was tired of juggling 3 cloud consoles, 3 billing dashboards, and 3 sets of API docs just to manage AI at work.

Every cloud has great models. None of them talk to each other. So I built a CLI that connects them all from a single YAML file.

What you can do:
- `bonito deploy -f showcase.yaml` — connect providers, create agents, set routing policies in one shot
- 7 providers supported (AWS, Azure, GCP, OpenAI, Anthropic, Groq, OpenRouter)
- 300+ models through one gateway endpoint
- Governed AI agents with budget caps and audit trails
- Smart routing with automatic failover across providers

Free tier: 1 provider, 25K requests/month, full model catalog, AI agents.

I'll be here all day. Try it: `pip install bonito-cli`"

## Pre-Launch Checklist (2 weeks before)

### Week -2
- [ ] Lock down launch date (Tuesday-Thursday)
- [ ] Create showcase YAML files and add to repo
- [ ] Record terminal demo with asciinema or VHS
- [ ] Polish CLI README on PyPI (install, quickstart, feature list)
- [ ] Write tagline, description, first comment
- [ ] Create "launching soon" page on PH
- [ ] Prepare social posts (LinkedIn, X) for launch day
- [ ] Draft personal DMs to send to supporters on launch morning
- [ ] Line up 10-15 people who will check it out + leave genuine comments in first 2 hours

### Week -1
- [ ] Test full flow end-to-end: pip install -> login -> deploy YAML -> see dashboard
- [ ] Decide: keep invite-only or open registration for PH day (recommend: open it)
- [ ] Prepare a PH-exclusive offer if needed (extended free tier? bonus request quota?)
- [ ] Schedule the launch on PH (goes live at 12:01 AM PT)
- [ ] Brief anyone helping with support/responses on launch day
- [ ] Pre-write responses to likely questions (see FAQ section below)

## Launch Day Playbook

### 12:01 AM PT — Go Live
- Launch goes live automatically
- Post first maker comment immediately
- Share on X (@BonitoAI) and LinkedIn

### 6-8 AM PT — Morning Push
- Send personal DMs to supporters: "Hey, we just launched bonito-cli on Product Hunt! Would mean a lot if you checked it out: [link]"
- Post in LAUNCH Cohort 37 Slack
- Post in relevant Discord servers (AI engineering, DevTools)
- DO NOT ask people to "upvote" — ask them to "check it out" (PH penalizes vote brigading)

### 9 AM - 6 PM PT — All Day
- Respond to EVERY comment within 1 hour
- Share updates on X/LinkedIn as milestones hit (#5, #3, #1)
- If someone asks a question, demo it live in terminal and post a Loom/screenshot

### 6 PM PT — Evening
- Thank everyone who supported
- Post final update comment with the day's stats
- Start following up with people who signed up via CLI

## Post-Launch (Week +1)

- [ ] Write a "lessons learned" post for LinkedIn
- [ ] Follow up with every PH commenter who showed interest
- [ ] Add PH badge to getbonito.com ("Featured on Product Hunt")
- [ ] Track installs from PH (check PyPI download spike)
- [ ] Track signups with UTM: ?ref=producthunt
- [ ] Retarget PH visitors with CLI-focused content

## FAQ — Pre-Written Responses

**"How is this different from LiteLLM?"**
LiteLLM is open-source routing middleware — great for proxying requests. Bonito is the full lifecycle: onboarding, IaC generation, governance, compliance, cost tracking, routing, AND governed AI agents. LiteLLM is one layer of what we do (and we actually use it under the hood for the gateway).

**"Why not just use each cloud's CLI?"**
You could, but then you're writing glue code across 3 different CLIs, 3 auth systems, 3 billing APIs. bonito-cli gives you one interface, one YAML, one deploy command across all of them. Plus you get things none of the cloud CLIs offer: cross-provider routing, failover, unified cost tracking, governed agents.

**"Is this open source?"**
The CLI is published on PyPI. The MCP server (bonito-mcp) is also on PyPI with 18 tools for Claude Desktop integration. The platform itself is not open source — it's a managed service.

**"What about security? I'm passing cloud credentials."**
Credentials are encrypted with AES-256-GCM and stored in HashiCorp Vault (or encrypted DB as fallback). We never store plaintext credentials. Your AI requests route through your own cloud accounts — we never proxy your data through our infrastructure.

**"How does pricing work?"**
Free tier: 1 provider, 25K gateway requests/month, full model catalog, AI agents. Pro: $499/mo for 3 providers, 250K requests, smart routing, failover. Enterprise: custom. You only pay Bonito for the platform — model inference runs on your own cloud accounts.

**"Can I self-host?"**
Not yet, but it's on the roadmap for Enterprise/Scale customers (VPC Gateway Agent).

## Competitor Launches to Study

Look at how these tools launched on PH — what worked, what got upvotes:
- Portkey.ai — proxy/gateway focus
- LiteLLM — open-source routing
- Helicone — observability
- Langfuse — tracing
- Cursor — AI code editor (different product but great PH launch execution)

Our edge: nobody else has CLI-driven deploy of the full stack (providers + agents + routing + KB) from one YAML file.

## Support Network for Launch Day

- LAUNCH Cohort 37 members (125+ founders)
- Elliot Cohen / Foundations network
- Bulletproof (Chris) — if relationship is warm enough by then
- LinkedIn connections
- X followers (@BonitoAI)
- ClawHub / OpenClaw community
- Brazil warm leads
- Any design partners / early users

## Metrics to Track

- PH rank (goal: Top 5 Product of the Day)
- Upvotes + comments
- PyPI downloads (day-of spike)
- Website visits from PH referral
- Free tier signups
- Provider connections made via CLI
- Showcase YAML deploys

## Multi-Launch Strategy

Don't burn everything on one launch. Consider staggering:

1. **Launch 1: bonito-cli** (this one) — Developer tool angle, pip install, YAML deploy
2. **Launch 2: Bonobot Agents** — "Governed AI agents for enterprise" — agent canvas, visual builder, security model
3. **Launch 3: bonito-mcp** — "18 AI ops tools for Claude Desktop" — ride the MCP/Claude wave

Each launch targets a slightly different audience and gives 3 shots at PH visibility over 2-3 months.

---

## Notes

- PH account already created
- CLI is live on PyPI (v0.6.1) with full API parity
- MCP server also on PyPI (bonito-mcp, 18 tools)
- ClawHub listing exists (clawhub.ai/shabarirepo/bonito)
- Anthropic knowledge-work-plugins PR #148 is open
- Voiceover audio files in docs/ could supplement the terminal demo
- Invite-only registration is currently on — MUST decide whether to open for PH day
