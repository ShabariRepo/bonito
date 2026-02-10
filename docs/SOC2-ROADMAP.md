# SOC-2 Type II Certification Roadmap

This document outlines Bonito's path to SOC-2 Type II certification, including current readiness, gaps, timeline, and cost estimates.

## What is SOC-2?

SOC-2 (Service Organization Control 2) is an auditing standard developed by the AICPA that evaluates a service organization's controls relevant to security, availability, processing integrity, confidentiality, and privacy. It's the de facto compliance requirement for B2B SaaS selling to enterprises.

- **Type I** — Point-in-time assessment: do the controls exist?
- **Type II** — Assessment over a period (typically 3–12 months): are the controls operating effectively over time?

Most enterprise buyers require **Type II**.

## Trust Service Criteria (TSC)

SOC-2 evaluates five Trust Service Criteria. Not all are required — Security is mandatory; the rest are selected based on what's relevant to the service.

### 1. Security (Required — Common Criteria)
Protection against unauthorized access, both physical and logical.
- Access controls, firewalls, intrusion detection
- Encryption in transit and at rest
- Vulnerability management, penetration testing
- Incident response procedures

### 2. Availability
System is available for operation and use as committed.
- Uptime monitoring and SLAs
- Disaster recovery and business continuity plans
- Capacity planning
- Backup and restore procedures

### 3. Processing Integrity
System processing is complete, valid, accurate, and timely.
- Data validation and error handling
- Quality assurance processes
- Monitoring for processing anomalies

### 4. Confidentiality
Information designated as confidential is protected as committed.
- Data classification policies
- Encryption of confidential data
- Access restrictions based on classification
- Secure data disposal

### 5. Privacy
Personal information is collected, used, retained, and disclosed in conformity with commitments.
- Privacy policy and notice
- Consent mechanisms
- Data subject rights (access, deletion, portability)
- Data retention and disposal policies

**Recommended for Bonito:** Security + Availability + Confidentiality. These are the most relevant for an AI operations platform handling cloud credentials and API traffic. Privacy can be added later if handling PII becomes a core use case.

## Current State Assessment

### What Bonito Already Has ✅

| Control Area | Current State |
|---|---|
| **Authentication** | JWT-based auth with refresh tokens, password hashing (bcrypt) |
| **Authorization** | Role-based access control (RBAC) with team/org scoping |
| **Audit logging** | Comprehensive audit trail for all user and system actions |
| **Encryption in transit** | TLS/HTTPS enforced on all endpoints |
| **Encryption at rest** | PostgreSQL with encrypted volumes (cloud deployment) |
| **Secrets management** | HashiCorp Vault (production), SOPS + age (development) |
| **Rate limiting** | API rate limiting per user/endpoint |
| **Input validation** | Pydantic schema validation on all API inputs |
| **Dependency scanning** | (Partial) — needs formalization |
| **Infrastructure as Code** | Docker Compose, deployment configs |
| **Monitoring** | Basic health checks and error tracking |

### What's Missing ❌

