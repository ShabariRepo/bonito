"use client";

import { motion } from "framer-motion";
import { Zap, Cloud, DollarSign, Shield, BarChart3, Bot, Rocket, Lock, Route, Bell, Terminal, KeyRound, Image, Video, Activity, Database, Layers, Sparkles, AlertTriangle, Workflow, Stamp, MessageSquare } from "lucide-react";

const entries = [
  {
    date: "May 2026",
    items: [
      { icon: Stamp, title: "Custom error pages (5/30)", desc: "Branded 404, 403, 500, 503, and global error pages with Bonito fish theme, Framer Motion animations, and contextual messaging. 503 includes 60s auto-retry countdown." },
      { icon: DollarSign, title: "Starter tier — $199/mo (5/28)", desc: "New tier between Free and Pro: 3 providers, 100K req/mo, 5 seats, 2 agents, RAG (2 KBs), analytics, audit trail, CLI, email support. Designed for teams that want to swipe a card without procurement approval." },
      { icon: KeyRound, title: "Personal Access Tokens + Project Tokens (5/27)", desc: "Three token types now live: gateway keys (bn-), personal access tokens (bp-) carrying user permissions across all endpoints, and project tokens (bj-) scoped to a single project (Pro+, admin-only). Per-tier caps enforced at create time." },
      { icon: Shield, title: "Per-org log retention by tier (5/27)", desc: "Retention runs per-org: Free=30d, Pro=60d, Enterprise/Scale=90d. Settings UI shows tier-appropriate options with locked indicators for higher tiers." },
      { icon: Database, title: "GCS log sink org-partitioned (5/27)", desc: "Restructured to {org_id}/{log_type}/{YYYY}/{MM}/{DD}/{HH}.ndjson across 10 log types (gateway, agent, auth, kb, admin, deployment, billing, compliance, approval, system). Per-org GCS lifecycle rules for tier-based retention." },
      { icon: Sparkles, title: "UX onboarding improvements (5/27)", desc: "Settings page shows subscription tier badge. Sidebar nav items requiring a higher tier show Pro/Ent badges. KB cards show pending-state guidance. /api/auth/me returns subscription_tier." },
      { icon: BarChart3, title: "Token efficiency metrics on Gateway dashboard (5/26)", desc: "Cost-per-1K-tokens at three levels: overall stat card, per-model in breakdown, and per-request in the logs table. Side-by-side model cost-effectiveness comparison across providers." },
      { icon: Workflow, title: "Overflow Queue for agents (5/25)", desc: "Redis-backed FIFO queue per agent. When RPM ceilings are hit, requests are queued not dropped — 202 Accepted with ticket_id and poll_url. Background drainer (2s interval) retries as capacity frees up. Max depth 500, result TTL 1h." },
      { icon: Activity, title: "Agent HPA — Phase 1 (5/25)", desc: "Elastic agent capacity. Virtual mode doubles effective RPM in Redis when utilization crosses threshold (default 60%). Scale-down via background loop (30s). Configurable via API, CLI, and bonito.yaml scaling block. Enterprise+ only." },
      { icon: Database, title: "KB vector dimension upgrade — 768 → 1024 (5/25)", desc: "Pgvector column migrated from vector(768) to vector(1024) to match Titan Embed V2 native dimensions. Migration NULLs existing embeddings, alters the column, and backfills KBs to embedding_dimensions=1024." },
      { icon: AlertTriangle, title: "Production reliability — 6 fixes (5/25)", desc: "Pgvector greenlet_spawn fix (codec registration moved to checkout event). KB delete cascade fix (raw SQL bypasses ORM ARRAY/vector coercion). Alembic multiple-heads merge after branched migration. Ingestion error handler rollback. GCS fast-fail on missing credentials. Embedding timeout raised 30s → 90s." },
      { icon: MessageSquare, title: "KB search quality (5/24)", desc: "Tool-search threshold lowered from 0.7 to 0.5 to match RAG injection. Added MODEL_MAX_DIMENSIONS map to clamp requested embedding dimensions to model max — fixes silent ingestion failures with GCP text-embedding-005 (768 max) at KB default 1024." },
      { icon: Lock, title: "Gateway Vault fallback (5/24)", desc: "_get_provider_credentials() now uses Vault → encrypted DB fallback chain across all provider lookups. No more single-point-of-failure on Vault availability." },
      { icon: Bot, title: "External orchestration / Breadcrumbs tracing (5/23)", desc: "POST /api/agents/{id}/execute accepts optional parent_agent_id. When set, a synthetic invoke_agent delegation record is logged in the parent's session, so code-orchestrated pipelines appear in Breadcrumbs with zero latency impact. CLI flag: --parent-agent." },
      { icon: Activity, title: "Agent Health dashboard (5/23)", desc: "Platform admin page at /admin/agent-health cross-references agent model_ids against available provider models to detect deprecated or unroutable models. Background check runs after every 24h model sync. Per-agent health badges: Healthy, Deprecated, No Route, Warning." },
      { icon: Route, title: "Gateway duplicate-provider fix (5/23)", desc: "_get_provider_credentials() now keys by provider UUID instead of provider_type — fixes silent credential overwrites when orgs have multiple providers of the same type. All provider CRUD endpoints now call reset_router() for immediate cache invalidation instead of waiting 50min TTL." },
      { icon: Image, title: "Image generation endpoint (5/20)", desc: "POST /v1/images/generations live across dall-e-3, dall-e-2, gpt-image-1. Same bn- key as chat. Powers creative-asset workflows: brand-asset pipelines, marketing visuals, campaign generation." },
      { icon: Video, title: "Video generation endpoints (5/20)", desc: "POST /v1/videos (submit), GET /v1/videos/{id} (status), GET /v1/videos/{id}/content (download) across OpenAI Sora-2 and Vertex AI Veo 2.0/3.0/3.1. Credentials injected from Vault/DB. Per-second cost tracking." },
      { icon: Shield, title: "Sentry tracking — backend + frontend (5/12)", desc: "sentry-sdk[fastapi] initializes before FastAPI app with environment-aware sampling (20% prod, 100% dev). @sentry/nextjs SDK with client/server/edge configs, instrumentation hook, global error boundary, and source-map upload via withSentryConfig." },
      { icon: Lock, title: "API schema hardening — extra=\"forbid\" (5/12)", desc: "All Bonobot create/update schemas now reject unknown fields with 422 instead of silently dropping them. Covers AgentCreate, AgentUpdate, AgentConnectionCreate, AgentGroupCreate/Update, AgentExecuteRequest, AgentScheduleCreate/Update." },
      { icon: Cloud, title: "All 6 providers connectable via UI (5/06)", desc: "Connect modal + onboarding wizard fixed for all 6 providers (OpenAI, Anthropic, AWS Bedrock, Google Vertex AI, Azure AI, Groq). Anthropic validation uses /v1/models instead of hardcoded model. Connect modal uses apiRequest() for JWT auth." },
      { icon: Sparkles, title: "Background model sync — 24h (5/06)", desc: "model_sync.py runs every 24h and syncs models for all active providers. Anthropic now uses live API with static pricing fallback. Wired into FastAPI lifespan." },
      { icon: Lock, title: "Credential storage fix (5/06)", desc: "Legacy POST/PATCH /api/providers endpoints now encrypt credentials at write time (were storing plain JSON). DB fallback auto-migrates plain JSON → AES-256-GCM on read. Bedrock _check_model_access fixed to use real API." },
      { icon: Shield, title: "Admin access requests UI (5/06)", desc: "Admin page at /admin/access-requests for invite-only registration approval. Submit → admin approve → invite code → register flow, rate-limited at 5 req/60s." },
    ],
  },
  {
    date: "March–April 2026",
    items: [
      { icon: Bot, title: "Bonobot agent framework", desc: "Enterprise agent framework with visual canvas (React Flow), project-based organization, built-in tools (KB search, HTTP, agent-to-agent), and enterprise security: default-deny tool policy, budget stops, rate limiting, SSRF protection, full audit trail." },
      { icon: Database, title: "RAG knowledge bases on pgvector HNSW", desc: "Cross-cloud RAG pipeline: upload/parse/chunk/embed docs, pgvector HNSW search, gateway context injection on chat completions, source citations on every response." },
      { icon: Layers, title: "VectorBoost — KB compression", desc: "3.9-8x storage reduction across scalar-8bit, polar-8bit, polar-4bit compression methods. Enterprise+ configurable per KB." },
      { icon: Lock, title: "SAML SSO across 4 IdPs", desc: "Okta, Azure AD, Google Workspace, Custom SAML. SSO enforcement, break-glass admin, JIT provisioning." },
      { icon: Sparkles, title: "Persistent agent memory", desc: "Long-term agent memory with pgvector similarity search, 5 memory types, AI-powered extraction. Cross-session continuity for production agent deployments." },
      { icon: Bell, title: "Scheduled autonomous execution", desc: "Cron-based agent tasks with timezone support and multi-channel delivery (webhook, email, Slack)." },
      { icon: Shield, title: "Approval queue / Human-in-the-loop", desc: "Risk assessment per tool call, auto-approve conditions, timeout handling, full audit trails. Enterprise governance for agent-initiated actions." },
      { icon: Lock, title: "Org Secrets Store — Vault-backed", desc: "HashiCorp Vault-backed key-value secrets, runtime injection into agent system prompts. Org-scoped, never exposed to model providers." },
      { icon: MessageSquare, title: "Memwright — shared conversational memory", desc: "Per-session memory via SQLite + ChromaDB. Model tier gating (zero memory for small models, full context for premium tiers)." },
    ],
  },
  {
    date: "February 2026",
    items: [
      { icon: Rocket, title: "Deployment Provisioning", desc: "Deploy AI models directly into your cloud from the Bonito UI. AWS Provisioned Throughput (reserved capacity), Azure OpenAI deployments (Standard/GlobalStandard TPM), and GCP Vertex AI serverless — all without leaving the dashboard." },
      { icon: Lock, title: "Least-Privilege Permissions", desc: "Two IAM modes for every provider: Quick Start (managed roles for fast setup) and Enterprise (separate least-privilege policies per capability). Only grant the exact permissions each feature needs." },
      { icon: Route, title: "Routing Policies", desc: "Cost-optimized routing, failover chains, and A/B testing with weight-based model selection. Route requests intelligently across providers and models with dry-run testing." },
      { icon: Bell, title: "Notifications", desc: "In-app notification system for deployment lifecycle events, spend alerts, model activation confirmations, and provider health updates. Configurable alert rules with email and in-app delivery." },
      { icon: Terminal, title: "Bonito CLI", desc: "Python CLI (bonito-cli) for terminal-based management. Manage providers, models, gateway keys, routing policies, and costs from your terminal or CI/CD pipelines." },
      { icon: Bot, title: "AI Copilot", desc: "Natural language assistant for managing your AI infrastructure. Ask questions about costs, configure routing, and analyze provider health." },
      { icon: BarChart3, title: "Enhanced Cost Analytics", desc: "Breakdown by model, provider, team, and application. Export reports in CSV and PDF formats." },
    ],
  },
  {
    date: "January 2026",
    items: [
      { icon: Zap, title: "One-Click Model Activation", desc: "Enable models directly from the Bonito dashboard without leaving to your cloud console. Supports individual enable and bulk activation (up to 20 models at once). Works across AWS Bedrock entitlements, Azure deployments, and GCP API enablement." },
      { icon: Zap, title: "API Gateway v2", desc: "OpenAI-compatible gateway endpoint with intelligent request routing, automatic failover, and support for routing policies. One API key for all your providers." },
      { icon: Cloud, title: "Google Vertex AI Support", desc: "Full integration with Google Vertex AI including Gemini models. Connect and manage alongside your other providers." },
      { icon: Shield, title: "Audit Trail", desc: "Complete audit logging for every API call, configuration change, and team action. Export for compliance reporting." },
    ],
  },
  {
    date: "December 2025",
    items: [
      { icon: DollarSign, title: "Budget Alerts", desc: "Set spending thresholds per provider, per team, or globally. Receive email and in-app notifications before you exceed them." },
      { icon: Cloud, title: "Azure OpenAI Integration", desc: "Connect your Azure OpenAI deployments alongside AWS Bedrock for multi-cloud routing strategies." },
    ],
  },
  {
    date: "November 2025",
    items: [
      { icon: Zap, title: "Public Launch", desc: "Bonito is live! Unified multi-cloud AI management with support for AWS Bedrock, Azure OpenAI, and Google Cloud Vertex AI." },
    ],
  },
];

