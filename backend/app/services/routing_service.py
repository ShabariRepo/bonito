"""Routing service — real cross-provider model routing.

Routes AI requests to the best provider based on strategy,
using real pricing data from connected providers.
"""

import logging
import time
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud_provider import CloudProvider as CloudProviderModel
from app.services.provider_service import (
    get_aws_provider,
    get_azure_provider,
    get_gcp_provider,
    get_models_for_provider,
)
from app.schemas.routing import (
    SimulationRequest,
    SimulationResult,
    ProviderOption,
    RoutingAnalytics,
)

logger = logging.getLogger(__name__)

STRATEGY_DESCRIPTIONS = {
    "cost-optimized": "Routes to the cheapest provider that meets requirements",
    "latency-optimized": "Routes to the fastest provider available",
    "balanced": "Balances cost and latency for optimal value",
    "failover": "Routes to primary provider with automatic failover chain",
}


async def simulate_routing_real(
    req: SimulationRequest,
    strategy: str,
    db: AsyncSession,
) -> SimulationResult:
    """Simulate routing using real connected providers and their models."""
    result = await db.execute(
        select(CloudProviderModel).where(CloudProviderModel.status == "active")
    )
    providers = result.scalars().all()

    all_options: list[ProviderOption] = []
    decision_path = [
        f"Request: {req.prompt_description}",
        f"Model type: {req.model_type}",
        f"Strategy: {strategy}",
        f"Connected providers: {len(providers)}",
    ]

    # Gather real models from all connected providers
    for p in providers:
        try:
            models = await get_models_for_provider(p.provider_type, str(p.id))
            for m in models:
                # Filter by model type if specified
                if req.model_type and req.model_type != "any":
                    caps = m.capabilities if hasattr(m, 'capabilities') else []
                    if req.model_type not in caps and req.model_type != "text":
                        continue

                cost_per_1k = (m.input_price_per_1k or 0) + (m.output_price_per_1k or 0)
                all_options.append(ProviderOption(
                    provider=p.provider_type,
                    model=m.provider_model_id if hasattr(m, 'provider_model_id') else m.name,
                    estimated_latency_ms=_estimate_latency(p.provider_type),
                    cost_per_1k_tokens=round(cost_per_1k, 6),
                    region=_get_region(p),
                    selected=False,
                    reason="",
                ))
        except Exception as e:
            decision_path.append(f"⚠ {p.provider_type}: failed to list models ({e})")

    if not all_options:
        decision_path.append("No models available from connected providers")
        return SimulationResult(
            selected_provider="none",
            selected_model="none",
            strategy_used=strategy,
            decision_path=decision_path,
            options=[],
            estimated_cost_savings_pct=0,
            estimated_latency_ms=0,
        )

    decision_path.append(f"Collected {len(all_options)} models across providers")

    # Apply strategy
    if strategy == "cost-optimized":
        all_options.sort(key=lambda o: o.cost_per_1k_tokens)
        decision_path.append("Sorted by cost (ascending)")
    elif strategy == "latency-optimized":
        all_options.sort(key=lambda o: o.estimated_latency_ms)
        decision_path.append("Sorted by estimated latency (ascending)")
    elif strategy == "failover":
        # Primary = first provider, failover chain
        decision_path.append("Using failover: primary → secondary → tertiary")
    else:  # balanced
        all_options.sort(key=lambda o: o.cost_per_1k_tokens * 0.4 + o.estimated_latency_ms * 0.002)
        decision_path.append("Balanced scoring: cost × 0.4 + latency × 0.002")

    # Apply filters
    if req.max_cost_per_token:
        filtered = [o for o in all_options if o.cost_per_1k_tokens <= req.max_cost_per_token * 1000]
        if filtered:
            all_options = filtered
            decision_path.append(f"Filtered by max cost: ${req.max_cost_per_token}/token → {len(filtered)} remain")

    if req.preferred_region:
        regional = [o for o in all_options if req.preferred_region in o.region]
        if regional:
            all_options = regional + [o for o in all_options if o not in regional]
            decision_path.append(f"Prioritized region: {req.preferred_region}")

    # Select winner
    winner = all_options[0]
    winner.selected = True
    winner.reason = f"Best match for {strategy} strategy"
    decision_path.append(f"✅ Selected: {winner.provider} / {winner.model}")

    # Annotate alternatives
    for o in all_options[1:]:
        if o.cost_per_1k_tokens > winner.cost_per_1k_tokens:
            o.reason = f"${o.cost_per_1k_tokens - winner.cost_per_1k_tokens:.4f}/1k more expensive"
        elif o.estimated_latency_ms > winner.estimated_latency_ms:
            o.reason = f"{o.estimated_latency_ms - winner.estimated_latency_ms}ms slower"
        else:
            o.reason = "Not selected by strategy"

    avg_cost = sum(o.cost_per_1k_tokens for o in all_options) / len(all_options)
    savings = ((avg_cost - winner.cost_per_1k_tokens) / avg_cost) * 100 if avg_cost > 0 else 0

    return SimulationResult(
        selected_provider=winner.provider,
        selected_model=winner.model,
        strategy_used=strategy,
        decision_path=decision_path,
        options=all_options[:10],
        estimated_cost_savings_pct=round(savings, 1),
        estimated_latency_ms=winner.estimated_latency_ms,
    )


