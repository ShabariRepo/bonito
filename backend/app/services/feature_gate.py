"""
Feature Gate Service - Subscription tier system with feature gating
"""
import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Union
import logging

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract
import redis.asyncio as redis

from app.core.database import get_db
from app.core.redis import redis_client
from app.models.organization import Organization
from app.models.user import User
from app.models.cloud_provider import CloudProvider
from app.models.gateway import GatewayRequest

logger = logging.getLogger(__name__)


class SubscriptionTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    TRIAL = "trial"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class BonobotPlan(str, Enum):
    NONE = "none"
    HOSTED = "hosted"
    VPC = "vpc"


class FeatureAccessException(HTTPException):
    """Custom exception for feature access denials"""
    def __init__(self, message: str, required_tier: str):
        detail = {
            "message": message,
            "required_tier": required_tier,
            "upgrade_url": "https://getbonito.com/pricing"
        }
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class TierLimits:
    """Define limits and features for each subscription tier"""
    
    TIER_CONFIG = {
        SubscriptionTier.FREE: {
            "providers": 1,
            "gateway_calls_per_month": 100,
            "members": 1,
            "features": {
                "models": True,
                "playground": True,
                "routing": False,
                "ai_context": False,
                "analytics": False,
                "cli": False,
                "audit": False,
                "notifications": False,
                "budget_alerts": False,
                "sso": False,
                "rbac": False,
                "iac_templates": False,
                "compliance": False,
                "on_premise": False,
                "custom_integrations": False,
                "dedicated_support": False,
            }
        },
        SubscriptionTier.PRO: {
            "providers": 3,
            "gateway_calls_per_month": 50000,
            "members": float('inf'),  # unlimited
            "features": {
                "models": True,
                "playground": True,
                "routing": True,
                "ai_context": True,
                "analytics": True,
                "cli": True,
                "audit": True,
                "notifications": True,
                "budget_alerts": True,
                "sso": False,
                "rbac": False,
                "iac_templates": False,
                "compliance": False,
                "on_premise": False,
                "custom_integrations": False,
                "dedicated_support": False,
            }
        },
        SubscriptionTier.ENTERPRISE: {
            "providers": float('inf'),  # unlimited
            "gateway_calls_per_month": float('inf'),  # unlimited
            "members": float('inf'),  # unlimited
            "features": {
                "models": True,
                "playground": True,
                "routing": True,
                "ai_context": True,
                "analytics": True,
                "cli": True,
                "audit": True,
                "notifications": True,
                "budget_alerts": True,
                "sso": True,
                "rbac": True,
                "iac_templates": True,
                "compliance": True,
                "on_premise": True,
                "custom_integrations": True,
                "dedicated_support": True,
            }
        }
    }

    @classmethod
    def get_tier_config(cls, tier: SubscriptionTier) -> Dict[str, Any]:
        return cls.TIER_CONFIG.get(tier, cls.TIER_CONFIG[SubscriptionTier.FREE])

    @classmethod
    def get_feature_access(cls, tier: SubscriptionTier, feature: str) -> bool:
        config = cls.get_tier_config(tier)
        return config["features"].get(feature, False)

    @classmethod
    def get_limit(cls, tier: SubscriptionTier, limit_type: str) -> Union[int, float]:
        config = cls.get_tier_config(tier)
        return config.get(limit_type, 0)

    @classmethod
    def get_required_tier_for_feature(cls, feature: str) -> Optional[SubscriptionTier]:
        """Get the minimum tier required for a feature"""
        for tier in [SubscriptionTier.FREE, SubscriptionTier.PRO, SubscriptionTier.ENTERPRISE]:
            if cls.get_feature_access(tier, feature):
                return tier
        return None


