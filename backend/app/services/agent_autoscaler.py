"""Agent-level Horizontal Pod Autoscaling (HPA).

Dynamically adjusts an agent's effective rate_limit_rpm based on utilization.
Phase 1 ("virtual scaling"): raises the effective RPM in Redis — no replica agents.
Phase 2 ("replica"): creates clone agents and load-balances across them.

Scale-up is reactive (checked on every request in _check_rate_limit).
Scale-down runs in a background loop (30s interval, advisory-locked).
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone

from redis.asyncio import Redis
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session

logger = logging.getLogger(__name__)

# Background loop interval
_SCALE_CHECK_INTERVAL = 30  # seconds

# Advisory lock ID — unique int64, must not collide with model_sync (839271)
_ADVISORY_LOCK_ID = 839272

# Redis key prefixes
_EFFECTIVE_RPM_KEY = "agent_hpa:rpm:{agent_id}"
_SCALED_AT_KEY = "agent_hpa:scaled_at:{agent_id}"

# TTLs
_EFFECTIVE_RPM_TTL = 300  # 5 min — if no traffic, effective RPM expires back to base
_SCALED_AT_TTL = 600  # 10 min

# Defaults for autoscale_config
DEFAULT_CAPACITY_THRESHOLD = 0.6
DEFAULT_SCALE_DOWN_THRESHOLD = 0.3
DEFAULT_SCALE_DOWN_COOLDOWN = 300  # 5 minutes
DEFAULT_MAX_REPLICAS = 5  # effective RPM cap = max_replicas * base_rpm

_task: asyncio.Task | None = None


def _get_config(agent) -> dict:
    """Extract autoscale config with defaults."""
    cfg = agent.autoscale_config or {}
    return {
        "capacity_threshold": cfg.get("capacity_threshold", DEFAULT_CAPACITY_THRESHOLD),
        "scale_down_threshold": cfg.get("scale_down_threshold", DEFAULT_SCALE_DOWN_THRESHOLD),
        "scale_down_cooldown_seconds": cfg.get("scale_down_cooldown_seconds", DEFAULT_SCALE_DOWN_COOLDOWN),
        "max_replicas": cfg.get("max_replicas", DEFAULT_MAX_REPLICAS),
        "mode": cfg.get("mode", "virtual"),
    }


async def get_effective_rpm(agent, redis: Redis) -> int:
    """Get the current effective RPM for an agent.

    Returns the scaled RPM from Redis if autoscaling is active,
    otherwise returns the agent's base rate_limit_rpm.
    """
    if not agent.autoscale_enabled:
        return agent.rate_limit_rpm

    key = _EFFECTIVE_RPM_KEY.format(agent_id=agent.id)
    value = await redis.get(key)
    if value is not None:
        return int(value)
    return agent.rate_limit_rpm


async def maybe_scale_up(agent, current_count: int, effective_rpm: int, redis: Redis) -> int:
    """Check if we need to scale up and do so if threshold is crossed.

    Called reactively on every request from _check_rate_limit.
    Returns the (possibly updated) effective RPM.
    """
    if not agent.autoscale_enabled:
        return effective_rpm

    cfg = _get_config(agent)
    utilization = current_count / effective_rpm if effective_rpm > 0 else 0

    if utilization < cfg["capacity_threshold"]:
        return effective_rpm

    # Calculate new RPM (double, capped)
    max_rpm = cfg["max_replicas"] * agent.rate_limit_rpm
    if effective_rpm >= max_rpm:
        return effective_rpm  # already at cap

    new_rpm = min(effective_rpm * 2, max_rpm)

    # Set in Redis
    rpm_key = _EFFECTIVE_RPM_KEY.format(agent_id=agent.id)
    scaled_key = _SCALED_AT_KEY.format(agent_id=agent.id)

    pipeline = redis.pipeline()
    pipeline.set(rpm_key, str(new_rpm), ex=_EFFECTIVE_RPM_TTL)
    pipeline.set(scaled_key, str(int(time.time())), ex=_SCALED_AT_TTL)
    await pipeline.execute()

    logger.info(
        f"[HPA] Scale UP agent {agent.id} ({agent.name}): "
        f"{effective_rpm} → {new_rpm} RPM (utilization={utilization:.0%})"
    )

    # Log event to DB (fire-and-forget — don't slow the request)
    asyncio.create_task(
        _log_scaling_event(
            agent_id=agent.id,
            org_id=agent.org_id,
            event_type="scale_up",
            previous_capacity=effective_rpm,
            new_capacity=new_rpm,
            utilization=utilization,
        )
    )

    return new_rpm


async def _log_scaling_event(
    agent_id: uuid.UUID,
    org_id: uuid.UUID,
    event_type: str,
    previous_capacity: int,
    new_capacity: int,
    utilization: float,
):
    """Write a scaling event to the DB. Runs as a background task."""
    try:
        from app.models.agent_scaling_event import AgentScalingEvent

        async with async_session() as db:
            event = AgentScalingEvent(
                id=uuid.uuid4(),
                agent_id=agent_id,
                org_id=org_id,
                event_type=event_type,
                previous_capacity=previous_capacity,
                new_capacity=new_capacity,
                replica_count=0,  # Phase 1: no replicas
                trigger_utilization=round(utilization, 4),
            )
            db.add(event)
            await db.commit()
    except Exception as e:
        logger.warning(f"[HPA] Failed to log scaling event: {e}")


async def _scale_down_check():
    """Check all autoscale-enabled agents and scale down if utilization is low.

    Uses advisory lock so only one worker runs at a time.
    """
    from app.models.agent import Agent

    async with async_session() as db:
        lock_result = await db.execute(
            text(f"SELECT pg_try_advisory_lock({_ADVISORY_LOCK_ID})")
        )
        acquired = lock_result.scalar()
        if not acquired:
            return

        try:
            from app.core.redis import get_redis
            redis = await get_redis()

            result = await db.execute(
                select(Agent).where(
                    Agent.autoscale_enabled == True,
                    Agent.status == "active",
                    Agent.primary_agent_id == None,  # only primary agents
                )
            )
            agents = result.scalars().all()

            current_minute = int(time.time() // 60)

            for agent in agents:
                cfg = _get_config(agent)

                rpm_key = _EFFECTIVE_RPM_KEY.format(agent_id=agent.id)
                effective_rpm_str = await redis.get(rpm_key)
                if effective_rpm_str is None:
                    continue  # not scaled up, nothing to do

                effective_rpm = int(effective_rpm_str)
                if effective_rpm <= agent.rate_limit_rpm:
                    # Already at base, clean up stale key
                    await redis.delete(rpm_key)
                    continue

                # Get current utilization
                rate_key = f"agent_rate:{agent.id}:{current_minute}"
                count_str = await redis.get(rate_key)
                current_count = int(count_str) if count_str else 0
                utilization = current_count / effective_rpm if effective_rpm > 0 else 0

                if utilization >= cfg["scale_down_threshold"]:
                    continue  # still busy

                # Check cooldown
                scaled_key = _SCALED_AT_KEY.format(agent_id=agent.id)
                scaled_at_str = await redis.get(scaled_key)
                if scaled_at_str:
                    elapsed = time.time() - int(scaled_at_str)
                    if elapsed < cfg["scale_down_cooldown_seconds"]:
                        continue  # still in cooldown

                # Scale down: halve the effective RPM
                new_rpm = max(agent.rate_limit_rpm, effective_rpm // 2)

                if new_rpm <= agent.rate_limit_rpm:
                    # Back to base — remove the key entirely
                    await redis.delete(rpm_key)
                    new_rpm = agent.rate_limit_rpm
                else:
                    await redis.set(rpm_key, str(new_rpm), ex=_EFFECTIVE_RPM_TTL)

                # Update the scaled_at timestamp for next cooldown window
                await redis.set(scaled_key, str(int(time.time())), ex=_SCALED_AT_TTL)

                logger.info(
                    f"[HPA] Scale DOWN agent {agent.id} ({agent.name}): "
                    f"{effective_rpm} → {new_rpm} RPM (utilization={utilization:.0%})"
                )

                await _log_scaling_event(
                    agent_id=agent.id,
                    org_id=agent.org_id,
                    event_type="scale_down",
                    previous_capacity=effective_rpm,
                    new_capacity=new_rpm,
                    utilization=utilization,
                )

        finally:
            await db.execute(
                text(f"SELECT pg_advisory_unlock({_ADVISORY_LOCK_ID})")
            )


async def _run_loop():
    """Background loop that checks for scale-down opportunities."""
    # Wait a bit on startup to let everything initialize
    await asyncio.sleep(10)

    while True:
        try:
            await _scale_down_check()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"[HPA] Scale-down check failed (non-fatal): {e}")

        await asyncio.sleep(_SCALE_CHECK_INTERVAL)


async def start_autoscaler():
    """Start the background autoscaler task."""
    global _task
    if _task is not None:
        return
    _task = asyncio.create_task(_run_loop())
    logger.info("[HPA] Agent autoscaler started (scale-down check every 30s)")


async def stop_autoscaler():
    """Stop the background autoscaler task."""
    global _task
    if _task is not None:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None
        logger.info("[HPA] Agent autoscaler stopped")


async def get_scaling_status(agent, redis: Redis) -> dict:
    """Get current scaling status for an agent (used by API endpoint)."""
    cfg = _get_config(agent)
    effective_rpm = await get_effective_rpm(agent, redis)
    scaling_active = effective_rpm > agent.rate_limit_rpm

    current_minute = int(time.time() // 60)
    rate_key = f"agent_rate:{agent.id}:{current_minute}"
    count_str = await redis.get(rate_key)
    current_count = int(count_str) if count_str else 0
    utilization = current_count / effective_rpm if effective_rpm > 0 else 0

    scaled_key = _SCALED_AT_KEY.format(agent_id=agent.id)
    scaled_at_str = await redis.get(scaled_key)
    last_scaled_at = datetime.fromtimestamp(int(scaled_at_str), tz=timezone.utc) if scaled_at_str else None

    return {
        "autoscale_enabled": agent.autoscale_enabled,
        "config": cfg,
        "base_rpm": agent.rate_limit_rpm,
        "effective_rpm": effective_rpm,
        "scaling_active": scaling_active,
        "current_rpm_usage": current_count,
        "utilization": round(utilization, 4),
        "last_scaled_at": last_scaled_at.isoformat() if last_scaled_at else None,
        "replica_count": 0,  # Phase 1: always 0
    }