| Control Area | Gap | Priority |
|---|---|---|
| **Formal security policies** | No written Information Security Policy, Acceptable Use Policy, or Data Classification Policy | 🔴 Critical |
| **Vendor management** | No formal vendor assessment process for third-party services (AWS, Azure, GCP, Groq, etc.) | 🔴 Critical |
| **Incident response plan** | No documented IR plan, escalation procedures, or post-mortem process | 🔴 Critical |
| **Change management** | No formal change management process (PR reviews exist but aren't documented as a control) | 🟡 High |
| **Business continuity / DR** | No documented BCP or disaster recovery plan; no tested backup/restore | 🟡 High |
| **Employee security training** | No security awareness training program | 🟡 High |
| **Background checks** | No formal background check process for employees/contractors | 🟡 High |
| **Vulnerability management** | No regular penetration testing or vulnerability scanning schedule | 🟡 High |
| **Asset inventory** | No formal inventory of systems, data stores, and third-party services | 🟠 Medium |
| **Risk assessment** | No formal risk assessment process | 🟠 Medium |
| **Access reviews** | No periodic access review process (who has access to what, and is it still needed?) | 🟠 Medium |
| **Endpoint security** | No MDM or endpoint protection requirements for team devices | 🟠 Medium |
| **Data retention policy** | No formal data retention and disposal policy | 🟠 Medium |
| **Board/management oversight** | No documented management review of security program | 🟢 Lower |

## Recommended Timeline

### Phase 1: Foundation (Months 1–2)
- [ ] Select and deploy compliance automation platform (Vanta, Drata, or Secureframe)
- [ ] Write core policies:
  - Information Security Policy
  - Acceptable Use Policy
  - Data Classification Policy
  - Incident Response Plan
  - Change Management Policy
  - Business Continuity / Disaster Recovery Plan
  - Vendor Management Policy
  - Data Retention Policy
  - Access Control Policy
- [ ] Conduct initial risk assessment
- [ ] Build asset inventory
- [ ] Set up employee security training (KnowBe4, Curricula, or built-in via compliance platform)

### Phase 2: Implementation (Months 3–4)
- [ ] Implement automated evidence collection (connect AWS/GCP/Azure, GitHub, HR tools to compliance platform)
- [ ] Set up vulnerability scanning (Snyk, Dependabot, or similar)
- [ ] Schedule first penetration test
- [ ] Implement access review process (quarterly)
- [ ] Document and formalize change management (link to GitHub PR workflow)
- [ ] Set up endpoint security requirements
- [ ] Implement background check process for new hires
- [ ] Configure monitoring and alerting for security events

### Phase 3: Observation Period Begins (Months 5–6)
- [ ] Engage SOC-2 auditor
- [ ] Begin Type II observation period (minimum 3 months, 6 months preferred)
- [ ] Run first incident response tabletop exercise
- [ ] Conduct first formal management review
- [ ] Perform first quarterly access review

### Phase 4: Audit (Months 8–12)
- [ ] Auditor reviews evidence and controls over the observation period
- [ ] Address any findings or exceptions
- [ ] Receive SOC-2 Type II report
- [ ] Share report with customers (under NDA or via trust page)

**Total timeline: 9–12 months** from kickoff to report in hand.

## Compliance Automation Platforms

These tools automate evidence collection, policy management, and auditor communication. Essential for a small team.

| Platform | Starting Price | Strengths | Notes |
|---|---|---|---|
| **Vanta** | ~$10K–15K/year | Market leader, most integrations, auditor network | Best overall for startups |
| **Drata** | ~$10K–12K/year | Strong automation, good UI, competitive pricing | Good alternative to Vanta |
| **Secureframe** | ~$8K–12K/year | Fast onboarding, good for small teams | Slightly less mature ecosystem |

**Recommendation:** Vanta or Drata. Both have strong integration with AWS, GCP, Azure, GitHub, and common SaaS tools. Choose based on pricing negotiation and which integrations matter most.

## Auditors

| Auditor | Type | Notes |
|---|---|---|
| **Johanson Group** | CPA firm | Popular with startups, reasonable pricing, fast turnaround |
| **Schellman** | CPA firm | Larger firm, strong reputation, more enterprise-focused |
| **Prescient Assurance** | CPA firm | Startup-friendly, competitive pricing |
| **BARR Advisory** | CPA firm | Mid-market, good reputation |

**Recommendation:** Johanson Group for first audit — experienced with startup-stage companies, reasonable pricing, and fast process.

## Cost Estimates

| Item | Estimated Cost | Frequency |
|---|---|---|
| Compliance platform (Vanta/Drata) | $10,000–15,000 | Annual |
| SOC-2 Type II audit | $15,000–30,000 | Annual |
| Penetration test | $5,000–15,000 | Annual (minimum) |
| Security training platform | $1,000–3,000 | Annual |
| **Total Year 1** | **$31,000–63,000** | — |
| **Total Year 2+** | **$26,000–48,000** | — |

Year 1 is higher due to setup costs and potentially longer audit scope. Subsequent years are renewal + audit.

## Key Decisions Needed

1. **Which TSC to include?** Recommendation: Security + Availability + Confidentiality
2. **Which compliance platform?** Recommendation: Vanta (negotiate pricing — they discount heavily for early-stage)
3. **Which auditor?** Recommendation: Johanson Group
4. **When to start?** The observation period is the bottleneck. Starting sooner means having the report sooner for sales conversations.
5. **Who owns this internally?** Needs a single DRI (Directly Responsible Individual) — likely a senior engineer or head of engineering until a dedicated security hire.

## Resources

- [AICPA SOC-2 Overview](https://www.aicpa.org/topic/audit-assurance/audit-and-assurance-greater-than-soc-2)
- [Vanta SOC-2 Guide](https://www.vanta.com/collection/soc-2)
- [Drata SOC-2 Guide](https://drata.com/blog/soc-2-compliance)

---

*Document created February 2026. Review quarterly as progress is made.*
