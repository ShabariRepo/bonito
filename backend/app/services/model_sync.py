"""Background model sync — periodically refreshes model catalogs from provider APIs.

Runs every 24 hours, syncing models for all active providers across all orgs.
This ensures new models (e.g. Claude Sonnet 4, new Groq models) appear
automatically without requiring users to manually resync.

Uses a PostgreSQL advisory lock so only one worker runs the sync at a time
(uvicorn spawns multiple workers, each with its own lifespan).
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session

logger = logging.getLogger(__name__)

SYNC_INTERVAL_SECONDS = 24 * 60 * 60  # 24 hours
# Advisory lock ID — arbitrary unique int64 for model sync
_ADVISORY_LOCK_ID = 839271  # "model_sync" hash

_task: asyncio.Task | None = None


async def _sync_all_providers():
    """Sync models for every active provider across all orgs.

    Uses pg_try_advisory_lock to ensure only one worker runs at a time.
    """
    from app.models.cloud_provider import CloudProvider
    from app.api.routes.models import sync_provider_models

    async with async_session() as db:
        # Try to acquire advisory lock — returns False if another worker holds it
        lock_result = await db.execute(
            text(f"SELECT pg_try_advisory_lock({_ADVISORY_LOCK_ID})")
        )
        acquired = lock_result.scalar()
        if not acquired:
            logger.debug("[MODEL SYNC] Skipping — another worker is already syncing")
            return

        try:
            result = await db.execute(
                select(CloudProvider).where(CloudProvider.status == "active")
            )
            providers = result.scalars().all()

            if not providers:
                logger.info("[MODEL SYNC] No active providers to sync")
                return

            total_synced = 0
            errors = []

            for p in providers:
                try:
                    async with db.begin_nested():
                        sync_result = await sync_provider_models(p, db)
                        count = sync_result["count"] if isinstance(sync_result, dict) else sync_result
                        total_synced += count
                        if isinstance(sync_result, dict) and sync_result.get("error"):
                            errors.append(f"{p.provider_type}: {sync_result['error']}")
                except Exception as e:
                    errors.append(f"{p.provider_type} ({p.id}): {e}")
                    logger.warning(f"[MODEL SYNC] Failed for {p.provider_type} (provider={p.id} org={p.org_id}): {e}")

            await db.commit()

            now = datetime.now(timezone.utc).isoformat()
            logger.info(
                f"[MODEL SYNC] Completed at {now}: "
                f"{len(providers)} providers, {total_synced} models synced"
                + (f", {len(errors)} errors" if errors else "")
            )
        finally:
            # Release advisory lock
            await db.execute(
                text(f"SELECT pg_advisory_unlock({_ADVISORY_LOCK_ID})")
            )


async def _run_loop():
    """Background loop — waits for interval, then syncs."""
    # Wait 60s after startup before first sync to let everything initialize
    await asyncio.sleep(60)

    while True:
        try:
            await _sync_all_providers()
        except Exception as e:
            logger.exception(f"[MODEL SYNC] Unexpected error: {e}")

        await asyncio.sleep(SYNC_INTERVAL_SECONDS)


async def start_model_sync():
    """Start the background model sync task."""
    global _task
    if _task is not None:
        return
    _task = asyncio.create_task(_run_loop())
    logger.info("[MODEL SYNC] Background sync started (every 24h)")


async def stop_model_sync():
    """Stop the background model sync task."""
    global _task
    if _task is not None:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None
        logger.info("[MODEL SYNC] Background sync stopped")
