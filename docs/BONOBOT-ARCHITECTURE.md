# Bonobot — Architecture Analysis & Build Plan

*What to take from OpenClaw, what to build new, and how to make it enterprise-grade.*

---

## OpenClaw Architecture — What Matters

After reviewing OpenClaw's docs and codebase, here are the key architectural pieces:

### The Good (What We Should Learn From)

**1. Gateway as Control Plane**
- Single long-lived process that owns all messaging surfaces
- WebSocket API for all clients (apps, CLI, web UI, nodes)
- Typed protocol with JSON Schema validation
- Session serialization (one run at a time per session = no race conditions)

**2. Agent Loop (the core)**
- `intake → context assembly → model inference → tool execution → streaming replies → persistence`
- Queueing + concurrency control per session
- Hook points throughout: `before_model_resolve`, `before_prompt_build`, `before_tool_call`, `after_tool_call`, `agent_end`
- Plugin system for extending behavior

**3. Multi-Agent Routing**
- Each agent is fully isolated: own workspace, own state dir, own sessions, own auth profiles
- Bindings route inbound messages to specific agents (by channel, peer, group, etc.)
- Most-specific match wins — deterministic routing
- Multiple agents share one Gateway process

**4. Memory System**
- Markdown files as source of truth (MEMORY.md + daily logs)
- Vector search over memory (embeddings + sqlite-vec)
- Pre-compaction memory flush (save durable memories before context gets trimmed)
- Compaction for long sessions (summarize → trim)

**5. Sandboxing**
- Docker containers for tool execution (optional)
- Scope: per-session, per-agent, or shared
- Workspace access: none, read-only, or read-write
- Blocks dangerous bind sources (docker.sock, /etc, /proc)

**6. Tool Policy System**
- Profiles: minimal, coding, messaging, full
- Allow/deny lists with group shorthands (`group:fs`, `group:runtime`, `group:messaging`)
- Per-provider tool restrictions (different tools for different models)
- Per-agent overrides

### The Gaps (What OpenClaw Doesn't Do for Enterprise)

| Gap | Why It Matters for Enterprise |
|-----|------|
| **Single-user design** | One person runs it on their machine. No multi-tenant. No org hierarchy. |
| **No centralized knowledge** | Memory is per-agent markdown files. No shared RAG across agents. |
| **No cost controls** | Uses your API keys directly. No budget caps, no per-agent cost tracking. |
| **No compliance/audit** | Audit trail is log files. No structured compliance reporting. |
| **No model governance** | Any agent can use any model. No approval workflows. |
| **Trust model is local** | "Runs on your machine" = trusted. Enterprise needs zero-trust per-agent. |
| **No centralized admin** | Each agent is independently configured. No fleet management. |

---

## Bonobot Architecture — What We Build

### Core Principle: Enterprise-First, Security-First

Unlike OpenClaw (personal-first, add security later), Bonobot is:
- **Multi-tenant from day one** — org → project → agent hierarchy
- **Zero-trust per agent** — each Bonobot has explicit permissions, nothing implicit
- **Audited by default** — every action, every model call, every tool use is logged and attributable
- **Bonito is the control plane** — all model access goes through Bonito's gateway (cost tracking, routing, policies)

### Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                    BONITO CONTROL PLANE (existing)                  │
│                                                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Gateway  │  │ AI       │  │ Cost     │  │ Compliance       │  │
│  │ Router   │  │ Context  │  │ Tracker  │  │ Engine           │  │
│  │ (LiteLLM)│  │ (RAG)    │  │          │  │                  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
│       │              │             │                  │            │
│  ─────┴──────────────┴─────────────┴──────────────────┴────────── │
│                     BONITO API LAYER                               │
│  ─────┬──────────────┬─────────────┬──────────────────┬────────── │
│       │              │             │                  │            │
│  ┌────┴─────────────────────────────────────────────────────────┐ │
│  │                   BONOBOT RUNTIME (new)                       │ │
│  │                                                               │ │
│  │  ┌─────────────────────────────────────────────────────────┐ │ │
│  │  │ Project Manager                                         │ │ │
│  │  │  • Creates/destroys agent instances per project         │ │ │
│  │  │  • Enforces project-level budgets and policies          │ │ │
│  │  │  • Routes messages to correct project agent             │ │ │
│  │  └─────────────────────────────────────────────────────────┘ │ │
│  │                                                               │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │ │
│  │  │ Bonobot  │  │ Bonobot  │  │ Bonobot  │  ...              │ │
│  │  │ Agent 1  │  │ Agent 2  │  │ Agent 3  │                   │ │
│  │  │          │  │          │  │          │                   │ │
│  │  │ Project: │  │ Project: │  │ Project: │                   │ │
│  │  │ Ad Tech  │  │ Support  │  │ Legal    │                   │ │
│  │  │          │  │          │  │          │                   │ │
│  │  │ 🧠 Scoped│  │ 🧠 Scoped│  │ 🧠 Scoped│                   │ │
│  │  │ Context  │  │ Context  │  │ Context  │                   │ │
│  │  │          │  │          │  │          │                   │ │
│  │  │ 🔧 Scoped│  │ 🔧 Scoped│  │ 🔧 Scoped│                   │ │
│  │  │ Tools    │  │ Tools    │  │ Tools    │                   │ │
│  │  │          │  │          │  │          │                   │ │
│  │  │ 💬 Slack │  │ 💬 Teams │  │ 💬 Email │                   │ │
│  │  └──────────┘  └──────────┘  └──────────┘                   │ │
│  │                                                               │ │
│  │  ┌─────────────────────────────────────────────────────────┐ │ │
│  │  │ Sandbox Runtime (Docker/WASM)                           │ │ │
│  │  │  • Each agent runs in isolated container                │ │ │
│  │  │  • No cross-agent filesystem access                     │ │ │
│  │  │  • Network egress controlled per project policy         │ │ │
│  │  └─────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

### What We Take From OpenClaw (Concepts, Not Code)

| OpenClaw Concept | Bonobot Implementation |
|---|---|
| **Agent loop** (intake → inference → tools → reply) | Same pattern, but all model calls go through Bonito's gateway (cost-tracked, policy-enforced) |
| **Multi-agent routing** (bindings) | Project-based routing — messages from Slack #ad-tech → Ad Tech Bonobot |
| **Workspace isolation** (per-agent dirs) | Per-project workspace in sandboxed container. No shared filesystem. |
| **Memory** (MEMORY.md + daily logs + vector search) | Same pattern, but memory stored in Bonito's DB (not flat files). Searchable via AI Context. |
| **Tool policies** (profiles + allow/deny + groups) | Hardened version: admin defines tool policy per project. Agent cannot escalate. |
| **Sandboxing** (Docker containers) | Mandatory, not optional. Per-agent container with network policies. |
| **Hook system** (before/after tool calls) | Used for compliance: log every tool call, enforce approval workflows for sensitive actions |
| **Compaction** (context management) | Same, but compaction summaries stored for audit trail |
| **Session management** (serialized runs) | Same, but sessions tied to Bonito user identity and org RBAC |

### What We Build New (Enterprise-Only)

**1. Project System**
```
Organization
  └── Project (e.g., "Ad Tech")
        ├── Bonobot Agent (one per project)
        ├── AI Context scope (which KBs this agent can access)
        ├── Model allowlist (which models this agent can use)
        ├── Tool policy (what this agent can do)
        ├── Budget (monthly spend cap)
        ├── Channel bindings (Slack channels, Teams channels, etc.)
        └── Team members (who can interact with this Bonobot)
```

**2. Security Model — Zero Trust Per Agent**

| Layer | Control |
|---|---|
| **Model access** | Agent can only use models explicitly allowed by project admin. Routes through Bonito gateway. |
| **Knowledge access** | Agent can only query AI Context KBs assigned to its project. Cross-project KB access requires explicit sharing. |
| **Tool access** | Admin defines tool policy per project. Default: messaging-only. Filesystem/exec require explicit approval. |
| **Network** | Sandboxed container with egress rules. Agent cannot call arbitrary APIs unless allowlisted. |
| **Data isolation** | Per-agent workspace in isolated container. No cross-agent filesystem. Memory stored in project-scoped DB tables. |
| **Action audit** | Every model call, tool use, and message is logged with user identity, project, timestamp. Exportable for compliance. |
| **Budget enforcement** | Per-project spend cap. Agent is throttled/stopped when budget is exceeded. Alerts to project admin. |
| **Approval workflows** | Sensitive actions (e.g., sending emails, modifying data) require human approval before execution. |

