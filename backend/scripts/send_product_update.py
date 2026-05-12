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

from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.user import User
from app.services.email_service import send_product_update_email


# ── Email content ──────────────────────────────────────────────────────────

SUBJECT = "Bonito Platform Update — May 2026"
HEADING = "What's New in Bonito"

ITEMS = [
    {
        "title": "Sentry Error Tracking",
        "description": (
            "Both the API and dashboard now report errors to Sentry in real-time. "
            "This means faster incident detection and resolution — issues that would have "
            "gone unnoticed are now caught immediately."
        ),
    },
    {
        "title": "Stricter API Validation (Action Required for API Users)",
        "description": (
            "The Bonobot Agent API now rejects unknown fields with a <strong>422 error</strong> "
            "instead of silently dropping them. If you're calling the API directly, check that you're using "
            "<code style='color:#7c3aed;'>model_id</code> (not <code>model</code>) and the correct "
            "<code style='color:#7c3aed;'>tool_policy</code> shape. "
            "See our updated docs at <a href='https://getbonito.com/docs' style='color:#7c3aed;'>getbonito.com/docs</a>."
        ),
    },
    {
        "title": "CLI v0.6.1",
        "description": (
            "Updated <code style='color:#7c3aed;'>bonito deploy</code> to work with the new validation. "
            "Upgrade with: <code style='color:#7c3aed;'>pip install --upgrade bonito-cli</code>"
        ),
    },
    {
        "title": "Updated API Documentation",
        "description": (
            "Corrected field names, schema shapes, and connection types across all Bonobot API docs. "
            "If you've been referencing the docs for agent provisioning, the latest version now matches "
            "what the live API actually accepts."
        ),
    },
]

CTA_TEXT = "View Documentation"
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
    async with async_session_factory() as session:
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
