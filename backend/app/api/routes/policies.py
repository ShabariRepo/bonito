import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.policy import Policy
from app.schemas.policy import PolicyCreate, PolicyUpdate, PolicyResponse

router = APIRouter(prefix="/policies", tags=["policies"])


async def _require_routing(db: AsyncSession, user: User):
    """Check that the organization has access to the routing feature."""
    from app.services.feature_gate import feature_gate
    await feature_gate.require_feature(db, str(user.org_id), "routing")


@router.get("", response_model=List[PolicyResponse])
async def list_policies(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_routing(db, user)
    result = await db.execute(
        select(Policy).where(Policy.org_id == user.org_id).order_by(Policy.created_at)
    )
    return result.scalars().all()


@router.post("", response_model=PolicyResponse, status_code=201)
async def create_policy(
    data: PolicyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_routing(db, user)
    policy = Policy(
        id=uuid.uuid4(),
        org_id=user.org_id,
        name=data.name,
        type=data.type,
        rules_json=data.rules_json,
        description=data.description,
        enabled=data.enabled,
    )
    db.add(policy)
    await db.flush()
    await db.refresh(policy)
    return policy


@router.patch("/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: str,
    data: PolicyUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_routing(db, user)
    result = await db.execute(
        select(Policy).where(
            Policy.id == uuid.UUID(policy_id),
            Policy.org_id == user.org_id,
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    if data.name is not None:
        policy.name = data.name
    if data.type is not None:
        policy.type = data.type
    if data.rules_json is not None:
        policy.rules_json = data.rules_json
    if data.description is not None:
        policy.description = data.description
    if data.enabled is not None:
        policy.enabled = data.enabled

    await db.flush()
    await db.refresh(policy)
    return policy


@router.delete("/{policy_id}", status_code=204)
async def delete_policy(
    policy_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_routing(db, user)
    result = await db.execute(
        select(Policy).where(
            Policy.id == uuid.UUID(policy_id),
            Policy.org_id == user.org_id,
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    await db.delete(policy)
    await db.flush()
