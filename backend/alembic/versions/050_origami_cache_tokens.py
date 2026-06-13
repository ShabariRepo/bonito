"""Add cache token columns to origami_turn_log for cache-aware cost.

Stores the cached-read and cache-write token counts per Studio/Origami turn
so the admin billing dashboard can compute the REAL (cache-discounted) cost
and true margin. The existing cost_usd stays full-price (conservative) — it
still feeds the spend cap, which we intentionally keep over-counting so usage
caps early and we recoup via metering.
"""

from alembic import op
import sqlalchemy as sa

revision = "050_origami_cache_tokens"
down_revision = "049_project_manifests"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "origami_turn_log",
        sa.Column("cache_read_tokens", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "origami_turn_log",
        sa.Column("cache_write_tokens", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_column("origami_turn_log", "cache_write_tokens")
    op.drop_column("origami_turn_log", "cache_read_tokens")
