import uuid
import secrets
from uuid import UUID
from typing import List, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.routing_policy import RoutingPolicy
from app.models.model import Model
from app.models.cloud_provider import CloudProvider
from app.models.user import User
from app.api.dependencies import get_current_user
from app.schemas.routing_policy import (
    RoutingPolicyCreate,
    RoutingPolicyUpdate, 
    RoutingPolicyResponse,
    RoutingPolicyDetailResponse,
    PolicyTestRequest,
    PolicyTestResult,
    PolicyStats
)

router = APIRouter(prefix="/routing-policies", tags=["routing-policies"])


def generate_api_key_prefix() -> str:
    """Generate a unique API key prefix for routing policies."""
    return f"rt-{secrets.token_hex(8)}"


async def validate_model_ids(model_ids: List[UUID], org_id: UUID, db: AsyncSession) -> None:
    """Validate that all model IDs belong to the organization."""
    result = await db.execute(
        select(func.count(Model.id))
        .join(CloudProvider, Model.provider_id == CloudProvider.id)
        .where(
            and_(
                Model.id.in_(model_ids),
                CloudProvider.org_id == org_id
            )
        )
    )
    count = result.scalar()
    if count != len(model_ids):
        raise HTTPException(
            status_code=400,
            detail="One or more model IDs do not belong to your organization"
        )


async def get_model_names(model_ids: List[UUID], db: AsyncSession) -> Dict[str, str]:
    """Get display names for model IDs."""
    result = await db.execute(
        select(Model.id, Model.display_name)
        .where(Model.id.in_(model_ids))
    )
    return {str(model_id): display_name for model_id, display_name in result.all()}