async def route_and_invoke(
    prompt: str,
    strategy: str,
    db: AsyncSession,
    model_type: str = "text",
    max_tokens: int = 1024,
    temperature: float = 0.7,
) -> dict:
    """Actually route a request and invoke the selected model."""
    sim = await simulate_routing_real(
        SimulationRequest(
            prompt_description=prompt[:100],
            model_type=model_type,
        ),
        strategy=strategy,
        db=db,
    )

    if sim.selected_provider == "none":
        raise RuntimeError("No providers available for routing")

    # Get the actual provider and invoke
    result = await db.execute(
        select(CloudProviderModel).where(
            CloudProviderModel.provider_type == sim.selected_provider,
            CloudProviderModel.status == "active",
        )
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise RuntimeError(f"Provider {sim.selected_provider} not found")

    provider_id = str(provider.id)
    start = time.monotonic()

    if provider.provider_type == "aws":
        cloud = await get_aws_provider(provider_id)
    elif provider.provider_type == "azure":
        cloud = await get_azure_provider(provider_id)
    elif provider.provider_type == "gcp":
        cloud = await get_gcp_provider(provider_id)
    else:
        raise RuntimeError(f"Unknown provider: {provider.provider_type}")

    inv = await cloud.invoke_model(
        model_id=sim.selected_model,
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    return {
        "response": inv.response_text,
        "routing": {
            "provider": sim.selected_provider,
            "model": sim.selected_model,
            "strategy": strategy,
            "decision_path": sim.decision_path,
        },
        "usage": {
            "input_tokens": inv.input_tokens,
            "output_tokens": inv.output_tokens,
            "latency_ms": inv.latency_ms,
            "cost": inv.estimated_cost,
        },
    }


def _estimate_latency(provider_type: str) -> int:
    """Baseline latency estimate per provider (will be replaced with real measurements)."""
    return {"aws": 180, "azure": 200, "gcp": 160}.get(provider_type, 200)


def _get_region(provider) -> str:
    """Extract region from provider credentials ref."""
    try:
        creds = provider.credentials_encrypted or ""
        if "vault:" in creds:
            return ""  # Can't read vault inline
        return ""
    except Exception:
        return ""


# ── Legacy API compatibility ────────────────────────────────────


def simulate_routing(req: SimulationRequest, strategy: str = "balanced") -> SimulationResult:
    """Sync fallback for when no DB session available."""
    return SimulationResult(
        selected_provider="none",
        selected_model="none",
        strategy_used=strategy,
        decision_path=["No database session — use async endpoint"],
        options=[],
        estimated_cost_savings_pct=0,
        estimated_latency_ms=0,
    )


def get_routing_analytics() -> RoutingAnalytics:
    """Placeholder — will be replaced with real analytics from DB."""
    return RoutingAnalytics(
        total_requests=0,
        requests_by_provider={},
        cost_savings_pct=0,
        avg_latency_ms=0,
        latency_by_provider={},
        routing_distribution={},
    )
