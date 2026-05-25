"""Agent overflow queue — holds rate-limited requests and drains them when capacity frees up.

When an agent execute request hits a 429 rate limit (even after HPA autoscaling),
instead of dropping the request, the queue:
1. Stores the request payload in Redis
2. Returns a queue ticket (202 Accepted)
3. Background drainer processes queued requests at a safe rate
4. Results are stored in Redis for polling

Redis keys:
    agent_queue:{agent_id}              — LIST of ticket_ids (FIFO)
    agent_queue_req:{ticket_id}         — HASH: message, agent_id, org_id, user_id, status, ...
    agent_queue_result:{ticket_id}      — HASH: content, tokens, cost, etc. (set when complete)
"""

import asyncio
import json
import logging
import time
import uuid as uuid_lib
from typing import Optional

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# ─── Config ───
QUEUE_MAX_DEPTH = 500          # Max queued items per agent
QUEUE_RESULT_TTL = 3600        # Results kept for 1 hour
QUEUE_REQUEST_TTL = 3600       # Request metadata TTL
DRAIN_INTERVAL = 2.0           # Seconds between drain attempts
DRAIN_BATCH_SIZE = 3           # Requests to dequeue per drain cycle

# Background task handle
_task: Optional[asyncio.Task] = None


async def enqueue_request(
    agent_id: uuid_lib.UUID,
    org_id: uuid_lib.UUID,
    user_id: uuid_lib.UUID,
    message: str,
    session_id: Optional[uuid_lib.UUID],
    parent_agent_id: Optional[uuid_lib.UUID],
    redis: Redis,
) -> dict:
    """Enqueue a rate-limited request. Returns ticket info."""
    ticket_id = str(uuid_lib.uuid4())
    queue_key = f"agent_queue:{agent_id}"
    req_key = f"agent_queue_req:{ticket_id}"

    # Check queue depth
    depth = await redis.llen(queue_key)
    if depth >= QUEUE_MAX_DEPTH:
        return {
            "queued": False,
            "error": f"Queue full ({depth}/{QUEUE_MAX_DEPTH}). Try again later.",
        }

    # Store request metadata
    req_data = {
        "ticket_id": ticket_id,
        "agent_id": str(agent_id),
        "org_id": str(org_id),
        "user_id": str(user_id),
        "message": message,
        "session_id": str(session_id) if session_id else "",
        "parent_agent_id": str(parent_agent_id) if parent_agent_id else "",
        "status": "queued",
        "queued_at": str(time.time()),
        "position": depth + 1,
    }
    pipeline = redis.pipeline()
    pipeline.hset(req_key, mapping=req_data)
    pipeline.expire(req_key, QUEUE_REQUEST_TTL)
    pipeline.rpush(queue_key, ticket_id)
    await pipeline.execute()

    logger.info(f"Queued request {ticket_id} for agent {agent_id} (position {depth + 1})")

    return {
        "queued": True,
        "ticket_id": ticket_id,
        "position": depth + 1,
        "estimated_wait_seconds": (depth + 1) * DRAIN_INTERVAL,
    }


async def get_queue_status(
    ticket_id: str,
    redis: Redis,
) -> dict:
    """Get status of a queued request."""
    req_key = f"agent_queue_req:{ticket_id}"
    result_key = f"agent_queue_result:{ticket_id}"

    req_data = await redis.hgetall(req_key)
    if not req_data:
        return {"status": "not_found", "ticket_id": ticket_id}

    status = req_data.get("status", "unknown")

    if status == "completed":
        # Fetch result
        result_data = await redis.hgetall(result_key)
        return {
            "status": "completed",
            "ticket_id": ticket_id,
            "result": {
                "content": result_data.get("content", ""),
                "tokens": int(result_data.get("tokens", 0)),
                "cost": result_data.get("cost", "0"),
                "turns": int(result_data.get("turns", 0)),
                "model_used": result_data.get("model_used", ""),
                "effective_rpm": int(result_data.get("effective_rpm", 0)) or None,
                "scaling_active": result_data.get("scaling_active", "false") == "true",
            },
        }
    elif status == "failed":
        return {
            "status": "failed",
            "ticket_id": ticket_id,
            "error": req_data.get("error", "Unknown error"),
        }
    else:
        # Still queued or processing
        agent_id = req_data.get("agent_id", "")
        queue_key = f"agent_queue:{agent_id}"
        # Approximate position
        queue_items = await redis.lrange(queue_key, 0, -1)
        try:
            position = queue_items.index(ticket_id) + 1
        except ValueError:
            position = 0  # Being processed or already done
        return {
            "status": status,
            "ticket_id": ticket_id,
            "position": position,
            "estimated_wait_seconds": position * DRAIN_INTERVAL if position else 0,
        }


