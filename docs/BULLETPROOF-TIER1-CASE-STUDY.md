# Tier 1 Support Automation — Case Study & Feasibility Report

**Prepared for:** Christopher Simm, CTO — Bulletproof (GLI Group)
**Prepared by:** Bonito AI
**Date:** May 2026

---

## The Problem

Bulletproof operates ~50 Tier 1 support agents across 300+ client sites in gaming, government, finance, healthcare, and manufacturing. These agents cost $55–70K/year each — $2.75M–$3.5M in total annual labor.

Tier 1 handles the front line: high-volume, repetitive, well-documented work. The knowledge to resolve most tickets already exists in runbooks and SOPs — it's just trapped in documents that agents have to search manually. This means:

- **Slow response times** — agents read through docs while the user waits
- **Inconsistent quality** — resolution depends on which agent picks up the ticket and how well they know that client's environment
- **Shift-dependent coverage** — no 24/7 without overtime or offshoring
- **High turnover cost** — every new hire needs weeks of training on client-specific procedures

The work is well-structured. That's what makes it automatable.

---

## What the AI Agent Actually Does

This isn't a chatbot that says "have you tried restarting?" — it's a knowledge-backed agent with access to client-specific runbooks, escalation rules, and tool integrations. Here's what a ticket lifecycle looks like:

### Ticket Types and Agent Behavior

**1. Password Resets & Account Lockouts** (~30% of Tier 1 volume)

```
User: "I'm locked out of my account, employee ID 4829"

Agent workflow:
├── Verify identity (employee ID + security question or email match)
├── Query client KB → find password reset SOP for this client's IdP
├── If self-service available:
│   └── Walk user through self-service reset link (client-specific URL)
├── If requires admin action:
│   └── Create ticket in ITSM with pre-filled details, escalate to Tier 2
└── Log interaction, resolution method, and time-to-resolve
```

**Human needed?** No — unless identity verification fails or the client has a non-standard IdP with no self-service.

**2. Connectivity & VPN Issues** (~20% of volume)

```
User: "VPN won't connect from home, getting error 'connection timed out'"

Agent workflow:
├── Identify client environment → query client-specific KB
├── Match error message to known resolution paths:
│   ├── "connection timed out" → check if VPN server is up (HTTP health check)
│   ├── If server is down → escalate immediately with severity tag
│   └── If server is up → walk through troubleshooting steps:
│       ├── Step 1: Check local firewall/antivirus blocking VPN port
│       ├── Step 2: Flush DNS, renew DHCP lease
│       ├── Step 3: Reinstall VPN client (provide client-specific download link)
│       └── Step 4: If unresolved → create Tier 2 ticket with diagnostic data collected
└── Log interaction + steps attempted
```

**Human needed?** Only if the issue is infrastructure-side (server down, cert expired) — which the agent detects and escalates immediately rather than wasting time troubleshooting the user's machine.

**3. Software Installation & Access Requests** (~15% of volume)

```
User: "I need Tableau installed on my workstation"

Agent workflow:
├── Query client KB → is Tableau on the approved software list?
├── If approved:
│   ├── Check if self-service software portal exists for this client
│   ├── If yes → provide direct link + instructions
│   └── If no → create provisioning ticket with user details + approval chain
├── If not approved:
│   └── Inform user, provide process to request approval from their IT manager
├── If requires license:
│   └── Flag license availability, route to procurement if needed
└── Log request + outcome
```

**Human needed?** No — this is pure KB lookup + ticket creation.

**4. "How Do I..." Questions** (~15% of volume)

```
User: "How do I set up MFA on my work email?"

Agent workflow:
├── Identify client → determine which email platform (O365, Google Workspace, etc.)
├── Query client KB for MFA setup guide
├── Return step-by-step instructions with screenshots (if in KB)
├── Ask user to confirm resolution
└── Log interaction
```

**Human needed?** Almost never. This is what KBs are built for.

**5. Hardware Issues** (~10% of volume)

