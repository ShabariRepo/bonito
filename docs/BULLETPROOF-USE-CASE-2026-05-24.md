# Bonito AI × Bulletproof — Partnership Proposal

**Prepared for:** Christopher Simm, CTO — Bulletproof, a GLI Company
**Prepared by:** Bonito AI
**Date:** May 2026

---

## Executive Summary

Bulletproof manages IT and security operations for 50,000+ users across 300+ client sites spanning gaming, government municipalities, finance, healthcare, and more. This proposal outlines three partnership models between Bonito AI and Bulletproof — each building on the last — to reduce operational costs, create new revenue streams, and position Bulletproof as an AI-forward managed services provider.

---

## How Bulletproof Connects to Bonito Today

Bulletproof has 3 internal developers plus a SharePoint/Power Automate team, currently being merged into an interim virtual AI group. The team already uses Claude Code as part of their workflow. Bonito integrates directly into this setup:

**Gateway Integration (5 minutes):**
Bonito provides a single OpenAI-compatible API endpoint. Any tool that speaks OpenAI's API — including Claude Code, custom scripts, internal apps — can route through Bonito by pointing to the gateway URL and using a `bn-` prefixed API key.

```bash
# Claude Code / CLI — point to Bonito gateway
export ANTHROPIC_BASE_URL=https://api.getbonito.com/v1
export ANTHROPIC_API_KEY=bn-your-key-here

# Every Claude Code request now flows through Bonito with:
# ✓ Unified cost tracking
# ✓ Audit logging
# ✓ Model access policies
# ✓ Budget controls per team/project
```

**What this gives Bulletproof immediately:**
- See exactly what every engineer is spending on AI, by person, by model, by day
- Set budget caps so no single project blows through credits
- Enforce model policies (e.g., only approved models for government client work)
- Full audit trail of every AI request — critical for compliance-sensitive clients
- Intelligent failover — if Anthropic has an outage, Bonito reroutes to an equivalent model on AWS Bedrock or Azure

---

## Scenario 1: Tier 1 Support Automation

### The Problem
Bulletproof currently employs ~50 Tier 1 support agents at a cost of $55–70K/year. These agents handle high-volume, repetitive tasks: password resets, basic troubleshooting, ticket triage, user provisioning, connectivity issues, and "how do I..." questions — across 300+ client environments with different runbooks, SOPs, and escalation procedures.

### The Solution
Deploy Bonito-powered AI agents as the **first line of response** for Tier 1 support tickets. The goal: deflect 40–60% of tickets automatically, reduce Tier 1 headcount by 50%, and improve response times from hours to seconds.

### How It Works

**Phase 1 — Knowledge Base Setup (Weeks 1–2)**
- Bulletproof provides per-client runbooks, SOPs, KB articles, escalation matrices, and common resolution scripts
- Bonito ingests these into isolated Knowledge Bases — one per client or client group
- Documents are chunked, embedded, and indexed for real-time retrieval
- Bulletproof's team reviews and validates the KB content — they know the clients, we know the platform

**Phase 2 — Agent Configuration (Weeks 2–3)**
- Bonito builds and configures the Tier 1 support agents within the Bonobot framework
- Each agent is scoped to a project (e.g., "Gaming Clients", "Municipal Clients", "Enterprise Clients")
- Agents are configured with:
  - **Approved models only** — locked to models that meet compliance requirements
  - **Per-client KB access** — agent queries the right runbook for the right client
  - **Hard budget stops** — monthly spend caps per agent
  - **Escalation rules** — confidence thresholds that trigger human handoff
  - **Human-in-the-loop approval** — for sensitive actions (account changes, access provisioning)
  - **Complete audit trail** — every interaction logged for compliance

**Phase 3 — Integration & Rollout (Weeks 3–4)**
- Agent exposed via API or embeddable chat widget for Bulletproof's ticketing system
- Integration with existing ITSM (Halo ITSM) and SIEM (Microsoft Sentinel)
- Pilot with 2–3 low-risk client environments
- Measure deflection rate, resolution accuracy, escalation rate

**Phase 4 — Scale (Months 2–3)**
- Roll out to all client environments
- Bulletproof reduces Tier 1 headcount by 25 agents
- Remaining human agents handle escalations with full AI-provided context
- Continuous improvement: agent learns from resolved tickets via persistent memory

### What Bulletproof Provides
- Client runbooks, SOPs, KB articles, resolution scripts
- Access to ticketing system for integration
- Feedback on agent accuracy during pilot
- Escalation rules and SLA requirements per client

### What Bonito Provides
- Agent build, configuration, and deployment
- Knowledge Base ingestion and management
- Ongoing platform hosting and support
- Dashboard for monitoring agent performance, costs, and accuracy

