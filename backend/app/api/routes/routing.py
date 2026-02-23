import uuid
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.routing import RoutingRule
from app.schemas.routing import (
    RoutingRuleCreate,
    RoutingRuleUpdate,
    RoutingRuleResponse,
    SimulationRequest,
    SimulationResult,
    RoutingAnalytics,
)
from app.api.dependencies import get_current_user, require_feature
from app.models.user import User
from app.services.routing_service import simulate_routing, simulate_routing_real, route_and_invoke, get_routing_analytics
from app.services.feature_gate import feature_gate

router = APIRouter(prefix="/routing", tags=["routing"])


async def _require_routing(db: AsyncSession, user: User):
    """Check that the organization has access to the routing feature."""
    await feature_gate.require_feature(db, str(user.org_id), "routing")


@router.get("/rules", response_model=List[RoutingRuleResponse])
async def list_rules(
    db: AsyncSession = Depends(get_db), 
    user: User = Depends(require_feature("routing"))
):
    result = await db.execute(
        select(RoutingRule).where(RoutingRule.org_id == user.org_id).order_by(RoutingRule.priority)
    )
    return result.scalars().all()


@router.post("/rules", response_model=RoutingRuleResponse, status_code=201)
async def create_rule(data: RoutingRuleCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await _require_routing(db, user)
    rule = RoutingRule(
        org_id=user.org_id,
        name=data.name,
        strategy=data.strategy,
        conditions_json=data.conditions_json,
        priority=data.priority,
        enabled=data.enabled,
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return rule


@router.patch("/rules/{rule_id}", response_model=RoutingRuleResponse)
async def update_rule(rule_id: UUID, data: RoutingRuleUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await _require_routing(db, user)
    result = await db.execute(select(RoutingRule).where(RoutingRule.id == rule_id, RoutingRule.org_id == user.org_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Routing rule not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    await db.flush()
    await db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(rule_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await _require_routing(db, user)
    result = await db.execute(select(RoutingRule).where(RoutingRule.id == rule_id, RoutingRule.org_id == user.org_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Routing rule not found")
    await db.delete(rule)


@router.post("/simulate", response_model=SimulationResult)
async def simulate(req: SimulationRequest, strategy: str = "balanced", db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Simulate routing using real connected providers."""
    await _require_routing(db, user)
    return await simulate_routing_real(req, strategy, db)


@router.post("/invoke")
async def invoke_routed(
    prompt: str,
    strategy: str = "balanced",
    model_type: str = "text",
    max_tokens: int = 1024,
    temperature: float = 0.7,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Route a prompt to the best provider and invoke the model."""
    await _require_routing(db, user)
    try:
        return await route_and_invoke(prompt, strategy, db, model_type, max_tokens, temperature)
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/analytics", response_model=RoutingAnalytics)
async def analytics(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await _require_routing(db, user)
    return get_routing_analytics()