```
User: "My monitor won't turn on"

Agent workflow:
├── Basic troubleshooting (power cable, different outlet, different cable)
├── If unresolved → create hardware ticket with:
│   ├── Asset tag / serial number (ask user)
│   ├── Client site location
│   ├── Warranty status (if accessible via ITSM integration)
│   └── Priority based on role (executive → high, standard → normal)
└── Provide ticket number and expected response time per client SLA
```

**Human needed?** For physical hardware, yes — but the agent handles triage, data collection, and ticket creation. Humans just do the physical work.

**6. Ticket Triage & Routing** (~10% of volume)

```
Incoming ticket: "Production database is showing high latency on gaming floor"

Agent workflow:
├── Parse ticket content → classify severity
│   ├── Keywords: "production", "gaming floor" → HIGH priority
│   ├── Match to client SLA → 1-hour response required
├── Route to correct team based on:
│   ├── Client → Bulletproof gaming team
│   ├── Category → Infrastructure / Database
│   └── Severity → Tier 2 or Tier 3 (skip Tier 1 entirely)
├── Enrich ticket with:
│   ├── Client environment details from KB
│   ├── Related recent incidents (query ticket history)
│   └── Relevant runbook sections attached
└── Notify on-call engineer immediately
```

**Human needed?** No for triage. The agent classifies, enriches, and routes faster than a human can read the ticket.

---

### Escalation Logic

The agent doesn't guess. Every agent has a confidence threshold and hard rules:

| Condition | Action |
|-----------|--------|
| User explicitly asks for a human | Immediate handoff with full context |
| Agent confidence < 70% | Escalate with suggested resolution attached |
| Sensitive action (account deletion, access change) | Human approval required (approval queue) |
| 3+ failed resolution attempts in same session | Escalate with full transcript |
| Ticket matches known outage pattern | Auto-escalate to incident team, skip Tier 1 |
| Client has "no AI" policy | Route directly to human (per-client config) |

When the agent escalates, the human gets the full conversation transcript, KB articles referenced, steps already attempted, and a suggested resolution. The human picks up mid-stream, not from scratch.

---

## Cost Model

### Current State

| Item | Value |
|------|-------|
| Tier 1 agents | ~50 |
| Avg salary + benefits | $55,000–$70,000/yr |
| Total annual Tier 1 labor | **$2,750,000–$3,500,000** |
| Avg tickets/month (estimated) | 8,000–15,000 |
| Avg resolution time | 15–45 min |

### Projected State (Month 6+)

| Item | Value |
|------|-------|
| AI-deflected tickets | 40–60% |
| Remaining human agents needed | 20–25 |
| Agents redeployed or reduced | 25–30 |

### Bonito Platform Cost

Bulletproof uses their own cloud providers for inference — Bonito doesn't charge for token usage. Bonito is the control plane, not the compute.

| Component | Cost |
|-----------|------|
| Bonito Enterprise license | $15,000/mo |
| Implementation + onboarding | $25,000 one-time |
| LLM inference (token usage) | Bulletproof's own cloud — not a Bonito cost |
| KB storage & embedding | Included |
| **Year 1 total** | **$205,000** |
| **Year 2+ annual** | **$180,000/yr** |

### Net Savings

| Scenario | Conservative (40% deflection) | Moderate (50%) | Aggressive (60%) |
|----------|-------------------------------|-----------------|-------------------|
| Agents reduced | 20 | 25 | 30 |
| Labor saved/yr | $1,100,000–$1,400,000 | $1,375,000–$1,750,000 | $1,650,000–$2,100,000 |
| Bonito cost/yr | $180,000 | $180,000 | $180,000 |
| **Net savings/yr** | **$920,000–$1,220,000** | **$1,195,000–$1,570,000** | **$1,470,000–$1,920,000** |
| **ROI** | **6–7x** | **7–9x** | **8–11x** |

Even the conservative scenario saves ~$1M/yr. The inference costs on Bulletproof's own cloud are minimal — routine Tier 1 tickets use small, fast models (a few cents per resolution).

---

## Rollout Timeline

This is an enterprise deployment across 300+ client environments with compliance requirements. We're not rushing it.