### Compliance Considerations
- **Government municipality clients:** Full audit trails, data residency controls, role-based access. All data stays within Bonito's governed infrastructure — no data leaks to third-party AI providers.
- **Gaming clients (GLI standards):** Agent interactions are logged and auditable, meeting NIGC MICS and GLI compliance requirements.
- **SOC 2:** Bonito's architecture supports SOC 2 controls. Bulletproof achieved SOC 2 Type 2 in 2024 — the AI layer maintains that posture.

### ROI
| Metric | Current | With Bonito |
|--------|---------|-------------|
| Tier 1 agents | ~50 | ~25 |
| Annual Tier 1 cost | $55–70K | ~$30–35K |
| Avg response time | Hours | Minutes |
| Coverage | Shift-dependent | 24/7/365 |
| Audit trail | Manual | Automatic |
| **Estimated annual savings** | | **$25–35K** |

---

## Scenario 2: White-Label Resale — Bulletproof as AI Managed Service Provider

### The Opportunity
Bulletproof already sells managed IT and managed security to 300+ clients. Adding **managed AI** as a third pillar is a natural extension. White-label Bonito as Bulletproof's own AI operations platform and sell it as a managed service to existing and new clients.

### How It Works

**What Bulletproof gets:**
- Bonito platform with Bulletproof branding (logo, colors, custom domain)
- Multi-tenant architecture — each Bulletproof client gets their own isolated org
- Bulletproof acts as the admin layer, managing client orgs, provisioning users, setting policies
- Full suite: AI gateway, agent framework, knowledge base, compliance, cost intelligence

**What Bulletproof sells to their clients:**
- "Managed AI" service — clients get governed AI access without building anything
- AI gateway for client dev teams (route all AI calls through a governed endpoint)
- Custom AI agents built by Bulletproof for client-specific use cases
- Knowledge base management — Bulletproof maintains client KBs
- Compliance reporting — AI usage reports for auditors

**Revenue model:**
- Bulletproof sets their own pricing (markup over Bonito cost)
- Example: Bonito charges Bulletproof $X/mo per client org. Bulletproof charges client $2–3X/mo as part of their managed service bundle.
- Margin on the AI layer is pure services revenue for Bulletproof

**How the dev team connects:**
Bulletproof's dev team (3 developers + power automate engineers) would use Bonito to:
- Build and configure agents for their clients
- Manage Knowledge Bases per client
- Set up routing policies and cost controls
- Monitor usage and generate compliance reports
- All via the Bonito dashboard or API — their Claude Code terminals route through the same gateway

**What's needed from Bonito:**
- White-label theming (custom branding on dashboard)
- Partner admin console (Bulletproof manages multiple client orgs)
- Bulk provisioning APIs
- SLA and support agreement

