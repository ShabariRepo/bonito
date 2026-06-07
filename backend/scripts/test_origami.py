#!/usr/bin/env python3
"""Standalone Origami orchestrator smoke test.

Calls run_origami_turn against the local database with a real Anthropic key
and prints the SSE events as they're emitted. Lets you sanity-check the
orchestrator + tools without standing up the full FastAPI server.

Usage:
    export ORIGAMI_ANTHROPIC_KEY=sk-ant-...
    cd backend
    python scripts/test_origami.py "what providers do I have connected?"

Optional:
    --email <user_email>   pick a specific user (default: first user in DB)
    --org-id <uuid>        pick a specific org (default: that user's org)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Make sure backend/ is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


async def get_test_user(db: AsyncSession, email: str | None):
    """Find a user to attribute the test turn to. Default: first user."""
    from app.models.user import User

    if email:
        result = await db.execute(select(User).where(User.email == email))
    else:
        result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        raise SystemExit(
            "No users in DB. Create one with /api/auth/register first, or pass --email."
        )
    return user


async def run(message: str, email: str | None):
    if not os.getenv("ORIGAMI_GATEWAY_KEY"):
        raise SystemExit(
            "Set ORIGAMI_GATEWAY_KEY env var first (bn-... — a Bonito gateway key).\n"
            "Get one from Settings → Gateway Keys in any active org."
        )

    # Lazy import so SystemExit above triggers cleanly
    from app.core.config import settings
    from app.services.origami.orchestrator import run_origami_turn

    db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(db_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with Session() as db:
        user = await get_test_user(db, email)
        print(f"┌── Origami test ──────────────────────────────")
        print(f"│ User: {user.email}  org_id: {user.org_id}")
        print(f"│ Message: {message!r}")
        print(f"└──────────────────────────────────────────────")
        print()

        async for event in run_origami_turn(
            user=user,
            message=message,
            conversation_id=None,
            db=db,
        ):
            ts = f"\033[2m{event.type:>20}\033[0m"
            color = {
                "turn_started": "\033[34m",  # blue
                "message_complete": "\033[36m",  # cyan
                "tool_started": "\033[33m",  # yellow
                "tool_completed": "\033[32m",  # green
                "tool_failed": "\033[31m",  # red
                "done": "\033[35m",  # magenta
                "error": "\033[91m",  # bright red
            }.get(event.type, "")
            reset = "\033[0m" if color else ""

            payload = json.dumps(event.payload, indent=2) if event.payload else ""
            print(f"{color}{ts}{reset}  {payload}")

    await engine.dispose()


def main():
    p = argparse.ArgumentParser(description="Origami orchestrator smoke test")
    p.add_argument("message", help="user message to send to Origami")
    p.add_argument("--email", help="user email (default: first user in DB)")
    args = p.parse_args()
    asyncio.run(run(args.message, args.email))


if __name__ == "__main__":
    main()
