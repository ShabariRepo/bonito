"""Add status column to models table

Revision ID: 029_add_model_status_column
Revises: 028_add_agent_canvas_position
Create Date: 2026-03-05 10:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '029_add_model_status_column'
down_revision = '028_add_agent_canvas_position'
branch_labels = None
depends_on = None


def upgrade():
    # Add status column to models table with default value 'active'
    op.add_column('models', sa.Column('status', sa.String(50), nullable=False, server_default='active'))


def downgrade():
    # Remove status column from models table
    op.drop_column('models', 'status')