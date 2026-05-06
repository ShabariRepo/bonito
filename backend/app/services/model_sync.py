"""Background model sync — periodically refreshes model catalogs from provider APIs.

Runs every 24 hours, syncing models for all active providers across all orgs.
This ensures new models (e.g. Claude Sonnet 4, new Groq models) appear
automatically without requiring users to manually resync.
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session

logger = logging.getLogger(__name__)

SYNC_INTERVAL_SECONDS = 24 * 60 * 60  # 24 hours

_task: asyncio.Task | None = None


async def _sync_all_providers():
    """Sync models for every active provider across all orgs."""
    from app.models.cloud_provider import CloudProvider
    from app.api.routes.models import sync_provider_models

    async with async_session() as db:
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
                logger.warning(f"[MODEL SYNC] Failed for {p.provider_type} ({p.id}): {e}")

        await db.commit()

        now = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"[MODEL SYNC] Completed at {now}: "
            f"{len(providers)} providers, {total_synced} models synced"
            + (f", {len(errors)} errors" if errors else "")
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
