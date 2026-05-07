"""Backfill email_verified=true for all existing users

Users created before the email verification feature (migration 011)
have email_verified=false by default, which locks them out of login.

Revision ID: 040_backfill_email_verified
Revises: 039_add_refresh_tokens
Create Date: 2026-05-07 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op

revision: str = "040_backfill_email_verified"
down_revision: str = "039_add_refresh_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE users SET email_verified = true WHERE email_verified = false")


def downgrade() -> None:
    pass  # Cannot safely revert — we don't know which users were originally unverified