export default function ChangelogPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 md:px-12">
      <section className="pt-20 pb-16">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-4xl md:text-6xl font-bold tracking-tight"
        >
          Changelog
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mt-4 text-lg text-[#888]"
        >
          What&apos;s new in Bonito. ~25 ships in May 2026 alone — gateway, agents, KB, infra, governance. The cadence below is the cadence.
        </motion.p>
      </section>

      <section className="pb-24">
        <div className="space-y-16">
          {entries.map((entry, ei) => (
            <motion.div
              key={entry.date}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: ei * 0.1 }}
            >
              <h2 className="text-sm font-semibold text-[#7c3aed] uppercase tracking-wider mb-6">{entry.date}</h2>
              <div className="space-y-6 border-l-2 border-[#1a1a1a] pl-6">
                {entry.items.map((item) => (
                  <div key={item.title} className="relative">
                    <div className="absolute -left-[31px] top-1 w-4 h-4 rounded-full bg-[#7c3aed]/20 border-2 border-[#7c3aed] flex items-center justify-center">
                      <div className="w-1.5 h-1.5 rounded-full bg-[#7c3aed]" />
                    </div>
                    <h3 className="font-semibold mb-1">{item.title}</h3>
                    <p className="text-sm text-[#888] leading-relaxed">{item.desc}</p>
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>
      </section>
    </div>
  );
}
