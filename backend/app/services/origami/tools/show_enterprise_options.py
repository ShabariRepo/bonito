"""show_enterprise_options — what Enterprise unlocks today vs. roadmap.

Enterprise prospects (and existing customers planning a tier upgrade) ask
"what do we actually get on Enterprise?" Origami should be able to answer
in chat with the same honesty we'd give on a sales call: features that
exist today, features that are partial / gated, and features that are
roadmap-only — without conflating the three.

The split matters a lot. Pitching VPC peering as "available" before it's
built is the kind of thing that breaks enterprise trust on the third call.
Read-only tool, no plan card. Output is structured so the model can
naturally tailor the answer to the user's actual tier and any specific
concern they raised ("security", "compliance", "scale", etc).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.origami.tools.base import OrigamiTool, register_tool


_VALID_CATEGORIES = {"all", "security", "compliance", "scale", "governance", "support"}


@register_tool
class ShowEnterpriseOptionsTool(OrigamiTool):
    name = "show_enterprise_options"
    description = (
        "List what the Bonito Enterprise tier (and Scale tier) actually "
        "unlock today, what's partial, and what's on the roadmap. Use "
        "this when the user asks 'what do we get on Enterprise', 'how "
        "does this work for an enterprise team', 'what about VPC / SSO "
        "/ compliance / SLA / audit log export', or anything similar. "
        "Returns three honest buckets: available, partial/gated, and "
        "roadmap. Read-only, no plan card. Always cite the contact path "
        "(shabari@bonito.ai) for procurement, pricing, and roadmap "
        "questions you can't answer from the structured output."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": sorted(_VALID_CATEGORIES),
                "description": (
                    "Optional focus area to bias the answer toward. "
                    "Defaults to 'all'."
                ),
            },
        },
        "required": [],
        "additionalProperties": False,
    }
    is_write = False

    async def execute(
        self,
        *,
        org_id: uuid.UUID,
        user: User,
        params: dict[str, Any],
        db: AsyncSession,
    ) -> dict[str, Any]:
        from app.services.feature_gate import feature_gate

        try:
            sub = await feature_gate.get_organization_subscription(db, str(org_id))
            tier = (sub["tier"].value if hasattr(sub["tier"], "value") else str(sub["tier"])).lower()
        except Exception:
            tier = "free"

        category = (params.get("category") or "all").lower()
        if category not in _VALID_CATEGORIES:
            category = "all"

        # ── Available today (shipped + working) ─────────────────────────
        available = [
            {
                "name": "SAML SSO",
                "category": "security",
                "detail": "Okta, Azure AD, Google Workspace, and Custom SAML. JIT provisioning, SSO enforcement, break-glass admin.",
            },
            {
                "name": "RBAC",
                "category": "security",
                "detail": "Role-based access control across org/project/agent boundaries.",
            },
            {
                "name": "Org Secrets Store (HashiCorp Vault)",
                "category": "security",
                "detail": "Customer credentials encrypted at rest in Vault; runtime injection into agent prompts.",
            },
            {
                "name": "Audit log export to GCS",
                "category": "compliance",
                "detail": "Org-partitioned NDJSON sink (logs/{org_id}/{log_type}/{YYYY}/{MM}/{DD}/{HH}.ndjson). Tier-aware retention.",
            },
            {
                "name": "99.9% SLA",
                "category": "support",
                "detail": "Enterprise tier carries a 99.9% uptime SLA. Scale tier carries 99.99%.",
            },
            {
                "name": "Multi-cloud governance + compliance checks",
                "category": "compliance",
                "detail": "SOC-2, HIPAA, GDPR, ISO27001 policy checks across AWS, Azure, GCP.",
            },
            {
                "name": "Agent HPA (autoscaling)",
                "category": "scale",
                "detail": "Virtual scale-up on RPM utilization, automatic scale-down via background loop. Configurable via API, CLI, and bonito.yaml. Enterprise+ only.",
            },
            {
                "name": "Overflow queue",
                "category": "scale",
                "detail": "Redis-backed FIFO queue per agent. Returns 202 Accepted with ticket_id + poll_url when RPM is saturated; drainer processes as capacity frees up.",
            },
            {
                "name": "Persistent agent memory",
                "category": "scale",
                "detail": "Long-term memory with pgvector similarity search across 5 memory types.",
            },
            {
                "name": "Approval queue (human-in-the-loop)",
                "category": "governance",
                "detail": "Risk assessment, auto-approve conditions, timeout handling, audit trails.",
            },
            {
                "name": "Cost intelligence",
                "category": "governance",
                "detail": "Real-time aggregation, forecasting, optimization recommendations across providers.",
            },
            {
                "name": "Intelligent multi-provider failover",
                "category": "scale",
                "detail": "Detects rate limits, 5xx, model unavailability; retries on equivalent models across providers.",
            },
            {
                "name": "AI Context (RAG) — cross-cloud knowledge bases",
                "category": "scale",
                "detail": "Upload/parse/chunk/embed docs, pgvector HNSW search, gateway context injection with source citations.",
            },
            {
                "name": "External orchestration / Breadcrumbs tracing",
                "category": "governance",
                "detail": "Code-orchestrated agent pipelines log delegation records in the parent agent's session for visualisation.",
            },
            {
                "name": "Personal access tokens + project tokens",
                "category": "security",
                "detail": "bp- PATs work on all endpoints; bj- project tokens scope to a single project for least-privilege per-app credentials.",
            },
            {
                "name": "Origami in-app build workspace",
                "category": "governance",
                "detail": "Conversational interface to plan, deploy, and govern Bonito infrastructure (projects, KBs, agents, gateway keys) without leaving the dashboard.",
            },
        ]

        # ── Partial / gated (shipped but with caveats) ──────────────────
        partial = [
            {
                "name": "VectorBoost (KB compression)",
                "category": "scale",
                "detail": "API endpoints + config available on Enterprise. Compression pipeline is NOT yet wired into ingestion — endpoint-gated to prevent configuring a feature that doesn't fully work yet.",
            },
            {
                "name": "Vault tenant isolation",
                "category": "security",
                "detail": "Customer credentials live in Vault at providers/{provider_id} today. Move to providers/{org_id}/{provider_id} (proper org-namespacing) is queued.",
            },
        ]

        # ── Roadmap (not built yet, but planned) ────────────────────────
        roadmap = [
            {
                "name": "VPC Gateway Agent",
                "category": "security",
                "detail": "Enterprise self-hosted data plane that runs in the customer's VPC, so inference traffic never leaves the customer's network. Planned.",
            },
            {
                "name": "SOC-2 Type II certification",
                "category": "compliance",
                "detail": "Active program (see docs/SOC2-ROADMAP.md). Type I posture is in place via controls; Type II audit not yet started.",
            },
            {
                "name": "Smart routing (complexity-aware model selection)",
                "category": "scale",
                "detail": "Pick the cheapest model that can handle the request based on prompt analysis.",
            },
            {
                "name": "Advanced audit log SIEM integration",
                "category": "compliance",
                "detail": "Direct Splunk / Datadog / Chronicle connectors beyond the GCS NDJSON sink we have today.",
            },
            {
                "name": "Additional providers",
                "category": "scale",
                "detail": "Cohere, Mistral, and customer-owned endpoint integrations are queued behind the current 6 (AWS Bedrock, Azure, GCP Vertex, OpenAI, Anthropic, Groq).",
            },
            {
                "name": "Agent HPA Phase 2 — physical replicas + load balancer",
                "category": "scale",
                "detail": "Today's Phase 1 is virtual scaling. Phase 2 adds true replica spawning behind a load balancer for hard-capped agents.",
            },
        ]

        if category != "all":
            available = [f for f in available if f["category"] == category]
            partial = [f for f in partial if f["category"] == category]
            roadmap = [f for f in roadmap if f["category"] == category]

        # Tier headlines
        tier_pricing = {
            "free": "$0 — invite-only, 3 providers, 25K requests/mo, basic failover.",
            "starter": "$199/mo — 3 providers, 100K req/mo, 5 seats, 2 agents.",
            "pro": "$999/mo — 5 providers, 500K req/mo, unlimited seats, 5 agents.",
            "enterprise": "Starts at $6K/mo (typical band $6K-$20K) — unlimited everything, SSO/SAML, RBAC, compliance, 99.9% SLA. Single SKU; Enterprise+ with dedicated infra + multi-region + named TAM is on the roadmap.",
            "scale": "Custom ($200K+/yr) — dedicated infra, multi-region, 99.99% SLA, custom fine-tuning, dedicated account team.",
        }

        return {
            "success": True,
            "current_tier": tier,
            "current_tier_pricing": tier_pricing.get(tier),
            "tier_above": (
                "enterprise" if tier in {"free", "starter", "pro", "growth", "builder"}
                else "scale" if tier == "enterprise"
                else None
            ),
            "category_focus": category,
            "available_today": available,
            "partial_or_gated": partial,
            "roadmap": roadmap,
            "contact": {
                "procurement": "shabari@bonito.ai",
                "roadmap_questions": "shabari@bonito.ai",
                "security_review": "shabari@bonito.ai",
            },
            "notes": [
                "Available-today items are shipped and routinely exercised in prod.",
                "Partial/gated items are visible in the UI/API but have known caveats. Ask before relying on them.",
                "Roadmap items are not built. Don't pitch them as deliverable on a specific date without checking first.",
            ],
            "next_step": (
                "If you have a specific enterprise concern (compliance audit, "
                "VPC requirement, custom SLA, security review), reply with the "
                "specific ask and I'll either point at the live capability or "
                "loop in Shabari at shabari@bonito.ai."
            ),
        }
