"""Cleanup stale Azure model entries and ensure deployment records exist.

Fixes:
- Removes Azure models that don't match any real Azure deployment
  (e.g. gpt-4o-2024-05-13 when actual deployment is 'gpt-4o')
- Removes audio/realtime/transcription models from the catalog
- Ensures Deployment records exist for the 4 known working Azure deployments

Revision ID: 023_cleanup_azure
Revises: 9475f6b522e4
Create Date: 2026-02-24
"""
from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = '023_cleanup_azure'
down_revision: Union[str, None] = '9475f6b522e4'
branch_labels = None
depends_on = None

# Known working Azure deployments (from `az cognitiveservices account deployment list`)
AZURE_DEPLOYMENTS = {
    'gpt-4o-mini': 'gpt-4o-mini',
    'gpt-4o': 'gpt-4o',
    'o3-mini': 'o3-mini',
    'o4-mini': 'o4-mini',
}

# Patterns that indicate non-chat models (should not be in playground)
NON_CHAT_PATTERNS = [
    'audio', 'realtime', 'transcription', 'whisper', 'tts-',
    'dall-e', 'sora', 'embed', 'babbage',
]


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Find all Azure providers
    azure_providers = conn.execute(
        sa.text("SELECT id, org_id FROM cloud_providers WHERE provider_type = 'azure'")
    ).fetchall()

    for provider_id, org_id in azure_providers:
        # 2. Get all models for this Azure provider
        models = conn.execute(
            sa.text("SELECT id, model_id, display_name FROM models WHERE provider_id = :pid"),
            {"pid": provider_id},
        ).fetchall()

        for model_uuid, model_id, display_name in models:
            mid_lower = (model_id or '').lower()
            dname_lower = (display_name or '').lower()

            # 3. Remove non-chat models (audio, embedding, etc.)
            if any(p in mid_lower or p in dname_lower for p in NON_CHAT_PATTERNS):
                # Check if it has deployments first
                dep_count = conn.execute(
                    sa.text("SELECT COUNT(*) FROM deployments WHERE model_id = :mid"),
                    {"mid": model_uuid},
                ).scalar()
                if dep_count == 0:
                    conn.execute(
                        sa.text("DELETE FROM models WHERE id = :mid"),
                        {"mid": model_uuid},
                    )
                continue

            # 4. For models that match a known deployment name exactly, ensure
            #    a Deployment record exists
            if model_id in AZURE_DEPLOYMENTS:
                dep_name = AZURE_DEPLOYMENTS[model_id]
                existing_dep = conn.execute(
                    sa.text(
                        "SELECT id FROM deployments WHERE model_id = :mid AND org_id = :oid"
                    ),
                    {"mid": model_uuid, "oid": org_id},
                ).fetchone()

                if not existing_dep:
                    import uuid as _uuid
                    import json as _json
                    conn.execute(
                        sa.text("""
                            INSERT INTO deployments (id, org_id, model_id, provider_id, config, status)
                            VALUES (:id, :oid, :mid, :pid, :config, 'active')
                        """),
                        {
                            "id": str(_uuid.uuid4()),
                            "oid": org_id,
                            "mid": model_uuid,
                            "pid": provider_id,
                            "config": _json.dumps({
                                "name": dep_name,
                                "cloud_model_id": model_id,
                                "provider_type": "azure",
                                "tpm": 10,
                                "tier": "Standard",
                            }),
                        },
                    )

            # 5. For models with date suffixes (e.g. gpt-4o-2024-05-13)
            #    that DON'T match any deployment and have no deployment record,
            #    delete them — they'll just 500 in the playground
            else:
                # Check if the model is a date-suffixed variant of a known deployment
                is_stale_variant = False
                for known_name in AZURE_DEPLOYMENTS:
                    if mid_lower.startswith(known_name) and mid_lower != known_name:
                        is_stale_variant = True
                        break

                if is_stale_variant:
                    dep_count = conn.execute(
                        sa.text("SELECT COUNT(*) FROM deployments WHERE model_id = :mid"),
                        {"mid": model_uuid},
                    ).scalar()
                    if dep_count == 0:
                        conn.execute(
                            sa.text("DELETE FROM models WHERE id = :mid"),
                            {"mid": model_uuid},
                        )


    # 6. Fix AWS on-demand deployments showing provisioned throughput cost estimates
    #    If config_applied.type == "on-demand", cost should be $0
    import json as _json2
    aws_deps = conn.execute(
        sa.text("""
            SELECT id, config FROM deployments
            WHERE config::text LIKE '%"provider_type": "aws"%'
        """)
    ).fetchall()
    for dep_id, config in aws_deps:
        if not config:
            continue
        config_applied = config.get("config_applied", {})
        cost_est = config.get("cost_estimate", {})
        if config_applied.get("type") == "on-demand" and cost_est.get("monthly", 0) > 0:
            config["cost_estimate"] = {
                "hourly": 0,
                "daily": 0,
                "monthly": 0,
                "unit": "Pay-per-request (no fixed cost)",
                "notes": "On-demand access — you pay per token used, no reserved capacity.",
            }
            conn.execute(
                sa.text("UPDATE deployments SET config = :config WHERE id = :id"),
                {"config": _json2.dumps(config), "id": dep_id},
            )

    # 7. Remove duplicate Azure deployment records (keep the one with tier set)
    azure_deps = conn.execute(
        sa.text("""
            SELECT id, config, org_id FROM deployments
            WHERE config::text LIKE '%"provider_type": "azure"%'
            ORDER BY created_at ASC
        """)
    ).fetchall()

    seen_azure = {}  # (org_id, deployment_name) -> first deployment id
    for dep_id, config, org_id in azure_deps:
        if not config:
            continue
        dep_name = config.get("name", "")
        key = (str(org_id), dep_name)
        if key in seen_azure:
            # Duplicate — delete this one
            conn.execute(
                sa.text("DELETE FROM deployments WHERE id = :id"),
                {"id": dep_id},
            )
        else:
            seen_azure[key] = dep_id


def downgrade() -> None:
    # Data-only migration — downgrade is a no-op.
    # Models will be re-synced on next provider sync.
    pass
