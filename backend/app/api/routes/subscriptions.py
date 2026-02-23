from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user, require_superadmin
from app.models.user import User
from app.models.organization import Organization
from app.models.subscription_history import SubscriptionHistory
from app.services.feature_gate import feature_gate, TierLimits, SubscriptionTier
from app.schemas.subscription import (
    SubscriptionResponse,
    SubscriptionUpdateRequest,
    UsageResponse,
    TierComparisonResponse,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get current organization subscription details"""
    subscription = await feature_gate.get_organization_subscription(db, str(user.org_id))
    
    # Get usage information
    usage_info = {}
    for limit_type in ["providers", "members", "gateway_calls_per_month"]:
        usage = await feature_gate.check_usage_limit(db, str(user.org_id), limit_type)
        usage_info[limit_type] = usage
    
    # Get tier limits
    tier_config = TierLimits.get_tier_config(subscription["tier"])
    
    return SubscriptionResponse(
        tier=subscription["tier"].value,
        status=subscription["status"].value,
        bonobot_plan=subscription["bonobot_plan"].value,
        bonobot_agent_limit=subscription["bonobot_agent_limit"],
        tier_limits=tier_config,
        usage=usage_info
    )


@router.get("/usage", response_model=UsageResponse)
async def get_usage_details(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get detailed usage information for current organization"""
    usage_info = {}
    for limit_type in ["providers", "members", "gateway_calls_per_month"]:
        usage = await feature_gate.check_usage_limit(db, str(user.org_id), limit_type)
        usage_info[limit_type] = usage
    
    return UsageResponse(usage=usage_info)


@router.get("/tiers", response_model=TierComparisonResponse)
async def get_tier_comparison(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get comparison of all subscription tiers"""
    subscription = await feature_gate.get_organization_subscription(
        db, str(user.org_id)
    )
    
    tiers = await feature_gate.get_tier_comparison(subscription["tier"])
    
    return TierComparisonResponse(
        current_tier=subscription["tier"].value,
        tiers=tiers
    )


@router.post("/update", response_model=SubscriptionResponse)
async def update_subscription(
    request: SubscriptionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
):
    """Update subscription tier (platform admin only)"""
    
    # Get organization
    stmt = select(Organization).where(Organization.id == request.org_id)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Store current values for history
    current_tier = org.subscription_tier
    current_status = org.subscription_status
    current_bonobot_plan = org.bonobot_plan
    current_bonobot_limit = org.bonobot_agent_limit
    
    # Update organization
    if request.tier:
        org.subscription_tier = request.tier
    if request.status:
        org.subscription_status = request.status
    if request.bonobot_plan is not None:
        org.bonobot_plan = request.bonobot_plan
    if request.bonobot_agent_limit is not None:
        org.bonobot_agent_limit = request.bonobot_agent_limit
    
    org.subscription_updated_at = datetime.utcnow()
    
    # Create history record
    history = SubscriptionHistory(
        org_id=request.org_id,
        previous_tier=current_tier,
        new_tier=org.subscription_tier,
        previous_status=current_status,
        new_status=org.subscription_status,
        previous_bonobot_plan=current_bonobot_plan,
        new_bonobot_plan=org.bonobot_plan,
        previous_bonobot_agent_limit=current_bonobot_limit,
        new_bonobot_agent_limit=org.bonobot_agent_limit,
        changed_by_user_id=admin_user.id,
        reason=request.reason,
        notes=request.notes,
    )
    
    db.add(history)
    await db.commit()
    await db.refresh(org)
    
    # Return updated subscription info
    subscription = await feature_gate.get_organization_subscription(db, str(org.id))
    tier_config = TierLimits.get_tier_config(subscription["tier"])
    
    return SubscriptionResponse(
        tier=subscription["tier"].value,
        status=subscription["status"].value,
        bonobot_plan=subscription["bonobot_plan"].value,
        bonobot_agent_limit=subscription["bonobot_agent_limit"],
        tier_limits=tier_config,
        usage={}  # Empty usage for admin update response
    )


@router.get("/history")
async def get_subscription_history(
    org_id: str = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get subscription history for organization (admins can specify org_id)"""
    
    # If org_id is specified, require superadmin
    target_org_id = org_id or str(user.org_id)
    if org_id and org_id != str(user.org_id):
        # Check if user is superadmin
        from app.core.config import settings
        admin_emails = [e.strip() for e in settings.admin_emails.split(",") if e.strip()]
        if user.email not in admin_emails:
            raise HTTPException(status_code=403, detail="Platform admin access required")
    
    stmt = (
        select(SubscriptionHistory)
        .where(SubscriptionHistory.org_id == target_org_id)
        .order_by(SubscriptionHistory.created_at.desc())
    )
    result = await db.execute(stmt)
    history_records = result.scalars().all()
    
    return [
        {
            "id": str(record.id),
            "previous_tier": record.previous_tier,
            "new_tier": record.new_tier,
            "previous_status": record.previous_status,
            "new_status": record.new_status,
            "previous_bonobot_plan": record.previous_bonobot_plan,
            "new_bonobot_plan": record.new_bonobot_plan,
            "previous_bonobot_agent_limit": record.previous_bonobot_agent_limit,
            "new_bonobot_agent_limit": record.new_bonobot_agent_limit,
            "changed_by_user_id": str(record.changed_by_user_id) if record.changed_by_user_id else None,
            "reason": record.reason,
            "notes": record.notes,
            "created_at": record.created_at,
        }
        for record in history_records
    ]


@router.get("/features")
async def check_feature_access(
    feature: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Check if current organization has access to a specific feature"""
    has_access = await feature_gate.check_feature_access(db, str(user.org_id), feature)
    
    subscription = await feature_gate.get_organization_subscription(db, str(user.org_id))
    required_tier = TierLimits.get_required_tier_for_feature(feature)
    
    return {
        "feature": feature,
        "has_access": has_access,
        "current_tier": subscription["tier"].value,
        "required_tier": required_tier.value if required_tier else None,
        "upgrade_url": "https://getbonito.com/pricing" if not has_access else None,
    }