### Phase 1 — Discovery & KB Ingestion (Weeks 1–4)

- Bulletproof provides runbooks, SOPs, escalation matrices for 5–10 pilot clients
- Bonito ingests into isolated per-client Knowledge Bases
- Joint review of KB coverage gaps — identify what's documented vs tribal knowledge
- Map ticket categories to agent capabilities (what can be automated vs what stays human)
- Define escalation rules per client
- **Deliverable:** KB coverage report, automation feasibility matrix

### Phase 2 — Agent Build & Integration (Weeks 5–8)

- Configure Bonobot agents per client group (gaming, government, enterprise)
- Set up model policies (government clients may require specific models or regions)
- Integrate with Bulletproof's ITSM (ServiceNow, ConnectWise, or similar) via MCP or API
- Build escalation workflows with human-in-the-loop approval for sensitive actions
- Set budget caps and rate limits per agent
- Internal testing with synthetic tickets
- **Deliverable:** Working agents in staging, integration tested

### Phase 3 — Shadow Mode Pilot (Weeks 9–12)

- Deploy agents in **shadow mode** on 3–5 client environments
- Agent receives every Tier 1 ticket and generates a suggested response
- Human agents see the suggestion and choose to use it, modify it, or ignore it
- Track: deflection rate, accuracy, false escalations, user satisfaction
- Zero risk — humans are still resolving every ticket, agent is just proving itself
- Iterate on prompts, KB content, escalation thresholds based on real data
- **Deliverable:** Pilot metrics report, accuracy benchmarks

### Phase 4 — Supervised Go-Live (Weeks 13–16)

- Promote to live on pilot clients — agent handles Tier 1 directly
- Start with low-risk ticket categories (password resets, FAQ, software requests)
- Human review queue for first 2 weeks (spot-check 20% of resolutions)
- Gradually expand to more ticket types as accuracy is validated
- **Deliverable:** Production deployment on pilot clients

### Phase 5 — Scale & Optimize (Months 5–8)

- Roll out to full 300+ client base in waves (20–30 clients per wave)
- Headcount reduction begins as deflection rates stabilize
- Continuous KB improvement — resolved tickets feed back into knowledge base
- Monthly performance reviews: deflection rate, CSAT, cost per ticket
- **Deliverable:** Full production deployment, headcount plan realized

**Total time to full production: 6–8 months**
**Time to first measurable impact (pilot results): 12 weeks**

---

## Integration Architecture

```
                    ┌─────────────────────────┐
                    │   Bulletproof Clients    │
                    │  (Chat Widget / Email /  │
                    │   ITSM Portal / Phone*)  │
                    └──────────┬──────────────┘
                               │
                    ┌──────────▼──────────────┐
                    │  Bulletproof ITSM        │
                    │  (ServiceNow/ConnectWise)│
                    └──────────┬──────────────┘
                               │ Webhook / API
                    ┌──────────▼──────────────┐
                    │     Bonito Platform      │
                    │                          │
                    │  ┌────────────────────┐  │
                    │  │   Bonobot Agent     │  │
                    │  │                     │  │
                    │  │  • Client KB Search │  │
                    │  │  • Ticket Creation  │  │
                    │  │  • Escalation Logic │  │
                    │  │  • Audit Trail      │  │
                    │  └────────┬───────────┘  │
                    │           │               │
                    │  ┌────────▼───────────┐  │
                    │  │  AI Gateway         │  │
                    │  │  (Multi-provider)   │  │
                    │  │                     │  │
                    │  │  Anthropic ─┐       │  │
                    │  │  OpenAI   ──┤ Auto  │  │
                    │  │  Bedrock  ──┤ Route │  │
                    │  │  Azure    ──┘       │  │
                    │  └────────────────────┘  │
                    │                          │
                    │  Compliance │ Cost Track  │
                    │  Audit Logs │ Budget Caps  │
                    └──────────────────────────┘
                               │
                    ┌──────────▼──────────────┐
                    │   Escalation Path        │
                    │                          │
                    │  Tier 2 Human Agent      │
                    │  (Full context + AI      │
                    │   suggested resolution)  │
                    └──────────────────────────┘

*Phone: Voicemail transcription → ticket → agent. Live voice is Phase 2.
```

