"""
One-off script to send product update emails to all verified users.

Usage:
  # Dry run (shows who would receive the email):
  python scripts/send_product_update.py --dry-run

  # Send for real:
  python scripts/send_product_update.py

  # Send to a single email first (test):
  python scripts/send_product_update.py --test-email shabari@bonito.ai

Requires: RESEND_API_KEY and DATABASE_URL env vars (or Vault configured).
"""

import asyncio
import os
import sys

# Add backend root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.email_service import send_product_update_email


# ── Email content ──────────────────────────────────────────────────────────

SUBJECT = "Bonito just got sharper"
HEADING = "Platform Update — May 2026"

ITEMS = [
    {
        "title": "Cleaner API Responses",
        "description": (
            "The Bonobot Agent API now gives you clear, immediate feedback when something "
            "in your request isn't right — no more guessing. "
            "If you're calling the API directly, run a quick test to make sure your payloads are current. "
            "Our <a href='https://getbonito.com/docs' style='color:#7c3aed;'>updated docs</a> have the latest field reference."
        ),
    },
    {
        "title": "CLI v0.6.1 — Upgrade Recommended",
        "description": (
            "The Bonito CLI has been updated to match the latest API improvements. "
            "Upgrade in one command: <code style='color:#7c3aed;'>pip install --upgrade bonito-cli</code>"
        ),
    },
    {
        "title": "Refreshed Documentation",
        "description": (
            "Agent provisioning guides, connection schemas, and tool policy references have all been "
            "updated to reflect exactly what the live API expects. If you're building on Bonobot, "
            "the docs are now your single source of truth."
        ),
    },
]

CTA_TEXT = "Explore the Docs"
CTA_URL = "https://getbonito.com/docs"


# ── Main ───────────────────────────────────────────────────────────────────

async def main():
    dry_run = "--dry-run" in sys.argv
    test_email = None
    for i, arg in enumerate(sys.argv):
        if arg == "--test-email" and i + 1 < len(sys.argv):
            test_email = sys.argv[i + 1]

    if test_email:
        print(f"Sending test email to: {test_email}")
        await send_product_update_email(
            to=test_email,
            name="Test User",
            subject=SUBJECT,
            heading=HEADING,
            items=ITEMS,
            cta_text=CTA_TEXT,
            cta_url=CTA_URL,
        )
        print("Sent!")
        return

    # Query all verified users
    from sqlalchemy import select
    from app.core.database import async_session
    from app.models.user import User

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.email_verified.is_(True)).order_by(User.created_at)
        )
        users = result.scalars().all()

    print(f"Found {len(users)} verified users")

    if dry_run:
        for user in users:
            print(f"  Would send to: {user.email} ({user.name})")
        print(f"\nDry run complete. Use without --dry-run to send.")
        return

    sent = 0
    errors = 0
    for user in users:
        try:
            await send_product_update_email(
                to=user.email,
                name=user.name,
                subject=SUBJECT,
                heading=HEADING,
                items=ITEMS,
                cta_text=CTA_TEXT,
                cta_url=CTA_URL,
            )
            sent += 1
            print(f"  Sent to: {user.email}")
        except Exception as e:
            errors += 1
            print(f"  FAILED: {user.email} — {e}")

    print(f"\nDone: {sent} sent, {errors} failed")


if __name__ == "__main__":
    asyncio.run(main())
