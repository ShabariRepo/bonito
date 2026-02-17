import redis.asyncio as redis
from typing import Optional

from app.core.config import settings

# Global Redis client reference (now backed by a connection pool)
redis_client: Optional[redis.Redis] = None
_pool: Optional[redis.ConnectionPool] = None


async def init_redis() -> redis.Redis:
    """Initialize Redis with a connection pool for concurrent access.

    max_connections controls how many simultaneous Redis operations
    can run without queuing.  20 is generous for rate-limit checks
    and cache ops under moderate load.
    """
    global redis_client, _pool
    if redis_client is None:
        _pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=settings.redis_max_connections,
        )
        redis_client = redis.Redis(connection_pool=_pool)
    return redis_client


async def close_redis():
    """Close Redis connection pool."""
    global redis_client, _pool
    if redis_client:
        await redis_client.close()
        redis_client = None
    if _pool:
        await _pool.disconnect()
        _pool = None


async def get_redis() -> redis.Redis:
    """Get Redis client instance."""
    if redis_client is None:
        return await init_redis()
    return redis_client