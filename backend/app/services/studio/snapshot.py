"""Org snapshot for Bonito Studio's first-turn opener.

Returns a single dict summarizing the org's current state — providers,
agents, KBs, last-7-day gateway usage, billing, projects. The Studio chat
route injects a rendered version of this into the user_content prefix
so the BDR opener can ground its first reply ("you have 3 providers
connected and did 12K gateway requests yesterday — want to look at
usage, build an agent, or something else?").

Performance target: <500ms p95. We fire all the count queries in parallel
via asyncio.gather. No external service hops — pure DB reads against
already-indexed columns (every aggregate is filtered by org_id which
every relevant table indexes).

Fail-open philosophy: if any single sub-query fails we log + omit that
field. The snapshot still renders, just with one section missing. Studio
chat must keep working even when one count query trips.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.cloud_provider import CloudProvider
from app.models.gateway import GatewayRequest
from app.models.knowledge_base import KnowledgeBase
from app.models.organization import Organization
from app.models.project import Project

logger = logging.getLogger(__name__)


@dataclass
class ProviderSummary:
    provider_type: str
    status: str


@dataclass
class GatewayUsage:
    requests_7d: int = 0
    cost_7d_usd: float = 0.0
    top_models: list[tuple[str, int]] = field(default_factory=list)


@dataclass
class BillingSummary:
    tier: str = "free"
    days_since_signup: int = 0


@dataclass
class StudioSnapshot:
    """Single-shot snapshot consumed by Studio's opener.

    Every field is best-effort. Missing fields signal we couldn't reach the
    underlying table for some reason — the opener template renders around
    that gracefully.
    """

    org_id: str
    org_name: Optional[str] = None
    providers: list[ProviderSummary] = field(default_factory=list)
    agent_count: int = 0
    agent_active_count: int = 0
    kb_count: int = 0
    kb_total_documents: int = 0
    gateway: GatewayUsage = field(default_factory=GatewayUsage)
    billing: BillingSummary = field(default_factory=BillingSummary)
    project_count: int = 0
    generated_at: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "org_id": self.org_id,
            "org_name": self.org_name,
            "providers": [
                {"provider_type": p.provider_type, "status": p.status}
                for p in self.providers
            ],
            "agent_count": self.agent_count,
            "agent_active_count": self.agent_active_count,
            "kb_count": self.kb_count,
            "kb_total_documents": self.kb_total_documents,
            "gateway": {
                "requests_7d": self.gateway.requests_7d,
                "cost_7d_usd": round(self.gateway.cost_7d_usd, 4),
                "top_models": [
                    {"model": m, "requests": c}
                    for (m, c) in self.gateway.top_models
                ],
            },
            "billing": {
                "tier": self.billing.tier,
                "days_since_signup": self.billing.days_since_signup,
            },
            "project_count": self.project_count,
            "generated_at": self.generated_at,
        }


async def _fetch_org(
    db: AsyncSession, org_id: uuid.UUID
) -> tuple[Optional[str], BillingSummary]:
    try:
        row = (
            await db.execute(
                select(
                    Organization.name,
                    Organization.subscription_tier,
                    Organization.created_at,
                ).where(Organization.id == org_id)
            )
        ).one_or_none()
        if not row:
            return None, BillingSummary()
        name, tier, created_at = row
        days = 0
        if created_at:
            days = max(0, (datetime.now(tz=timezone.utc) - created_at).days)
        return name, BillingSummary(tier=tier or "free", days_since_signup=days)
    except Exception:
        logger.exception("studio.snapshot: org fetch failed for %s", org_id)
        return None, BillingSummary()


async def _fetch_providers(
    db: AsyncSession, org_id: uuid.UUID
) -> list[ProviderSummary]:
    try:
        rows = (
            await db.execute(
                select(CloudProvider.provider_type, CloudProvider.status)
                .where(CloudProvider.org_id == org_id)
                .order_by(CloudProvider.created_at.asc())
            )
        ).all()
        return [ProviderSummary(provider_type=t, status=s) for t, s in rows]
    except Exception:
        logger.exception("studio.snapshot: providers fetch failed for %s", org_id)
        return []


async def _fetch_agent_counts(
    db: AsyncSession, org_id: uuid.UUID
) -> tuple[int, int]:
    try:
        total = (
            await db.execute(
                select(func.count(Agent.id)).where(Agent.org_id == org_id)
            )
        ).scalar() or 0
        active = (
            await db.execute(
                select(func.count(Agent.id)).where(
                    Agent.org_id == org_id, Agent.status == "active"
                )
            )
        ).scalar() or 0
        return int(total), int(active)
    except Exception:
        logger.exception("studio.snapshot: agent count failed for %s", org_id)
        return 0, 0


async def _fetch_kb_summary(
    db: AsyncSession, org_id: uuid.UUID
) -> tuple[int, int]:
    try:
        row = (
            await db.execute(
                select(
                    func.count(KnowledgeBase.id),
                    func.coalesce(func.sum(KnowledgeBase.document_count), 0),
                ).where(KnowledgeBase.org_id == org_id)
            )
        ).one_or_none()
        if not row:
            return 0, 0
        return int(row[0] or 0), int(row[1] or 0)
    except Exception:
        logger.exception("studio.snapshot: kb summary failed for %s", org_id)
        return 0, 0


async def _fetch_gateway_usage(
    db: AsyncSession, org_id: uuid.UUID
) -> GatewayUsage:
    try:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=7)
        agg = (
            await db.execute(
                select(
                    func.count(GatewayRequest.id),
                    func.coalesce(func.sum(GatewayRequest.cost), 0.0),
                ).where(
                    GatewayRequest.org_id == org_id,
                    GatewayRequest.created_at >= cutoff,
                )
            )
        ).one_or_none()
        requests_7d = int(agg[0] or 0) if agg else 0
        cost_7d = float(agg[1] or 0.0) if agg else 0.0

        top_models: list[tuple[str, int]] = []
        if requests_7d > 0:
            top_rows = (
                await db.execute(
                    select(
                        GatewayRequest.model_used,
                        func.count(GatewayRequest.id).label("n"),
                    )
                    .where(
                        GatewayRequest.org_id == org_id,
                        GatewayRequest.created_at >= cutoff,
                        GatewayRequest.model_used.isnot(None),
                    )
                    .group_by(GatewayRequest.model_used)
                    .order_by(func.count(GatewayRequest.id).desc())
                    .limit(3)
                )
            ).all()
            top_models = [(m, int(n)) for m, n in top_rows]

        return GatewayUsage(
            requests_7d=requests_7d,
            cost_7d_usd=cost_7d,
            top_models=top_models,
        )
    except Exception:
        logger.exception("studio.snapshot: gateway usage failed for %s", org_id)
        return GatewayUsage()


async def _fetch_project_count(db: AsyncSession, org_id: uuid.UUID) -> int:
    try:
        n = (
            await db.execute(
                select(func.count(Project.id)).where(Project.org_id == org_id)
            )
        ).scalar() or 0
        return int(n)
    except Exception:
        logger.exception("studio.snapshot: project count failed for %s", org_id)
        return 0


async def get_org_snapshot(
    *, db: AsyncSession, org_id: uuid.UUID
) -> StudioSnapshot:
    """Fan out every snapshot query in parallel and assemble the dataclass.

    All sub-queries are wrapped to fail open — a single broken query
    surfaces as a zero/empty field, not a 500. The opener template handles
    empty fields gracefully.
    """
    (
        org_summary,
        providers,
        agent_counts,
        kb_summary,
        gateway_usage,
        project_count,
    ) = await asyncio.gather(
        _fetch_org(db, org_id),
        _fetch_providers(db, org_id),
        _fetch_agent_counts(db, org_id),
        _fetch_kb_summary(db, org_id),
        _fetch_gateway_usage(db, org_id),
        _fetch_project_count(db, org_id),
    )

    org_name, billing = org_summary
    agent_total, agent_active = agent_counts
    kb_count, kb_docs = kb_summary

    return StudioSnapshot(
        org_id=str(org_id),
        org_name=org_name,
        providers=providers,
        agent_count=agent_total,
        agent_active_count=agent_active,
        kb_count=kb_count,
        kb_total_documents=kb_docs,
        gateway=gateway_usage,
        billing=billing,
        project_count=project_count,
    )