**What's needed from Bulletproof:**
- Sales and client relationship management
- First-line support for their clients' AI questions
- Agent configuration and KB management (with Bonito's guidance)

### Why This Works for Bulletproof
- They already have the client relationships and trust
- Their clients already pay them for managed IT and security — AI is the natural next ask
- Gaming and government clients can't just sign up for ChatGPT — they need a governed, auditable platform sold by a trusted vendor they already work with
- Bulletproof becomes a one-stop shop: managed IT + managed security + managed AI

---

## Scenario 3: Referral / Channel Partner

### The Opportunity
Simplest model. When Bulletproof clients are onboarding AI or asking about AI strategy, Bulletproof refers them to Bonito. Bonito handles the sale, onboarding, and support. Bulletproof gets a cut.

### How It Works

**Referral structure:**
- Bulletproof identifies a client interested in AI operations
- Introduces them to Bonito (warm intro, joint call, or direct referral)
- If the client signs with Bonito, Bulletproof receives a referral fee

**Suggested terms:**
- 15–20% of first-year contract value, or
- 10% recurring revenue share for the life of the client, or
- Flat referral fee per qualified deal (e.g., $2,500–$5,000)

**What Bulletproof provides:**
- Warm introductions to clients in their network
- Context on the client's needs, environment, and compliance requirements
- Optional: joint positioning in proposals ("Bulletproof for IT + Security, Bonito for AI")

**What Bonito provides:**
- Full sales, onboarding, and support for referred clients
- Partner portal with referral tracking and commission reporting
- Co-marketing materials (case studies, one-pagers)
- Priority support for partner-referred clients

### Why This Works
- Zero engineering effort from Bulletproof
- Monetizes conversations they're already having ("our clients keep asking about AI")
- Builds toward Scenario 2 as Bulletproof sees Bonito in action with their clients
- Government and gaming clients referred by a trusted MSP convert at higher rates

---

## What's Already Proven (May 2026)

These are not planned features — they've been tested in production with a live enterprise customer running autonomous AI agents on Bonito:

| Capability | Status | Evidence |
|---|---|---|
| Multi-agent orchestration | **Production** | 8 agents coordinating autonomously (triage → specialist → execution) |
| Agent-to-agent delegation (`invoke_agent`) | **Built & tested** | Synchronous delegation with depth limiting, parallel fan-out support |
| Breadcrumbs tracing | **Production** | Full delegation tree visible in UI — which agent called which, with what message, what response |
| Session message history | **Production** | Complete audit trail of every interaction per session |
| Multi-provider gateway failover | **Production** | Anthropic → Groq → AWS Bedrock automatic failover |
| Per-agent model configuration | **Production** | Temperature, max_tokens, model selection per agent |
| Knowledge Base RAG | **Production** | pgvector HNSW, per-project isolation, semantic search |
| Human-in-the-loop approval queues | **Built** | Risk assessment, auto-approve conditions, timeout handling |
| Budget caps & rate limiting | **Built** | Per-agent RPM limits, cost tracking per session |
| Scheduled execution (cron) | **Built** | Timezone-aware, multi-channel delivery |
| PATCH/PUT agent configuration via API | **Production** | Full CRUD for agents, connections, groups, schedules |
| External orchestration tracing | **Production** | `parent_agent_id` flag logs delegation records for code-orchestrated pipelines |

### What still needs a live test for Bulletproof

The production customer above uses **external orchestration** (their pipeline code calls each agent). Bulletproof needs **native delegation** — the Triage Router agent autonomously decides to call `invoke_agent` to hand off to specialists.

The `invoke_agent` tool is built and unit-tested in the agent engine. It:
- Only appears as a tool when the agent has outbound connections (`connection_type: handoff`)
- Validates the target agent exists and belongs to the same org
- Recursively creates a sub-engine with depth tracking (max depth: 2)
- Runs parallel `invoke_agent` calls concurrently via `asyncio.gather`
- Logs the delegation in the session (visible in Breadcrumbs)

**COMPLETED (May 24, 2026):** We built and tested this internally. Results:

**Bulletproof Tier 1 Pilot (Production — api.getbonito.com):**
- Project: `ef7c1fd9-0852-401f-8f7e-1e2330139190`
- Triage Router (gpt-4o-mini, tool_policy: allowlist[invoke_agent]) → 3 specialists
- Test 1: VPN ticket → Router autonomously delegated to Connectivity Agent via `invoke_agent` ✓
- Test 2: Password reset ticket → Router delegated to Password Agent ✓
- Breadcrumbs: Full delegation chain visible (tool_call records in session messages) ✓

**Duncan Lane Trading System (Local Dev — same architecture):**
- Signal Router → Edge Validator → Risk Manager → Trade Executor (4-agent chain)
- Test 1: ENTER signal — full chain executed, 8 messages in Breadcrumbs ✓
- Test 2: SKIP signal — chain short-circuited correctly, 4 messages ✓

Native `invoke_agent` delegation is **production-ready**. No feature build needed for the demo.

---

## Microsoft Integration Plan (Sentinel + Halo ITSM)

Bulletproof's stack:
- **Microsoft Sentinel** — SIEM, primary alert source, investigation playbooks
- **Halo ITSM** — ticket management, closure synced from Sentinel
- **Workflow:** Tier 1 analysts investigate Sentinel alerts → follow internal playbooks → remediate → close in Halo

### Sentinel → Bonito (Alert Ingestion)

**How it works:**
1. Sentinel alert fires (via Analytics Rule or Automation Rule)
2. Sentinel calls a Logic App or direct webhook → `POST https://api.getbonito.com/api/agents/{triage_router_id}/execute`
3. The message payload contains: alert severity, title, description, affected entities, MITRE tactic, incident URL
4. Triage Router classifies and delegates to the appropriate specialist agent

**Sentinel webhook payload example:**
```json
{
  "message": "SENTINEL ALERT: Severity=High | Title='Suspicious login from unusual location' | Entities=[user:jdoe@client.com, ip:203.0.113.42] | Tactic=InitialAccess | Client=GamingCo | IncidentURL=https://portal.azure.com/..."
}
```

**What Bulletproof configures in Sentinel:**
- Automation Rule: "When incident created → call webhook"
- Filter by severity if desired (e.g., only Medium+ trigger the AI agent)
- Logic App alternative for richer pre-processing (attach entity details, prior incidents)

**No custom code required.** Sentinel Automation Rules support HTTP webhooks natively. The agent receives the alert as a message, classifies it, and delegates.

### Halo ITSM Integration (Ticket Creation & Updates)

**How it works:**
Bonito agents use the built-in `http_request` tool to call Halo ITSM's REST API:

| Action | Halo API Call |
|---|---|
| Create ticket | `POST /api/Tickets` |
| Update ticket | `PUT /api/Tickets/{id}` |
| Add note | `POST /api/Tickets/{id}/Notes` |
| Close ticket | `PUT /api/Tickets/{id}` (status change) |
| Get ticket details | `GET /api/Tickets/{id}` |
| Search tickets | `GET /api/Tickets?search=...` |

**Agent workflow example:**
1. Specialist agent resolves a password reset
2. Agent calls `http_request` → `POST /api/Tickets` with: client, category, description, resolution notes, time spent
3. If the ticket came from Sentinel, agent also calls Sentinel API to update incident status

**Authentication:**
- Halo ITSM API uses OAuth2 client credentials (client_id + client_secret)
- Stored in Bonito's Org Secrets (Vault-backed) and injected into agent runtime
- Agent references credentials via `{{secrets.halo_client_id}}` and `{{secrets.halo_client_secret}}` in its HTTP tool config

**What Bulletproof provides:**
- Halo ITSM API credentials (client_id, client_secret)
- Halo instance URL
- Ticket field mappings (which fields are required per client, custom field IDs)
- Sentinel workspace details for the webhook/Logic App setup

### Microsoft Sentinel — Playbook-Driven Investigation

Beyond alert triage, the agents can run Sentinel playbook logic:

1. Alert arrives: "Multiple failed logins from IP 203.0.113.42"
2. Agent queries Sentinel via `http_request`:
   - `GET /api/incidents/{id}/entities` — who/what is affected
   - `GET /api/incidents/{id}/alerts` — related alerts
   - Cross-reference IP against threat intelligence (via Sentinel TI API or external feeds)
3. Agent follows the runbook decision tree from its KB:
   - Is this IP known malicious? → Escalate immediately
   - Is this a legitimate travel scenario? → Check user's recent locations
   - Is this a shared account? → Flag for review
4. Agent either resolves (updates Sentinel incident to "Closed — False Positive") or escalates to Tier 2 with full investigation context attached

**Sentinel API access:**
- Uses Azure AD app registration (service principal)
- Permissions: `SecurityIncident.ReadWrite.All`, `SecurityEvents.Read.All`
- Credentials stored in Bonito Vault

---

## Recommended Path Forward

We recommend starting with **Scenario 1** (Tier 1 support agents) as an immediate proof of value, with **Scenario 3** (referral) running in parallel at zero cost. **Scenario 2** (white-label) becomes the long-term play once the agent deployment proves ROI.

**Timeline:**

| Phase | Target |
|-------|--------|
| May 29, 2026 | In-person meetup — align on scope, tooling list |
| ~~Week of June 2~~ **DONE May 24** | ~~Internal test: native `invoke_agent` delegation~~ ✅ Proven on production + local dev |
| Mid–End June 2026 | Demo to Bulletproof dev team: live multi-agent triage demo, Sentinel webhook, Halo API integration |
| July 2026 | NDA signed, possibly MSA. Bulletproof shares sample runbooks/SOPs + Halo API creds + Sentinel workspace access |
| Aug–Sep 2026 | First pilot — 3 client environments in shadow mode (agent suggests, humans verify) |
| Post-pilot | Chris presents ROI to ELT → approval for 10x scale across business |
| Q4 2026+ | Broader rollout, headcount reduction, potential client resale |

### Pre-Demo Checklist (Before June Demo)

- [ ] Build internal test: Triage Router → 3 specialist agents with native `invoke_agent` delegation
- [ ] Confirm Breadcrumbs shows full delegation tree in UI
- [ ] Create sample KBs with mock runbooks (password procedures, VPN troubleshooting, software requests)
- [ ] Test Sentinel webhook → agent execution flow (use synthetic alerts)
- [ ] Test agent → Halo ITSM API ticket creation (use Halo sandbox if available)
- [ ] Record demo video showing: alert arrives → triage → delegation → resolution → ticket created → Breadcrumbs visible
- [ ] Prepare cost comparison slide: current Tier 1 spend vs projected with Bonito

**Next step:** In-person meeting May 29 to finalize scope. Internal `invoke_agent` test runs week of June 2. Demo phase begins mid-June with Bulletproof's dev teams. Chris is prepping a tooling list for the Tier 1 security stack (Microsoft Sentinel, Halo ITSM, and supporting tools).

---

**Bonito AI**
https://getbonito.com
shabari@bonito.ai
