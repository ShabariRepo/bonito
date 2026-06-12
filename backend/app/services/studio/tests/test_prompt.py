"""Tests for Studio's BDR system prompt + snapshot rendering.

The snapshot renderer is the contract between the snapshot service and
the model — it has to keep working with empty / partial / full org
states. These tests lock down the format so we don't accidentally break
the opener template when the snapshot dataclass grows new fields.
"""

from __future__ import annotations

from app.services.studio.prompt import (
    STUDIO_SYSTEM_PROMPT,
    render_snapshot_for_prompt,
)
from app.services.studio.snapshot import (
    BillingSummary,
    GatewayUsage,
    ProviderSummary,
    StudioSnapshot,
)


def _make_snapshot(**overrides) -> StudioSnapshot:
    base = dict(
        org_id="11111111-1111-1111-1111-111111111111",
        org_name="Acme Inc",
        providers=[],
        agent_count=0,
        agent_active_count=0,
        kb_count=0,
        kb_total_documents=0,
        gateway=GatewayUsage(),
        billing=BillingSummary(tier="free", days_since_signup=0),
        project_count=0,
    )
    base.update(overrides)
    return StudioSnapshot(**base)


def test_persona_is_first_person_and_warm():
    """Persona must be first-person + warm — Danny's whole point."""
    p = STUDIO_SYSTEM_PROMPT
    # First-person markers
    assert "I'll" in p or "I will" in p
    # BDR voice anchors
    assert "warm" in p.lower()
    assert "casual" in p.lower()
    assert "professional" in p.lower()
    # Must explicitly forbid generic openers
    assert "how can I help" in p.lower() or "what would you like" in p.lower()


def test_tool_use_rules_inherited():
    """Plan-card semantics from Origami must carry over verbatim — these
    are the rules the validator + parser were built against."""
    p = STUDIO_SYSTEM_PROMPT
    assert "create_project" in p
    assert "create_agent" in p
    assert "connect_agents" in p
    assert "link_kb_to_agent" in p
    assert "${step_N.field}" in p
    assert "DEPENDENCY RULE" in p


def test_snapshot_block_has_open_close_markers():
    """The frontend never sees the snapshot block — only the model does.
    We mark it with explicit open/close so future debugging is easy."""
    rendered = render_snapshot_for_prompt(_make_snapshot())
    assert rendered.startswith("[Bonito org snapshot")
    assert rendered.rstrip().endswith("[end snapshot]")


def test_snapshot_empty_org_renders_clean_opener_hints():
    """Brand-new org → snapshot tells the model exactly which opener to use."""
    s = _make_snapshot()
    rendered = render_snapshot_for_prompt(s)
    assert "Providers connected: none yet" in rendered
    assert "Agents: none yet" in rendered
    assert "Knowledge bases: none yet" in rendered
    assert "Gateway usage last 7 days: none" in rendered
    assert "Plan tier: free" in rendered


def test_snapshot_mid_build_org_lists_providers_and_agents():
    """1+ provider, 0 agents → opener should invite first agent build."""
    s = _make_snapshot(
        providers=[ProviderSummary("openai", "active")],
        billing=BillingSummary(tier="builder", days_since_signup=2),
    )
    rendered = render_snapshot_for_prompt(s)
    assert "Providers connected (1): openai (active)" in rendered
    assert "Agents: none yet" in rendered
    assert "Plan tier: builder (day 2 since signup)" in rendered


def test_snapshot_active_org_surfaces_gateway_usage_and_top_models():
    """Active org → opener should reference yesterday's gateway usage."""
    s = _make_snapshot(
        providers=[
            ProviderSummary("aws", "active"),
            ProviderSummary("anthropic", "active"),
        ],
        agent_count=4,
        agent_active_count=3,
        kb_count=2,
        kb_total_documents=128,
        project_count=2,
        gateway=GatewayUsage(
            requests_7d=12_400,
            cost_7d_usd=87.43,
            top_models=[
                ("claude-sonnet-4-6", 9_200),
                ("gpt-4o", 2_800),
                ("claude-haiku-4-5", 400),
            ],
        ),
        billing=BillingSummary(tier="pro", days_since_signup=180),
    )
    rendered = render_snapshot_for_prompt(s)
    # Top-line numbers must appear so the model can quote them
    assert "12400 requests" in rendered
    assert "$87.43" in rendered
    assert "claude-sonnet-4-6×9200" in rendered
    assert "Agents: 4 total (3 active)" in rendered
    assert "Knowledge bases: 2" in rendered
    assert "Providers connected (2):" in rendered


def test_snapshot_dict_round_trip_is_json_safe():
    """The /init endpoint returns this dict — must be plain JSON-able."""
    import json

    s = _make_snapshot(
        providers=[ProviderSummary("openai", "active")],
        gateway=GatewayUsage(
            requests_7d=10, cost_7d_usd=0.12345, top_models=[("gpt-4o", 10)]
        ),
    )
    blob = json.dumps(s.to_dict())
    decoded = json.loads(blob)
    assert decoded["providers"][0]["provider_type"] == "openai"
    assert decoded["gateway"]["requests_7d"] == 10
    # 4dp rounding applied so the API doesn't leak float noise
    assert decoded["gateway"]["cost_7d_usd"] == 0.1234 or decoded["gateway"]["cost_7d_usd"] == 0.1235
