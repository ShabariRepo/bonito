# Managed Agents - Rollout Plan

## Vision
Two-tier managed agent offering that turns Bonito from "AI infrastructure" into "AI solutions."
Customers don't just get a platform - they get working AI teams on day one.

---

## Tier 1: Solution Kits (Simple Managed Agents)
**"Upload your docs, pick a template, deploy in 10 minutes"**

### What the customer gets
- Pre-built agent with battle-tested prompts and behavior
- Auto-selected models based on their connected cloud providers
- RAG-powered with their own documents
- Embeddable chat widget (for customer-facing agents)
- Works on any single cloud or multi-cloud

### Starter Templates (ship first 4)

**1. Customer Service Bot**
- Answers product/service questions from uploaded docs
- Warm, professional tone with escalation paths
- "Talk to a human" escape hatch
- Widget-ready for website embedding
- Best for: any company with a product/service

**2. Internal Knowledge Assistant**
- Staff-facing Q&A over company docs, policies, processes
- Handles onboarding questions, policy lookups, process guides
- Stricter tone, more precise answers
- Best for: companies with 50+ employees

**3. Sales Qualification Bot**
- Engages website visitors, qualifies leads
- Asks discovery questions, captures contact info
- Recommends products/services based on needs
- Hands off to sales team with context summary
- Best for: B2B companies, service businesses

**4. Content Assistant**
- Generates blog posts, social captions, email drafts
- Trained on brand voice from uploaded style guides
- Internal tool (not customer-facing)
- Best for: marketing teams

### Auto Model Selection Logic

```
When deploying a Solution Kit:

1. Check connected providers
2. For each provider, pick optimal model:

   GCP  -> Gemini 2.0 Flash (primary), 2.5 Flash (complex fallback)
   AWS  -> Nova Lite (primary), Nova Pro (complex fallback)
   Azure -> gpt-4o-mini (primary), gpt-4o (complex fallback)

3. If multi-cloud: use cheapest for primary, strongest for fallback
4. Customer can override, but defaults should be good enough
```

### Deploy Flow (UI)

```
Step 1: Pick a Solution Kit
  [Customer Service] [Knowledge Assistant] [Sales Bot] [Content Assistant]

Step 2: Configure basics
  - Agent name (pre-filled: "Customer Service Bot")
  - Company name
  - Tone: [Warm] [Professional] [Casual]
  - Industry (optional, refines prompts)

Step 3: Feed it knowledge
  - Upload docs (drag and drop, PDF/TXT/MD/DOCX)
  - Or connect existing AI Context
  - "We'll use these to train your agent"

Step 4: Model selection (auto, with override)
  - "Based on your GCP connection, we'll use Gemini 2.0 Flash"
  - [Use recommended] or [Choose different model]

Step 5: Deploy
  - One click
  - Agent created, AI Context indexed, ready to chat
  - Widget embed code shown (for customer-facing agents)
```

### Build Estimate: ~2 weeks

| Component | Effort | Notes |
|-----------|--------|-------|
| Solution Kit data model | 2 days | Template schema, prompt library |
| Auto model selection service | 1 day | Already have provider + model data |
| Deploy flow API (backend) | 2 days | Orchestrates agent + AI Context + config |
| Deploy flow UI (frontend) | 3 days | Wizard with 5 steps |
| 4 starter templates | 2 days | Prompts, configs, behavior tuning |
| Chat widget (embeddable) | 2 days | JS snippet, iframe, styling |
| Testing + polish | 2 days | E2E with real providers |

---

## Tier 2: Advanced Managed Agents (MCP-powered)
**"Agents that don't just answer - they do things"**

### What the customer gets (everything in Tier 1, plus)
- External integrations via MCP (Salesforce, HubSpot, Google Sheets, etc.)
- Scheduled/triggered execution (not just chat)
- Multi-agent workflows (delegation, fan-out)
- Connector credentials secured in Vault

### Advanced Templates

**1. Campaign Ops (Advertising/Marketing)**
- Weekly performance report: pulls from ad platforms, summarizes, emails team
- Content calendar: generates ideas on schedule, posts to Slack/Teams
- Lead enrichment: new lead triggers research + personalized outreach draft
- Connectors: Google Ads MCP, Meta Ads MCP, Slack MCP, email

