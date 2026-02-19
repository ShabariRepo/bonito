"""
Usage Tracking Service - Track subscription tier usage limits
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.core.redis import redis_client
from app.services.feature_gate import feature_gate
from app.models.organization import Organization
from app.models.gateway import GatewayRequest
from app.models.user import User

logger = logging.getLogger(__name__)


class UsageTracker:
    """Service for tracking usage across various resources"""
    
    def __init__(self, redis_client=None):
        self.redis = redis_client or redis_client
        
    async def track_gateway_request(self, db: AsyncSession, org_id: str):
        """Track a gateway API request for an organization"""
        
        # Check if organization is at limit
        try:
            await feature_gate.require_usage_limit(db, org_id, "gateway_calls_per_month")
        except Exception as e:
            logger.warning(f"Gateway request blocked for org {org_id}: {e}")
            raise
        
        # Increment usage counter in Redis
        await feature_gate.increment_usage_counter(org_id, "gateway_calls", 1)
        
        # Log the usage
        logger.info(f"Gateway request tracked for org {org_id}")
    
    async def track_provider_addition(self, db: AsyncSession, org_id: str):
        """Track adding a new provider"""
        
        # Check if organization can add more providers
        try:
            await feature_gate.require_usage_limit(db, org_id, "providers")
        except Exception as e:
            logger.warning(f"Provider addition blocked for org {org_id}: {e}")
            raise
        
        logger.info(f"Provider addition allowed for org {org_id}")
    
    async def track_member_addition(self, db: AsyncSession, org_id: str):
        """Track adding a new team member"""
        
        # Check if organization can add more members
        try:
            await feature_gate.require_usage_limit(db, org_id, "members")
        except Exception as e:
            logger.warning(f"Member addition blocked for org {org_id}: {e}")
            raise
        
        logger.info(f"Member addition allowed for org {org_id}")
    
    async def get_usage_summary(self, db: AsyncSession, org_id: str) -> dict:
        """Get complete usage summary for an organization"""
        
        usage_summary = {}
        
        # Check all limit types
        for limit_type in ["providers", "members", "gateway_calls_per_month"]:
            usage_info = await feature_gate.check_usage_limit(db, org_id, limit_type)
            usage_summary[limit_type] = {
                "current": usage_info["current"],
                "limit": usage_info["limit"] if usage_info["limit"] != float('inf') else "unlimited",
                "remaining": usage_info["remaining"] if usage_info["remaining"] != float('inf') else "unlimited",
                "at_limit": usage_info["at_limit"],
                "percentage": (usage_info["current"] / usage_info["limit"]) * 100 
                             if usage_info["limit"] != float('inf') and usage_info["limit"] > 0 
                             else 0
            }
        
        return usage_summary
    
    async def check_approaching_limits(self, db: AsyncSession, org_id: str, threshold: float = 0.8) -> dict:
        """Check if organization is approaching any usage limits"""
        
        approaching_limits = {}
        usage_summary = await self.get_usage_summary(db, org_id)
        
        for limit_type, usage_info in usage_summary.items():
            if (usage_info["limit"] != "unlimited" and 
                usage_info["percentage"] >= threshold * 100):
                approaching_limits[limit_type] = {
                    "current": usage_info["current"],
                    "limit": usage_info["limit"],
                    "percentage": usage_info["percentage"]
                }
        
        return approaching_limits
    
    async def reset_monthly_counters(self, org_id: str):
        """Reset monthly usage counters (called by cron job)"""
        now = datetime.utcnow()
        cache_key = f"gateway_calls:{org_id}:{now.strftime('%Y-%m')}"
        
        try:
            await self.redis.delete(cache_key)
            logger.info(f"Reset monthly counters for org {org_id}")
        except Exception as e:
            logger.warning(f"Failed to reset monthly counters for org {org_id}: {e}")


# Create global instance
usage_tracker = UsageTracker()