async def get_agent_queue_depth(agent_id: uuid_lib.UUID, redis: Redis) -> int:
    """Get current queue depth for an agent."""
    return await redis.llen(f"agent_queue:{agent_id}")


async def _drain_agent_queue(agent_id_str: str, redis: Redis):
    """Process queued requests for a single agent."""
    from app.core.database import get_db_session
    from app.models.agent import Agent
    from app.models.user import User
    from sqlalchemy import select

    queue_key = f"agent_queue:{agent_id_str}"
    agent_id = uuid_lib.UUID(agent_id_str)

    processed = 0
    for _ in range(DRAIN_BATCH_SIZE):
        # Pop from front of queue (FIFO)
        ticket_id = await redis.lpop(queue_key)
        if not ticket_id:
            break

        req_key = f"agent_queue_req:{ticket_id}"
        req_data = await redis.hgetall(req_key)
        if not req_data:
            continue

        # Mark as processing
        await redis.hset(req_key, "status", "processing")

        try:
            async with get_db_session() as db:
                # Load agent
                result = await db.execute(select(Agent).where(Agent.id == agent_id))
                agent = result.scalar_one_or_none()
                if not agent:
                    await redis.hset(req_key, mapping={"status": "failed", "error": "Agent not found"})
                    continue

                # Execute via agent engine
                from app.services.agent_engine import AgentEngine
                agent_engine = AgentEngine()
                user_id_str = req_data.get("user_id", "")
                session_id_str = req_data.get("session_id", "")

                run_result = await agent_engine.execute(
                    agent=agent,
                    message=req_data["message"],
                    db=db,
                    redis=redis,
                    session_id=uuid_lib.UUID(session_id_str) if session_id_str else None,
                    user_id=uuid_lib.UUID(user_id_str) if user_id_str else None,
                )

                # Store result
                result_key = f"agent_queue_result:{ticket_id}"
                result_data = {
                    "content": run_result.content or "",
                    "tokens": str(run_result.tokens),
                    "cost": str(run_result.cost),
                    "turns": str(run_result.turns),
                    "model_used": run_result.model_used or "",
                    "effective_rpm": str(run_result.security.effective_rpm or 0),
                    "scaling_active": "true" if run_result.security.scaling_active else "false",
                }
                pipeline = redis.pipeline()
                pipeline.hset(result_key, mapping=result_data)
                pipeline.expire(result_key, QUEUE_RESULT_TTL)
                pipeline.hset(req_key, "status", "completed")
                await pipeline.execute()

                processed += 1
                logger.info(f"Queue drain: completed {ticket_id} for agent {agent_id_str}")

        except Exception as e:
            from app.services.agent_engine import AgentRateLimitError
            err_msg = str(e)[:500]
            is_rate_limit = isinstance(e, AgentRateLimitError) or "429" in err_msg or "rate limit" in err_msg.lower()
            if is_rate_limit:
                # Put it back at the front of the queue — not ready yet
                await redis.lpush(queue_key, ticket_id)
                await redis.hset(req_key, "status", "queued")
                logger.debug(f"Queue drain: re-queued {ticket_id} (still rate limited)")
                break  # Stop draining this agent — it's at capacity
            else:
                await redis.hset(req_key, mapping={"status": "failed", "error": err_msg})
                logger.error(f"Queue drain failed for {ticket_id}: {err_msg}")

    return processed


async def _drain_loop():
    """Background loop that drains all agent queues."""
    from app.core.redis import get_redis

    logger.info("Agent queue drainer started")

    while True:
        try:
            await asyncio.sleep(DRAIN_INTERVAL)

            redis = await get_redis()

            # Find all agent queues with pending items
            # Scan for agent_queue:* keys
            queue_keys = []
            async for key in redis.scan_iter(match="agent_queue:*", count=100):
                # Filter out req/result keys
                if "req" not in key and "result" not in key:
                    queue_keys.append(key)

            for queue_key in queue_keys:
                depth = await redis.llen(queue_key)
                if depth == 0:
                    continue

                # Extract agent_id from key
                agent_id_str = queue_key.replace("agent_queue:", "")
                try:
                    await _drain_agent_queue(agent_id_str, redis)
                except Exception as e:
                    logger.error(f"Queue drain error for {agent_id_str}: {e}")

        except asyncio.CancelledError:
            logger.info("Agent queue drainer stopping")
            return
        except Exception as e:
            logger.error(f"Queue drain loop error: {e}")
            await asyncio.sleep(5)


async def start_queue_drainer():
    """Start the background queue drainer."""
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_drain_loop())
        logger.info("Agent queue drainer task created")


async def stop_queue_drainer():
    """Stop the background queue drainer."""
    global _task
    if _task and not _task.done():
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        logger.info("Agent queue drainer stopped")
    _task = None
