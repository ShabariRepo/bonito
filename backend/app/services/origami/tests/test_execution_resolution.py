"""Regression tests for chained-build execution resolution.

Covers the 2026-06-12 bootcamp-sim failures:
  - garbage tool calls (resource name as tool name) breaking step indices
  - create_agent project_id heuristic when ${step_N} didn't resolve
"""

from __future__ import annotations

from app.services.origami.orchestrator import (
    _heuristic_fill_project_id,
    _resolve_template_params,
)


def test_project_id_heuristic_fills_from_create_project_result():
    """create_agent with an unresolved template project_id should get the
    most-recent create_project result's project_id."""
    step_results = [
        {"project_id": "11111111-1111-1111-1111-111111111111", "name": "proj"},
        {"kb_id": "22222222-2222-2222-2222-222222222222", "name": "kb"},
    ]
    params = {"name": "agent", "project_id": "${step_1.project_id}"}  # unresolved
    out = _heuristic_fill_project_id("create_agent", params, step_results)
    assert out["project_id"] == "11111111-1111-1111-1111-111111111111"


def test_project_id_heuristic_fills_from_name_in_id_field():
    """Model passed a NAME in project_id — heuristic should still find the
    real UUID from the plan's create_project step."""
    step_results = [
        {"project_id": "33333333-3333-3333-3333-333333333333", "name": "marketing"},
    ]
    params = {"name": "agent", "project_id": "marketing"}  # name, not UUID
    out = _heuristic_fill_project_id("create_agent", params, step_results)
    assert out["project_id"] == "33333333-3333-3333-3333-333333333333"


def test_project_id_heuristic_leaves_valid_uuid_alone():
    step_results = [{"project_id": "99999999-9999-9999-9999-999999999999"}]
    valid = "44444444-4444-4444-4444-444444444444"
    params = {"name": "agent", "project_id": valid}
    out = _heuristic_fill_project_id("create_agent", params, step_results)
    assert out["project_id"] == valid  # untouched


def test_project_id_heuristic_noop_for_non_create_agent():
    params = {"foo": "bar"}
    out = _heuristic_fill_project_id("create_kb", params, [])
    assert out == params


def test_template_resolution_correct_after_garbage_filtered():
    """With the garbage step filtered, step indices align so ${step_1}
    correctly points to the first real tool's result."""
    # Simulate: create_project (step 1) → create_agent referencing it
    step_results = [
        {"project_id": "55555555-5555-5555-5555-555555555555"},  # step_1
    ]
    params = {"name": "agent", "project_id": "${step_1.project_id}"}
    out = _resolve_template_params(params, step_results)
    assert out["project_id"] == "55555555-5555-5555-5555-555555555555"
