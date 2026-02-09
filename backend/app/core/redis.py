import redis.asyncio as redis
from typing import Optional

from app.core.config import settings

# Global Redis client reference
redis_client: Optional[redis.Redis] = None


async def init_redis() -> redis.Redis:
    """Initialize Redis connection."""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return redis_client


async def close_redis():
    """Close Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


async def get_redis() -> redis.Redis:
    """Get Redis client instance."""
    if redis_client is None:
        return await init_redis()
    return redis_client