"""Regression tests for the plan-dependency validator.

Locks in the fix for the bug where the orchestrator emitted plans that
referenced agents/KBs by name without including the corresponding
create_agent / create_kb steps. In PROD the model would silently
truncate the longer create_agent tool calls when the output budget got
tight, leaving connect_agents and link_kb_to_agent steps with dangling
references.

The validator runs at plan-build time (NOT execution time) so we can
inject a structured retry to the model before the user sees a broken
plan card.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest

from app.schemas.origami_plan import PlanChange
from app.services.origami.orchestrator import _validate_plan_dependencies


class _FakeResult:
    def scalar_one_or_none(self):
        return None


class _FakeDB:
    """No agents / KBs in this fake org — exercises the worst case."""

    async def execute(self, *_args, **_kwargs):
        return _FakeResult()


@pytest.fixture
def fake_db():
    return _FakeDB()


@pytest.fixture
def fake_org_id():
    return uuid.uuid4()


# The user's exact broken plan reported in the 2026-06-12 PROD issue.
USER_BROKEN_PLAN = [
    PlanChange(action="create_project", params={"name": "origami-venture-bots"}),
    PlanChange(action="create_kb", params={"name": "origami-venture-bots-deals"}),
    PlanChange(action="mint_gateway_key", params={"name": "origami-venture-bots-prod"}),
    # No create_agent calls — bug!
    PlanChange(
        action="connect_agents",
        params={
            "source_agent_name": "deal-intake",
            "target_agent_name": "market-analyst",
            "connection_type": "handoff",
        },
    ),
    PlanChange(
        action="connect_agents",
        params={
            "source_agent_name": "deal-intake",
            "target_agent_name": "financial-analyst",
            "connection_type": "handoff",
        },
    ),
    PlanChange(
        action="connect_agents",
        params={
            "source_agent_name": "deal-intake",
            "target_agent_name": "team-analyst",
            "connection_type": "handoff",
        },
    ),
    PlanChange(
        action="link_kb_to_agent",
        params={"agent_name": "deal-intake", "kb_name": "origami-venture-bots-deals"},
    ),
    PlanChange(
        action="link_kb_to_agent",
        params={"agent_name": "market-analyst", "kb_name": "origami-venture-bots-deals"},
    ),
    PlanChange(
        action="link_kb_to_agent",
        params={"agent_name": "financial-analyst", "kb_name": "origami-venture-bots-deals"},
    ),
    PlanChange(
        action="link_kb_to_agent",
        params={"agent_name": "team-analyst", "kb_name": "origami-venture-bots-deals"},
    ),
]


@pytest.mark.asyncio
async def test_user_broken_plan_caught(fake_db, fake_org_id):
    """The exact user-reported broken plan must be flagged with at least
    one error per missing agent reference."""
    errors = await _validate_plan_dependencies(
        USER_BROKEN_PLAN, db=fake_db, org_id=fake_org_id
    )
    assert len(errors) >= 8, (
        f"Expected at least 8 errors (4 agents × at least 2 references), "
        f"got {len(errors)}: {errors}"
    )
    # All four expected agent names should appear at least once
    for missing in ("deal-intake", "market-analyst", "financial-analyst", "team-analyst"):
        assert any(missing in e for e in errors), (
            f"No error mentioned missing agent '{missing}'. Errors: {errors}"
        )


@pytest.mark.asyncio
async def test_corrected_plan_passes(fake_db, fake_org_id):
    """Same plan with the create_agent calls added must pass validation."""
    corrected = [
        PlanChange(action="create_project", params={"name": "origami-venture-bots"}),
        PlanChange(action="create_kb", params={"name": "origami-venture-bots-deals"}),
        PlanChange(action="mint_gateway_key", params={"name": "origami-venture-bots-prod"}),
        PlanChange(action="create_agent", params={"name": "deal-intake", "system_prompt": "..."}),
        PlanChange(action="create_agent", params={"name": "market-analyst", "system_prompt": "..."}),
        PlanChange(action="create_agent", params={"name": "financial-analyst", "system_prompt": "..."}),
        PlanChange(action="create_agent", params={"name": "team-analyst", "system_prompt": "..."}),
        PlanChange(
            action="connect_agents",
            params={
                "source_agent_name": "deal-intake",
                "target_agent_name": "market-analyst",
                "connection_type": "handoff",
            },
        ),
        PlanChange(
            action="link_kb_to_agent",
            params={"agent_name": "deal-intake", "kb_name": "origami-venture-bots-deals"},
        ),
    ]
    errors = await _validate_plan_dependencies(
        corrected, db=fake_db, org_id=fake_org_id
    )
    assert errors == [], f"Corrected plan should pass; got errors: {errors}"


@pytest.mark.asyncio
async def test_uuid_references_skip_validation(fake_db, fake_org_id):
    """When the model emits UUIDs instead of names, skip name-based
    validation — the UUID will be resolved at execution time."""
    plan = [
        PlanChange(
            action="connect_agents",
            params={
                "source_agent_id": str(uuid.uuid4()),
                "target_agent_id": str(uuid.uuid4()),
                "connection_type": "handoff",
            },
        ),
    ]
    errors = await _validate_plan_dependencies(plan, db=fake_db, org_id=fake_org_id)
    assert errors == [], (
        f"UUID-only references should skip name validation; got: {errors}"
    )


@pytest.mark.asyncio
async def test_from_to_aliases_validated(fake_db, fake_org_id):
    """The model sometimes uses from_agent_name / to_agent_name aliases.
    The validator must catch missing references under either naming."""
    plan = [
        PlanChange(
            action="connect_agents",
            params={
                "from_agent_name": "nonexistent-1",
                "to_agent_name": "nonexistent-2",
                "connection_type": "handoff",
            },
        ),
    ]
    errors = await _validate_plan_dependencies(plan, db=fake_db, org_id=fake_org_id)
    assert any("nonexistent-1" in e for e in errors), (
        f"from_agent_name alias not validated. errors={errors}"
    )
    assert any("nonexistent-2" in e for e in errors), (
        f"to_agent_name alias not validated. errors={errors}"
    )


@pytest.mark.asyncio
async def test_link_kb_to_agent_missing_kb(fake_db, fake_org_id):
    """link_kb_to_agent referencing a KB that's neither created nor existing
    must fail validation."""
    plan = [
        PlanChange(action="create_agent", params={"name": "my-agent"}),
        PlanChange(
            action="link_kb_to_agent",
            params={"agent_name": "my-agent", "kb_name": "ghost-kb"},
        ),
    ]
    errors = await _validate_plan_dependencies(plan, db=fake_db, org_id=fake_org_id)
    assert any("ghost-kb" in e for e in errors), (
        f"Missing KB not caught; errors={errors}"
    )


@pytest.mark.asyncio
async def test_empty_plan_passes(fake_db, fake_org_id):
    """Empty plan has no dependency violations."""
    errors = await _validate_plan_dependencies([], db=fake_db, org_id=fake_org_id)
    assert errors == []


@pytest.mark.asyncio
async def test_alias_action_names_handled(fake_db, fake_org_id):
    """Models sometimes call connect_agents by aliases like 'wire_agents' or
    'create_connection'. The validator must resolve those aliases before
    checking."""
    plan = [
        PlanChange(
            action="wire_agents",
            params={
                "source_agent_name": "ghost-source",
                "target_agent_name": "ghost-target",
                "connection_type": "handoff",
            },
        ),
    ]
    errors = await _validate_plan_dependencies(plan, db=fake_db, org_id=fake_org_id)
    assert len(errors) >= 2, (
        f"Aliased action 'wire_agents' should be resolved to connect_agents "
        f"and validated; got errors={errors}"
    )