**3. Enterprise Channel Integration**
- Slack: per-channel bindings (Slack app installed in workspace, specific channels → specific Bonobots)
- Microsoft Teams: same pattern via Teams bot framework
- Email: dedicated inbox per Bonobot (support@company.com → Support Bonobot)
- Internal web chat: embedded widget in company tools
- API: direct integration for programmatic access

**4. Admin Dashboard (in Bonito UI)**
- Create/manage projects and Bonobots
- Configure tool policies, model allowlists, KB access per project
- View per-project cost analytics
- Audit log viewer with filtering
- Health monitoring per agent

---

## Build Phases

### Phase 1: Projects + Scoped AI Context (Weeks 1-4)
- Add "Projects" to Bonito data model (org → project → resources)
- Scope AI Context (KBs) per project
- Scope gateway keys per project
- Project-level cost tracking and budgets
- Admin UI for project management
- **No agent yet** — just the organizational layer

### Phase 2: Bonobot Agent Runtime (Weeks 5-10)
- Agent loop: message → context assembly → Bonito gateway → tool execution → reply
- Session management with compaction
- Memory system (project-scoped, stored in DB, vector-searchable)
- Tool policy engine (allow/deny per project)
- Sandboxed execution (Docker containers per agent)
- Slack integration as first channel

### Phase 3: Enterprise Hardening (Weeks 11-14)
- Approval workflows for sensitive actions
- Full audit trail with export
- Network egress policies per agent
- SSO/SAML integration (agent access tied to identity)
- Rate limiting and abuse detection
- Microsoft Teams integration

### Phase 4: Agent Marketplace (Weeks 15-20)
- Pre-built agent templates (Support Bot, Compliance Bot, Analytics Bot)
- Custom tool development SDK
- Agent-to-agent communication (within same org, with permission)
- Workflow builder (multi-step tasks with approval gates)

---

## Technical Decisions

### Build vs Integrate

| Component | Decision | Rationale |
|---|---|---|
| **Agent loop** | Build | Core IP. Must be Bonito-native, security-first. OpenClaw's loop is personal-first. |
| **Tool execution** | Build | Must go through Bonito's security layer. No direct host access. |
| **Model routing** | Existing | Bonito's gateway + LiteLLM already handles this perfectly |
| **RAG/Knowledge** | Existing | AI Context (pgvector) already built and working |
| **Sandboxing** | Build (inspired by OpenClaw) | Docker-based, but mandatory and with network policies |
| **Memory** | Build (inspired by OpenClaw) | Same markdown concept but DB-backed for multi-tenant |
| **Channel integration** | Build | Enterprise channels (Slack apps, Teams bots) are different from personal messaging |
| **Session management** | Build (inspired by OpenClaw) | Same serialization concept but with RBAC and audit |

### Language Choice: Python (FastAPI)

Why: Bonito backend is already Python/FastAPI. Adding the agent runtime in the same stack means:
- Shared DB models, auth, and middleware
- AI Context (RAG) accessible directly
- Gateway routing reusable
- One deployment, one codebase
- Python has the best AI/ML library ecosystem

---

## The Moat

1. **AI Context is shared across all Bonobots** — one KB, all agents can access it (with permission). No competitor has cross-agent shared knowledge.
2. **Bonito gateway tracks every token** — cost per agent, per project, per query. Budget enforcement is automatic.
3. **Security is structural, not bolted on** — zero-trust per agent, sandboxed execution, approval workflows. Enterprise can deploy with confidence.
4. **Same control plane for models AND agents** — competitors sell routing OR agents. Bonito sells both on one platform.

---

*This is the blueprint. Phase 1 (Projects) can start immediately since it's just extending the existing Bonito data model. The agent runtime (Phase 2) is the real engineering lift.*
