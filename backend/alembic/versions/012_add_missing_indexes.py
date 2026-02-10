"""Add missing indexes on org_id and frequently queried columns

Revision ID: 012_add_missing_indexes
Revises: 011_email_verification
Create Date: 2026-02-10
"""
from alembic import op

revision = "012_add_missing_indexes"
down_revision = "011_email_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Single-column org_id indexes
    op.create_index("ix_cloud_providers_org_id", "cloud_providers", ["org_id"])
    op.create_index("ix_routing_rules_org_id", "routing_rules", ["org_id"])
    op.create_index("ix_policies_org_id", "policies", ["org_id"])
    op.create_index("ix_gateway_keys_org_id", "gateway_keys", ["org_id"])

    # Composite indexes for time-range queries
    op.create_index("ix_audit_logs_org_id_created_at", "audit_logs", ["org_id", "created_at"])
    op.create_index("ix_cost_records_org_id_record_date", "cost_records", ["org_id", "record_date"])

    # Composite index for user notification lookups
    op.create_index("ix_notifications_user_id_org_id", "notifications", ["user_id", "org_id"])


def downgrade() -> None:
    op.drop_index("ix_notifications_user_id_org_id", table_name="notifications")
    op.drop_index("ix_cost_records_org_id_record_date", table_name="cost_records")
    op.drop_index("ix_audit_logs_org_id_created_at", table_name="audit_logs")
    op.drop_index("ix_gateway_keys_org_id", table_name="gateway_keys")
    op.drop_index("ix_policies_org_id", table_name="policies")
    op.drop_index("ix_routing_rules_org_id", table_name="routing_rules")
    op.drop_index("ix_cloud_providers_org_id", table_name="cloud_providers")
