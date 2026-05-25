# Bulletproof — Internal Brief

**Last updated:** 2026-05-24
**Deal owner:** Shabari
**Contact:** Christopher Simm (CTO)
**Company:** Bulletproof ($81M revenue, 262 employees, 300+ client sites)
**Timeline:** Dev team demo mid-June 2026

---

## Silver Bullet Demo — Proven on Prod

We built and ran "Silver Bullet" — a full end-to-end Tier 1 support automation demo on Bonito prod. 5 agents, 5 knowledge bases, 10 realistic tickets across Bulletproof's verticals (gaming, government, healthcare, finance, startups, real estate).

### Results

| Metric | Value |
|--------|-------|
| Tickets processed | 10 |
| Routing accuracy | **10/10 (100%)** |
| Total time | 4 min 14 sec |
| Total cost | **$0.0088** |
| Cost per ticket | ~$0.0009 |
| Model | gpt-4o-mini (all agents) |
| Infrastructure | 100% Bonito prod (api.getbonito.com) |

### Cost at Scale

| Volume | AI Cost | Notes |
|--------|---------|-------|
| 10 tickets | $0.009 | Demo run |
| 500 tickets | **$0.45** | Daily volume estimate |
| 5,000 tickets | $4.50 | Weekly volume |
| 50,000 tickets/mo | **$45/mo** | Bulletproof's actual monthly volume |

**Context:** A single Tier 1 support analyst costs $45K-55K/yr (~$4,000/mo). The AI cost to triage and resolve 50K tickets is roughly **1% of one analyst's salary**.

### Architecture

```
Ticket → Triage Router (gpt-4o-mini)
           ├── invoke_agent → Password Specialist (KB: password-procedures)
           ├── invoke_agent → Connectivity Specialist (KB: vpn-procedures)
           ├── invoke_agent → Software Specialist (KB: approved-software)
           ├── invoke_agent → General Support (KB: client-directory)
           └── ESCALATE → Human (security incidents, org-wide outages)
```

All agent-to-agent delegation uses Bonito's native `invoke_agent` tool — no external orchestration. Breadcrumbs shows the full delegation chain in the dashboard.

### What the Demo Proves

1. **Multi-agent delegation works** — Triage Router classifies and routes to the right specialist via invoke_agent
2. **KB-powered resolution** — Specialists search per-client knowledge bases (password procedures, VPN troubleshooting, approved software lists) and generate contextual responses
3. **Smart escalation** — Security incidents (Sentinel alerts) and org-wide outages correctly bypass delegation and escalate to human
4. **Cost efficiency** — gpt-4o-mini handles Tier 1 classification + resolution without needing frontier models
5. **Compliance-aware** — Agents recognize PHIPA, PCI-DSS, MFIPPA, GLI compliance requirements per client

### Ticket Breakdown

| ID | Type | Client | Routed To | Time |
|----|------|--------|-----------|------|
| BP-001 | Password reset + MFA | GamingCo | Password Specialist | 25.7s |
| BP-002 | Account lockout | Maple Ridge (Gov) | Password Specialist | 22.3s |
| BP-003 | MFA broken (urgent, doctor) | Northern Health | Password Specialist | 35.4s |
| BP-004 | VPN error 443 | Apex Financial | Connectivity Specialist | 48.4s |
| BP-005 | New employee VPN setup | TechStart | Connectivity Specialist | 45.1s |
| BP-006 | Adobe CC install | GamingCo | Software Specialist | 15.7s |
| BP-007 | Dropbox request (denied - GLI) | GamingCo | Software Specialist | 19.7s |
| BP-008 | Laptop screen flickering | Pinnacle Properties | General Support | 25.1s |
| BP-009 | Sentinel: suspicious login Nigeria | Maple Ridge | ESCALATION | 4.5s |
| BP-010 | CEO: email down org-wide | Apex Financial | ESCALATION | 3.9s |

---

## Deal Economics

### Bulletproof's Profile
- 300+ managed client sites
- ~50K support tickets/month
- Verticals: gaming (GLI compliance), government (MFIPPA), healthcare (PHIPA/HIPAA), finance (SOC 2/PCI-DSS)
- Stack: Microsoft Sentinel (SIEM) + Halo ITSM
- Dev team uses Claude Code already

### Revenue Scenarios

| Tier | Monthly | Annual | What They Get |
|------|---------|--------|---------------|
| Pro | $999 | ~$12K | 5 agents, 500K requests, RAG, analytics |
| Enterprise | $10K-$20K | $120K-$240K | SSO, RBAC, compliance, SLA, unlimited agents |

**Most likely path:** Enterprise tier ($10K-20K/mo) because of compliance requirements (gaming + government + healthcare clients). They need audit trails, RBAC, and per-client isolation.

### White-Label Upside
Bulletproof can resell Bonito as "Managed AI" to their 300+ clients. Their pricing, their margins. This turns Bulletproof from a customer into a distribution channel.

---

## Demo Repo

- **GitHub:** https://github.com/ShabariRepo/bulletproof-demo
- **Bonito project:** Silver Bullet (`b0bcd4b2-c667-4b98-8edb-48924d364e74`)
- **Org:** tradesauceofficial@gmail.com

### Running the Demo
```bash
cd bulletproof-demo
python -m src.run_demo              # All 10 tickets
python -m src.run_demo --ticket BP-004  # Single ticket
```

### Provisioned Resources (Bonito Prod)
- Triage Router: `98c6d000-6bc1-4346-b10e-cf5b190cfd34`
- Password Specialist: `6638b048-78be-45f4-8248-03654be24369`
- Connectivity Specialist: `c11dd9b7-9557-4ca9-ac1c-fc5c704a46f0`
- Software Specialist: `fa814ced-c621-4716-a062-4d2b43617327`
- General Support: `253d8fe7-2af7-42f8-888d-c10e26dfaf33`

---

## Next Steps

1. **Mid-June:** Demo to Christopher Simm's dev team — run Silver Bullet live, show Breadcrumbs, show cost cards
2. **Integration scoping:** Get sample Sentinel playbooks + Halo API access for real integration
3. **Pilot proposal:** 2-3 client environments, real tickets, 30-day trial on Enterprise tier
4. **White-label conversation:** Separate track — Bulletproof as Bonito distribution partner