@router.post("", response_model=RoutingPolicyResponse, status_code=201)
async def create_routing_policy(
    data: RoutingPolicyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Create a new routing policy."""
    # Validate that all model IDs belong to the organization
    model_ids = [model.model_id for model in data.models]
    await validate_model_ids(model_ids, user.org_id, db)
    
    # Generate unique API key prefix
    api_key_prefix = generate_api_key_prefix()
    
    # Ensure unique API key prefix
    while True:
        result = await db.execute(
            select(RoutingPolicy.id).where(RoutingPolicy.api_key_prefix == api_key_prefix)
        )
        if not result.scalar_one_or_none():
            break
        api_key_prefix = generate_api_key_prefix()
    
    policy = RoutingPolicy(
        org_id=user.org_id,
        name=data.name,
        description=data.description,
        strategy=data.strategy,
        models=[{**model.model_dump(), "model_id": str(model.model_id)} for model in data.models],
        rules=data.rules.model_dump(),
        is_active=data.is_active,
        api_key_prefix=api_key_prefix
    )
    
    db.add(policy)
    await db.flush()
    await db.refresh(policy)
    
    return policy


@router.get("", response_model=List[RoutingPolicyResponse])
async def list_routing_policies(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """List all routing policies for the organization."""
    result = await db.execute(
        select(RoutingPolicy)
        .where(RoutingPolicy.org_id == user.org_id)
        .order_by(RoutingPolicy.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{policy_id}", response_model=RoutingPolicyDetailResponse)
async def get_routing_policy(
    policy_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get routing policy details with resolved model names."""
    result = await db.execute(
        select(RoutingPolicy).where(
            and_(
                RoutingPolicy.id == policy_id,
                RoutingPolicy.org_id == user.org_id
            )
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Routing policy not found")
    
    # Get model names
    model_ids = [UUID(model["model_id"]) for model in policy.models]
    model_names = await get_model_names(model_ids, db)
    
    # Create response with model names
    response_data = {
        **policy.__dict__,
        "model_names": model_names
    }
    return RoutingPolicyDetailResponse(**response_data)


@router.put("/{policy_id}", response_model=RoutingPolicyResponse)
async def update_routing_policy(
    policy_id: UUID,
    data: RoutingPolicyUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Update a routing policy."""
    result = await db.execute(
        select(RoutingPolicy).where(
            and_(
                RoutingPolicy.id == policy_id,
                RoutingPolicy.org_id == user.org_id
            )
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Routing policy not found")
    
    # If updating models, validate model IDs
    if data.models is not None:
        model_ids = [model.model_id for model in data.models]
        await validate_model_ids(model_ids, user.org_id, db)
        policy.models = [{**model.model_dump(), "model_id": str(model.model_id)} for model in data.models]
    
    # Update other fields
    for field, value in data.model_dump(exclude_unset=True, exclude={"models"}).items():
        if hasattr(policy, field) and value is not None:
            setattr(policy, field, value)
    
    await db.flush()
    await db.refresh(policy)
    
    return policy


@router.delete("/{policy_id}", status_code=204)
async def delete_routing_policy(
    policy_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Delete a routing policy."""
    result = await db.execute(
        select(RoutingPolicy).where(
            and_(
                RoutingPolicy.id == policy_id,
                RoutingPolicy.org_id == user.org_id
            )
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Routing policy not found")
    
    await db.delete(policy)


@router.post("/{policy_id}/test", response_model=PolicyTestResult)
async def test_routing_policy(
    policy_id: UUID,
    data: PolicyTestRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Test a routing policy with a sample prompt (dry-run)."""
    result = await db.execute(
        select(RoutingPolicy).where(
            and_(
                RoutingPolicy.id == policy_id,
                RoutingPolicy.org_id == user.org_id
            )
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Routing policy not found")
    
    if not policy.models:
        raise HTTPException(status_code=400, detail="Policy has no models configured")
    
    import random

    # Real model selection logic matching gateway.apply_routing_policy
    selected_model = None
    selection_reason = ""
    
    if policy.strategy == "cost_optimized":
        # Sort by weight (higher = cheaper) and pick cheapest
        sorted_models = sorted(policy.models, key=lambda m: m.get("weight", 0), reverse=True)
        selected_model = sorted_models[0]
        selection_reason = "Selected cheapest model for cost optimization"
    
    elif policy.strategy == "latency_optimized":
        sorted_models = sorted(policy.models, key=lambda m: m.get("weight", 0), reverse=True)
        selected_model = sorted_models[0]
        selection_reason = "Selected fastest model for latency optimization"
    
    elif policy.strategy == "balanced":
        selected_model = random.choice(policy.models)
        selection_reason = "Selected using balanced random strategy"
    
    elif policy.strategy == "failover":
        # Pick primary first, then fallbacks in order
        for model_config in policy.models:
            if model_config.get("role") == "primary" or not model_config.get("role"):
                selected_model = model_config
                selection_reason = f"Primary model selected (failover chain: {len(policy.models)} models)"
                break
        if not selected_model:
            for model_config in policy.models:
                if model_config.get("role") == "fallback":
                    selected_model = model_config
                    selection_reason = "Fallback model selected (primary unavailable)"
                    break
    
    elif policy.strategy == "ab_test":
        # Weight-based random selection
        rand = random.random() * 100
        cumulative_weight = 0
        for model_config in policy.models:
            weight = model_config.get("weight", 0)
            cumulative_weight += weight
            if rand <= cumulative_weight:
                selected_model = model_config
                selection_reason = f"A/B test: selected with {weight}% weight (roll: {rand:.1f})"
                break
    
    if not selected_model:
        selected_model = policy.models[0]
        selection_reason = "Default selection (no strategy match)"
    
    # Get model name
    model_ids = [UUID(selected_model["model_id"])]
    model_names = await get_model_names(model_ids, db)
    model_name = model_names.get(selected_model["model_id"], "Unknown Model")
    
    return PolicyTestResult(
        selected_model_id=UUID(selected_model["model_id"]),
        selected_model_name=model_name,
        strategy_used=policy.strategy,
        selection_reason=selection_reason,
        estimated_cost=0.01,  # Demo value
        estimated_latency_ms=150  # Demo value
    )


@router.get("/{policy_id}/stats", response_model=PolicyStats)
async def get_policy_stats(
    policy_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get usage statistics for a routing policy."""
    result = await db.execute(
        select(RoutingPolicy).where(
            and_(
                RoutingPolicy.id == policy_id,
                RoutingPolicy.org_id == user.org_id
            )
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Routing policy not found")
    
    # TODO: Implement real stats from gateway logs when traffic exists
    model_distribution = {}
    if policy.models:
        for m in policy.models:
            model_distribution[str(m.get("model_id", "unknown"))] = 0

    return PolicyStats(
        policy_id=policy_id,
        request_count=0,
        total_cost=0.0,
        avg_latency_ms=0.0,
        success_rate=0.0,
        last_24h_requests=0,
        model_distribution=model_distribution,
    )