## Agent Architecture

Production Tier 1 automation isn't one mega-agent with every runbook stuffed in. It's a multi-agent system — specialized agents with focused knowledge bases, coordinated by a triage router.

### Why Multi-Agent

A single agent loaded with 300+ clients' runbooks across every ticket category will hallucinate. It'll pull VPN troubleshooting steps from Client A's runbook when the user is from Client B. Specialist agents with scoped KBs have higher retrieval accuracy because their search space is smaller and more relevant.

### Architecture Overview

```
              Incoming Ticket (webhook / widget / email / API)
                                  │
                                  ▼
                    ┌──────────────────────────┐
                    │      Triage Router       │
                    │                          │
                    │  • Classify ticket type   │
                    │  • Identify client        │
                    │  • Assess severity/SLA    │
                    │  • Route to specialist    │
                    │                          │
                    │  KBs: client-directory,   │
                    │       escalation-matrix   │
                    └──────┬───────────────────┘
                           │
              ┌────────────┼────────────┬─────────────┐
              ▼            ▼            ▼             ▼
    ┌─────────────┐ ┌────────────┐ ┌──────────┐ ┌──────────────┐
    │  Password   │ │Connectivity│ │ Software │ │   General    │
    │  & Account  │ │  & VPN     │ │ & Access │ │   Support    │
    │             │ │            │ │          │ │              │
    │  ~45% vol   │ │  ~20% vol  │ │ ~20% vol │ │  ~15% vol    │
    │             │ │            │ │          │ │  (catch-all)  │
    └──────┬──────┘ └─────┬──────┘ └────┬─────┘ └──────┬───────┘
           │              │             │              │
           └──────────────┴──────┬──────┴──────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │   Human Escalation        │
                    │                          │
                    │  Tier 2 agent receives:   │
                    │  • Full conversation      │
                    │  • KB articles referenced  │
                    │  • Steps already tried     │
                    │  • Suggested resolution    │
                    └──────────────────────────┘
```

### Agent Specifications

**1. Triage Router** — The front door

| Setting | Value |
|---------|-------|
| Model | `auto` (cheapest available — classification is simple) |
| Knowledge Bases | `client-directory`, `escalation-matrix` |
| Tools | `search_knowledge_base`, `invoke_agent`, `delegate_task`, `send_notification` |
| Connections | Handoff to all 4 specialists, escalation to human |
| Triggers | Webhook (ITSM), API (widget/chat) |
| Purpose | Classify ticket type, identify client, assess severity, route to the right specialist. Does NOT attempt resolution. |

This agent is high-volume, low-cost. It reads the ticket, determines what kind of problem it is and which client it's from, and hands off. Fast, cheap, accurate.

**2. Password & Account Agent** — ~45% of volume

| Setting | Value |
|---------|-------|
| Model | `auto` |
| Knowledge Bases | `password-procedures`, `mfa-guides`, `identity-provider-docs` |
| Tools | `search_knowledge_base`, `http_request`, `send_notification` |
| Connections | Escalation to human |
| Purpose | Password resets, account lockouts, MFA setup, identity verification |

Handles the highest volume category. Most resolutions are KB lookups — "here's the self-service reset link for your client's IdP" or "here are the MFA setup steps for O365." Uses `http_request` to check if self-service portals are up and to create ITSM tickets when admin action is needed.

**3. Connectivity & VPN Agent** — ~20% of volume

| Setting | Value |
|---------|-------|
| Model | `auto` |
| Knowledge Bases | `vpn-procedures`, `network-runbooks`, `infrastructure-status` |
| Tools | `search_knowledge_base`, `http_request`, `send_notification` |
| Connections | Escalation to human |
| Purpose | VPN issues, network connectivity, DNS, DHCP, firewall troubleshooting |

Uses `http_request` to check VPN server health endpoints. If the server is down, it skips troubleshooting the user's machine and immediately escalates as an infrastructure incident with the right severity tag.

