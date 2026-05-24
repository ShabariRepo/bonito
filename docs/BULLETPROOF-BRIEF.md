# Bonito AI — Brief for Bulletproof

Hi Chris,

Great speaking with you. Here's a quick overview of how Bonito fits into what Bulletproof is doing and the three models we discussed.

---

## What Bonito Is

Bonito is a unified AI control plane. One platform to connect, govern, route, and manage AI workloads across cloud providers — AWS, Azure, Google, OpenAI, Anthropic, and more. It gives organizations a single API endpoint, unified cost tracking, compliance controls, and a built-in framework for deploying autonomous AI agents.

---

## How It Fits Bulletproof

### 1. Tier 1 Support Agents

Your team handles Tier 1 support across 300+ client environments. Bonito can power AI agents that act as the first line of response — resolving common tickets (password resets, connectivity, basic troubleshooting) and intelligently escalating everything else with full context.

**How it works:**
- You provide client runbooks, SOPs, and KB articles
- We ingest them into isolated Knowledge Bases on Bonito — per client or client group
- We configure AI agents scoped to each environment with the right docs, approved models, and escalation rules
- Agents integrate into your existing ticketing workflow via API or embedded widget
- Every interaction is logged with a full audit trail — critical for your government and gaming clients

**What you keep control of:**
- Which models the agents can use
- Budget caps per agent, per client
- Human approval gates on sensitive actions
- Complete visibility into what the agent is doing and what it costs

### 2. White-Label Managed AI

You already sell managed IT and managed security. Bonito can be white-labeled under Bulletproof's brand as a managed AI offering to your clients.

Your clients get governed AI access — gateway, agents, knowledge base, compliance — without building anything themselves. You manage it as an extension of your existing service. Your pricing, your margins.

This is especially relevant for your gaming and government clients who can't adopt AI without proper governance and audit controls in place.

### 3. Referral Partnership

The simplest model. When your clients ask about AI — and they will — you point them to Bonito. We handle the sale and onboarding, you earn a referral fee on every deal.

Zero engineering lift. Monetizes conversations you're already having.

---

## Connecting Your Dev Team

Your engineers already use Claude Code. Connecting to Bonito takes two environment variables:

```
ANTHROPIC_BASE_URL=https://api.getbonito.com/v1
ANTHROPIC_API_KEY=bn-your-key-here
```

Every request then routes through Bonito — you get cost tracking by engineer, audit logs, model policies, and budget controls across the team. If Anthropic goes down, Bonito automatically reroutes to an equivalent model on another provider.

---

## Your Stack (Confirmed)

- **SIEM:** Microsoft Sentinel — primary alert source, investigation, playbooks
- **ITSM:** Halo ITSM — ticket management, closure synced from Sentinel
- **Workflow:** Tier 1 analysts investigate Sentinel alerts, follow internal playbooks, remediate, close in Halo

Bonito agents can sit between Sentinel and Halo — ingesting alerts, running playbook-driven investigation at machine speed, auto-resolving false positives, and escalating real threats with full context already attached. Your analysts pick up mid-investigation instead of starting from scratch.

## What We'd Need to Get Started

- Sample security playbooks / SOPs for 2–3 client environments (anonymized is fine)
- A walkthrough of your Sentinel → Halo workflow so we can plan the integration
- Any compliance requirements specific to your government or gaming clients
- Tooling list for the Tier 1 security stack (Chris is prepping this)

We'll build a pilot agent you can interact with live before any commitment.

---

Looking forward to the next conversation.

**Shabari**
Bonito AI
https://getbonito.com
shabari@bonito.ai
