from fastapi import APIRouter, Depends
import redis.asyncio as redis

from app.core.redis import get_redis

router = APIRouter()


@router.get("/health")
async def health_check(redis_client: redis.Redis = Depends(get_redis)):
    redis_ok = False
    try:
        await redis_client.ping()
        redis_ok = True
    except Exception:
        pass

    return {
        "status": "healthy",
        "redis": "connected" if redis_ok else "disconnected",
    }
