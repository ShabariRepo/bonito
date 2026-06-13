"""Prompt-cache wiring tests (zero LLM calls).

Verifies the orchestrator marks the static prefix (system + tools) with an
Anthropic ephemeral cache_control breakpoint when the flag is on AND the
model is Anthropic — and that it's byte-identical to the old uncached path
otherwise. Caching is a billing/latency optimization; these tests prove the
request shape without spending a cent.
"""

from __future__ import annotations

import copy

from app.services.origami import orchestrator as orch
from app.services.origami.orchestrator import _build_gateway_body, _is_anthropic_model


_TOOLS = [
    {"type": "function", "function": {"name": "create_project", "parameters": {}}},
    {"type": "function", "function": {"name": "create_agent", "parameters": {}}},
]


def _body(monkeypatch, *, cache: bool, model: str):
    monkeypatch.setattr(orch, "ORIGAMI_PROMPT_CACHE", cache)
    monkeypatch.setattr(orch, "ORIGAMI_MODEL", model)
    return _build_gateway_body(
        system="SYSTEM PROMPT TEXT",
        messages=[{"role": "user", "content": "hi"}],
        tools=copy.deepcopy(_TOOLS),
        customer_org_id=None,
        customer_user_id=None,
        stream=True,
    )


def test_anthropic_gate():
    assert _is_anthropic_model("claude-sonnet-4-6")
    assert _is_anthropic_model("us.anthropic.claude-sonnet-4-6")
    assert _is_anthropic_model("claude-haiku-4-5")
    assert not _is_anthropic_model("gpt-4o")
    assert not _is_anthropic_model("groq/llama-3.3-70b")
    assert not _is_anthropic_model("gemini-2.5-flash")


def test_cache_on_anthropic_marks_system_and_last_tool(monkeypatch):
    body = _body(monkeypatch, cache=True, model="claude-sonnet-4-6")
    sys_msg = body["messages"][0]
    assert sys_msg["role"] == "system"
    # System content becomes a content-block list with an ephemeral marker
    assert isinstance(sys_msg["content"], list)
    assert sys_msg["content"][0]["text"] == "SYSTEM PROMPT TEXT"
    assert sys_msg["content"][0]["cache_control"] == {"type": "ephemeral"}
    # Last tool carries the breakpoint; earlier tools do not
    assert body["tools"][-1]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in body["tools"][0]


def test_cache_off_is_plain_string(monkeypatch):
    body = _body(monkeypatch, cache=False, model="claude-sonnet-4-6")
    sys_msg = body["messages"][0]
    # Byte-identical to the original uncached path
    assert sys_msg == {"role": "system", "content": "SYSTEM PROMPT TEXT"}
    assert all("cache_control" not in t for t in body["tools"])


def test_cache_on_non_anthropic_is_plain_string(monkeypatch):
    # Flag on but model routes elsewhere => no cache_control injected
    body = _body(monkeypatch, cache=True, model="gpt-4o")
    sys_msg = body["messages"][0]
    assert sys_msg == {"role": "system", "content": "SYSTEM PROMPT TEXT"}
    assert all("cache_control" not in t for t in body["tools"])


def test_original_tool_schemas_not_mutated(monkeypatch):
    pristine = copy.deepcopy(_TOOLS)
    tools = copy.deepcopy(_TOOLS)
    monkeypatch.setattr(orch, "ORIGAMI_PROMPT_CACHE", True)
    monkeypatch.setattr(orch, "ORIGAMI_MODEL", "claude-sonnet-4-6")
    _build_gateway_body(
        system="S", messages=[], tools=tools,
        customer_org_id=None, customer_user_id=None, stream=False,
    )
    # The caller's tools list must be untouched (we copy before marking)
    assert tools == pristine