class FeatureGateService:
    """Service for checking subscription tier permissions and usage limits"""
    
    def __init__(self, redis_client=None):
        self.redis = redis_client or redis_client
    
    async def get_organization_subscription(self, db: AsyncSession, org_id: str) -> Dict[str, Any]:
        """Get organization subscription details"""
        stmt = select(Organization).where(Organization.id == org_id)
        result = await db.execute(stmt)
        org = result.scalar_one_or_none()
        
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        return {
            "tier": SubscriptionTier(org.subscription_tier),
            "status": SubscriptionStatus(org.subscription_status),
            "bonobot_plan": BonobotPlan(org.bonobot_plan),
            "bonobot_agent_limit": org.bonobot_agent_limit,
        }
    
    async def check_feature_access(self, db: AsyncSession, org_id: str, feature: str) -> bool:
        """Check if organization has access to a specific feature"""
        subscription = await self.get_organization_subscription(db, org_id)
        
        # Check if subscription is active
        if subscription["status"] != SubscriptionStatus.ACTIVE:
            return False
        
        tier = subscription["tier"]
        return TierLimits.get_feature_access(tier, feature)
    
    async def require_feature(self, db: AsyncSession, org_id: str, feature: str):
        """Require access to a feature, raise exception if not available"""
        if not await self.check_feature_access(db, org_id, feature):
            subscription = await self.get_organization_subscription(db, org_id)
            tier = subscription["tier"]
            required_tier = TierLimits.get_required_tier_for_feature(feature)
            
            if required_tier:
                tier_names = {
                    SubscriptionTier.FREE: "Free",
                    SubscriptionTier.PRO: "Pro", 
                    SubscriptionTier.ENTERPRISE: "Enterprise"
                }
                
                if required_tier == SubscriptionTier.PRO:
                    message = f"This feature requires a Pro or Enterprise plan. Upgrade at getbonito.com/pricing"
                elif required_tier == SubscriptionTier.ENTERPRISE:
                    message = f"This feature requires an Enterprise plan. Upgrade at getbonito.com/pricing"
                else:
                    message = f"This feature is not available on your current plan."
                
                raise FeatureAccessException(message, required_tier.value)
            else:
                raise FeatureAccessException("This feature is not available.", "enterprise")
    
    async def check_usage_limit(self, db: AsyncSession, org_id: str, limit_type: str) -> Dict[str, Any]:
        """Check usage against tier limits"""
        subscription = await self.get_organization_subscription(db, org_id)
        tier = subscription["tier"]
        limit = TierLimits.get_limit(tier, limit_type)
        
        # Get current usage
        current_usage = await self._get_current_usage(db, org_id, limit_type)
        
        return {
            "limit": limit,
            "current": current_usage,
            "remaining": max(0, limit - current_usage) if limit != float('inf') else float('inf'),
            "at_limit": current_usage >= limit if limit != float('inf') else False,
        }
    
    async def require_usage_limit(self, db: AsyncSession, org_id: str, limit_type: str):
        """Check usage limit and raise exception if at limit"""
        usage_info = await self.check_usage_limit(db, org_id, limit_type)
        
        if usage_info["at_limit"]:
            subscription = await self.get_organization_subscription(db, org_id)
            tier = subscription["tier"]
            
            limit_messages = {
                "providers": f"You've reached the limit of {usage_info['limit']} provider(s) for your {tier.value} plan.",
                "gateway_calls_per_month": f"You've reached the monthly limit of {usage_info['limit']} gateway calls for your {tier.value} plan.",
                "members": f"You've reached the limit of {usage_info['limit']} team member(s) for your {tier.value} plan."
            }
            
            message = limit_messages.get(limit_type, f"Usage limit exceeded for {limit_type}")
            message += " Upgrade at getbonito.com/pricing for higher limits."
            
            raise FeatureAccessException(message, "pro" if tier == SubscriptionTier.FREE else "enterprise")
    
    async def _get_current_usage(self, db: AsyncSession, org_id: str, limit_type: str) -> int:
        """Get current usage for a specific limit type"""
        if limit_type == "providers":
            stmt = select(func.count(CloudProvider.id)).where(CloudProvider.org_id == org_id)
            result = await db.execute(stmt)
            return result.scalar() or 0
        
        elif limit_type == "members":
            stmt = select(func.count(User.id)).where(User.org_id == org_id)
            result = await db.execute(stmt)
            return result.scalar() or 0
        
        elif limit_type == "gateway_calls_per_month":
            return await self._get_monthly_gateway_calls(db, org_id)
        
        return 0
    
    async def _get_monthly_gateway_calls(self, db: AsyncSession, org_id: str) -> int:
        """Get gateway calls for current month"""
        now = datetime.utcnow()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Try Redis cache first
        cache_key = f"gateway_calls:{org_id}:{start_of_month.strftime('%Y-%m')}"
        try:
            cached_count = await self.redis.get(cache_key)
            if cached_count:
                return int(cached_count)
        except Exception as e:
            logger.warning(f"Redis cache miss for gateway calls: {e}")
        
        # Fall back to database query
        stmt = select(func.count(GatewayRequest.id)).where(
            and_(
                GatewayRequest.org_id == org_id,
                GatewayRequest.created_at >= start_of_month,
                extract('month', GatewayRequest.created_at) == now.month,
                extract('year', GatewayRequest.created_at) == now.year
            )
        )
        result = await db.execute(stmt)
        count = result.scalar() or 0
        
        # Cache the result for 5 minutes
        try:
            await self.redis.setex(cache_key, 300, str(count))
        except Exception as e:
            logger.warning(f"Failed to cache gateway calls count: {e}")
        
        return count
    
    async def increment_usage_counter(self, org_id: str, usage_type: str, amount: int = 1):
        """Increment usage counter in Redis"""
        now = datetime.utcnow()
        cache_key = f"{usage_type}:{org_id}:{now.strftime('%Y-%m')}"
        
        try:
            await self.redis.incrby(cache_key, amount)
            # Set expiration to end of next month to handle month boundaries
            expire_time = (now.replace(day=1) + timedelta(days=32)).replace(day=1) + timedelta(days=31) - now
            await self.redis.expire(cache_key, int(expire_time.total_seconds()))
        except Exception as e:
            logger.warning(f"Failed to increment usage counter: {e}")
    
    async def get_tier_comparison(self, current_tier: SubscriptionTier) -> Dict[str, Any]:
        """Get comparison of features across tiers for upgrade messaging"""
        tiers = {}
        for tier in SubscriptionTier:
            config = TierLimits.get_tier_config(tier)
            tiers[tier.value] = {
                "providers": config["providers"],
                "gateway_calls": config["gateway_calls_per_month"],
                "members": config["members"],
                "features": config["features"]
            }
        return tiers


# Create a global instance
feature_gate = FeatureGateService()