**4. Software & Access Agent** — ~20% of volume

| Setting | Value |
|---------|-------|
| Model | `auto` |
| Knowledge Bases | `approved-software-lists`, `provisioning-procedures`, `license-inventory` |
| Tools | `search_knowledge_base`, `http_request`, `send_notification` |
| Connections | Escalation to human |
| Purpose | Software installation requests, access provisioning, license checks |

Checks if the requested software is on the client's approved list, whether a self-service portal exists, and if licenses are available. Creates provisioning tickets with the full approval chain pre-filled.

**5. General Support Agent** — ~15% of volume (catch-all)

| Setting | Value |
|---------|-------|
| Model | `auto` |
| Knowledge Bases | `general-it-faq`, `hardware-procedures`, `onboarding-guides` |
| Tools | `search_knowledge_base`, `http_request`, `send_notification` |
| Connections | Escalation to human |
| Purpose | How-to questions, hardware triage, general IT support, anything that doesn't fit the other categories |

The safety net. If the triage router can't confidently classify a ticket into the other three categories, it goes here. For hardware issues, this agent handles triage and data collection (asset tag, serial number, warranty status, location) and creates an enriched ticket for the team that does physical work.

### Knowledge Base Strategy

**10 KBs organized by domain, not by client.**

Creating a separate KB per client (300+ KBs) is unmanageable. Instead, domain KBs contain documents from all clients, tagged and sectioned by client name. The agent's system prompt includes the client identifier, and KB search returns the most relevant results for that client.

| KB | Contents | Update Frequency |
|----|----------|-----------------|
| `client-directory` | Client names, environments, contact info, SLA tiers, special policies | Monthly |
| `escalation-matrix` | Severity rules, response time SLAs, escalation contacts per client | Monthly |
| `password-procedures` | Per-client IdP docs (Okta, Azure AD, on-prem AD), reset SOPs, self-service links | As needed |
| `mfa-guides` | MFA setup instructions per platform (O365, Google Workspace, Duo, etc.) | As needed |
| `identity-provider-docs` | IdP-specific configuration, known issues, admin procedures | As needed |
| `vpn-procedures` | VPN client setup, troubleshooting decision trees, per-client VPN configs | As needed |
| `network-runbooks` | DNS, DHCP, firewall, connectivity troubleshooting per environment | As needed |
| `approved-software-lists` | Per-client approved software, self-service portal URLs, license info | Quarterly |
| `provisioning-procedures` | Access request workflows, approval chains, onboarding checklists | As needed |
| `general-it-faq` | Common how-to guides, hardware procedures, onboarding docs | As needed |

### Failover & Reliability

Every agent uses `model_id: auto`, which means Bonito's gateway handles model selection and failover:

- **Primary model fails?** Gateway automatically retries on an equivalent model from a different provider
- **Provider outage?** Transparent failover — Anthropic down → route to OpenAI or Bedrock
- **Rate limited?** Automatic retry with backoff, then failover to next provider
- **All providers down?** Agent returns a graceful "we're experiencing issues" message and creates an ITSM ticket for human follow-up

Support agents are 24/7. Provider outages are not. Multi-provider failover is what makes this production-grade.

### Budget & Cost Controls

| Control | Setting |
|---------|---------|
| Per-agent monthly budget cap | Configurable (e.g., $500/mo for triage, $1,000/mo for password agent) |
| 80% budget alert | Notification to Bulletproof admin when approaching cap |
| Hard stop at cap | Agent stops accepting new tickets, routes everything to human |
| Per-ticket cost tracking | Logged per session — know exactly what each resolution costs |
| Rate limiting | 30 RPM default per agent, adjustable |

### Scaling Considerations

As the deployment grows, additional specialist agents may be needed:

- **Compliance & Audit Agent** — For gaming/government clients with specific regulatory requirements. Handles compliance-related queries, audit trail generation, and policy verification.
- **Onboarding Agent** — Dedicated to new user provisioning, equipment requests, and day-one setup for new hires across client organizations.
- **Incident Correlation Agent** — Monitors incoming tickets for patterns (e.g., 10 users from the same client reporting VPN issues = likely infrastructure incident, not individual troubleshooting).
- **Client-Specific Agents** — For Bulletproof's largest clients (e.g., a dedicated agent for a major gaming client with complex, unique procedures that don't fit the general KBs).
- **Reporting Agent** — Generates weekly/monthly support metrics per client: deflection rates, resolution times, common issues, KB coverage gaps. Scheduled execution via cron.

The architecture is designed to add agents without disrupting existing ones. New specialists just get registered in the triage router's connection list.

---

### Supported Integrations (Today)

| Category | Options |
|----------|---------|
| Ticketing / ITSM | ServiceNow, ConnectWise, Jira Service Desk, Freshdesk, Zendesk (via MCP or HTTP tool) |
| Chat | Embeddable widget (Bonito-hosted), Slack, Microsoft Teams |
| Email | Inbound email parsing → ticket → agent (via webhook) |
| Identity | SAML SSO (Okta, Azure AD, Google Workspace) — already built |
| Monitoring | PagerDuty, Datadog, Grafana (via MCP or webhook triggers) |
| Knowledge Sources | PDF, DOCX, TXT, Markdown, HTML — parsed and embedded automatically |

### What's Not Built Yet (Honest Assessment)

| Feature | Status | Timeline |
|---------|--------|----------|
| White-label branding (custom logo, colors, domain) | Not started | Would scope during contract negotiation |
| Partner admin console (Bulletproof manages client orgs) | Not started | 4–6 weeks to build |
| Phone/voice integration | Not started | Phase 2 — depends on Bulletproof's telephony stack |
| Bulk KB sync from Confluence/SharePoint | Partial (manual upload today) | 2–3 weeks |

We'd rather be upfront about what's built vs what needs building than overpromise.

---

## Why This Works on Bonito (and Not DIY)

Bulletproof's engineering team is 6–15 people. They could build a support chatbot. They can't build what's behind it:

**Multi-provider failover.** If Anthropic rate-limits or has an outage at 2 AM, Bonito automatically reroutes to an equivalent model on AWS Bedrock or Azure. Bulletproof's clients don't notice. A DIY chatbot hardcoded to one provider goes down when the provider goes down.

**Per-client isolation.** Each client's KB, policies, and data are isolated at the platform level. Government clients' data never touches gaming clients' inference. This isn't a prompt — it's architecture-level tenant isolation enforced by the gateway.

**Compliance out of the box.** Full audit trail of every AI interaction, model call, and tool use. SOC-2 aligned controls. HIPAA and GDPR policy enforcement. For gaming clients subject to GLI standards and government clients subject to municipal audit requirements, this matters.

**Cost visibility.** Bulletproof sees exactly what each agent costs per client, per month, per ticket category. No surprise bills. Budget caps that actually stop spend, not just alert.

**Human-in-the-loop.** Approval queues for sensitive actions are built into the agent runtime — not bolted on. Risk assessment, auto-approve conditions for low-risk actions, timeout handling, and full audit trails.

**They don't have to maintain it.** Bonito handles model updates, security patches, scaling, and uptime. Bulletproof's engineers configure agents and manage KBs — they don't operate infrastructure.

---

## Simulation Plan

Before contract signing, we propose building a working simulation:

1. **Bulletproof provides** sample runbooks/SOPs for 2–3 clients (anonymized is fine)
2. **Bonito builds** a live agent configured with those KBs
3. **Bulletproof's team tests it** — submit real ticket scenarios and see how the agent responds
4. **We measure** accuracy, response quality, escalation appropriateness
5. **Chris and team evaluate** whether this is worth deploying to production

No commitment required. The simulation runs on Bonito's infrastructure at our cost. If it doesn't meet the bar, we part as friends.

---

## Next Step

We'll build the simulation as soon as Bulletproof shares sample runbooks for 2–3 client environments. Christopher and team can interact with the agent live — no slides, no demos, just the real thing handling real ticket scenarios.

**Contact:** shabari@bonito.ai | https://getbonito.com