**2. Finance Analyst**
- Cost anomaly detection: monitors cloud/SaaS spend, alerts on spikes
- Periodic reporting: weekly/monthly financial summaries
- Budget tracking: pull from accounting tools, compare to budgets
- Connectors: QuickBooks MCP, Google Sheets MCP, email

**3. Sales Operations**
- Lead follow-up: Salesforce trigger, draft personalized email, queue for approval
- Pipeline reporting: weekly pipeline summary from CRM
- Meeting prep: pull prospect data before scheduled calls
- Connectors: Salesforce MCP, HubSpot MCP, calendar, email

**4. IT/DevOps Assistant**
- Incident response: PagerDuty trigger, pull logs, suggest fixes
- Deployment monitoring: check CI/CD status, report failures
- Security scan summaries: periodic review of findings
- Connectors: GitHub MCP, AWS MCP, PagerDuty MCP, Slack MCP

### Trigger System

```
Types:
- Schedule: cron expressions ("every Monday 9am", "daily at 6pm")
- Webhook: HTTP endpoint that wakes the agent
- Event: triggered by another agent or external system

Storage:
- agent_triggers table (already in DB schema)
- Needs: execution engine, retry logic, history/audit

UI:
- Trigger config in agent detail panel
- Run history with status + output
```

### Connector Credential Flow

```
Step 1: Agent template says "needs Salesforce connector"
Step 2: UI prompts: "Enter your Salesforce API key"
Step 3: Key goes to Vault (encrypted, scoped to this agent + org)
Step 4: MCP server configured with Vault reference (never plaintext)
Step 5: Agent can now use Salesforce tools

Enterprise/VPC: Vault runs in their infra. Keys never leave their network.
```

### Build Estimate: ~4 weeks (after Tier 1)

| Component | Effort | Notes |
|-----------|--------|-------|
| Trigger execution engine | 4 days | Schedule runner, webhook listener |
| Trigger UI | 2 days | Config panel, run history |
| Connector credential management | 3 days | Vault integration per agent |
| Connector setup wizard UI | 3 days | Per-template connector config |
| MCP server library/catalog | 3 days | Curate, test, document 8-10 servers |
| 4 advanced templates | 3 days | Prompts, connectors, trigger configs |
| Multi-step workflow testing | 3 days | Real E2E with actual APIs |
| Polish + docs | 2 days | |

---

## Pricing

| Tier | Platform | Per Agent | Notes |
|------|----------|-----------|-------|
| DIY (current) | Pro $499/mo | $349/mo | Full control, build everything yourself |
| Tier 1 Solution Kit | Pro $499/mo | $249/mo | Lower per-agent, higher volume play |
| Tier 2 Advanced | Enterprise $2K+/mo | $449/mo | Premium for integrations + triggers |
| Friends rate (Step Sciences) | $400/mo | $150/mo | First customer, case study value |

Note: Tier 1 agents are cheaper because templates reduce our support burden.
Tier 2 agents are premium because they provide more value and complexity.

---

## Rollout Timeline

### Phase A: Tier 1 (Weeks 1-2)
- [ ] Solution Kit data model + template schema
- [ ] Auto model selection service
- [ ] Deploy flow backend (orchestration API)
- [ ] Deploy flow frontend (5-step wizard)
- [ ] 4 starter templates (prompts, configs)
- [ ] Embeddable chat widget
- [ ] Beta with Step Sciences

### Phase B: Tier 2 Foundation (Weeks 3-4)
- [ ] Trigger execution engine (schedule + webhook)
- [ ] Trigger UI in agent panel
- [ ] Connector credential management (Vault per-agent)
- [ ] Connector setup wizard

### Phase C: Tier 2 Templates (Weeks 5-6)
- [ ] Curate MCP server library (8-10 tested servers)
- [ ] 4 advanced templates with real integrations
- [ ] E2E testing with live APIs
- [ ] Documentation + pricing page update

### Phase D: Launch (Week 7)
- [ ] Update marketing site (new "Solutions" page)
- [ ] Update pitch deck
- [ ] Case study from Step Sciences
- [ ] Announce to existing users

---

## Step Sciences as Beta

Step Sciences is the perfect Tier 1 beta:
- GCP-only (simple)
- Needs customer service bot (Template #1)
- Needs internal KB (Template #2)
- Small, friendly, tolerant of rough edges
- LinkedIn post as marketing asset

Build their agents USING the Solution Kit flow. If it works for them, it works for anyone.
