import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis

from app.core.redis import get_redis
from app.core.database import get_db
from app.core.vault import vault_client

router = APIRouter()


async def check_database(db: AsyncSession) -> dict:
    """Check database connectivity."""
    try:
        result = await db.execute(text("SELECT 1"))
        result.fetchone()
        return {"status": "healthy", "latency_ms": 0}  # Could add timing
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_redis(redis_client: redis.Redis) -> dict:
    """Check Redis connectivity."""
    try:
        await redis_client.ping()
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_vault() -> dict:
    """Check Vault connectivity."""
    try:
        result = await vault_client.health_check()
        return result
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@router.get("/health")
async def health_check_basic():
    """Simple health check - just return alive status."""
    return {"status": "alive", "service": "bonito-api"}


@router.get("/health/live")
async def health_check_liveness():
    """Kubernetes liveness probe - just check if the service is running."""
    return {"status": "alive", "service": "bonito-api", "timestamp": asyncio.get_event_loop().time()}


@router.get("/health/ready")
async def health_check_readiness(
    redis_client: redis.Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db)
):
    """
    Kubernetes readiness probe - check if service is ready to accept traffic.
    Includes dependencies: database, Redis, and Vault.
    """
    # Run all checks concurrently
    db_check_task = asyncio.create_task(check_database(db))
    redis_check_task = asyncio.create_task(check_redis(redis_client))
    vault_check_task = asyncio.create_task(check_vault())
    
    try:
        db_status, redis_status, vault_status = await asyncio.gather(
            db_check_task,
            redis_check_task,
            vault_check_task,
            return_exceptions=True
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {e}")
    
    # Handle any exceptions from the checks
    if isinstance(db_status, Exception):
        db_status = {"status": "unhealthy", "error": str(db_status)}
    if isinstance(redis_status, Exception):
        redis_status = {"status": "unhealthy", "error": str(redis_status)}
    if isinstance(vault_status, Exception):
        vault_status = {"status": "unhealthy", "error": str(vault_status)}
    
    # Determine overall health
    all_healthy = all(
        check.get("status") == "healthy" 
        for check in [db_status, redis_status, vault_status]
    )
    
    response = {
        "status": "healthy" if all_healthy else "degraded",
        "service": "bonito-api",
        "dependencies": {
            "database": db_status,
            "redis": redis_status,
            "vault": vault_status,
        }
    }
    
    # Return 503 if any critical dependency is down
    if not all_healthy:
        raise HTTPException(status_code=503, detail=response)
    
    return response