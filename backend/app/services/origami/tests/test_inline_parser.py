"""Regression tests for the inline tool-call fallback parser.

When Claude degrades to text-mode tool-call emission (observed in PROD
on complex multi-agent prompts even with raised max_tokens), the
orchestrator's fallback parser walks the response text line-by-line and
tries to recover each `name(args)` call as if it were a proper tool_use
block. The fallback can only run when the parser can actually parse the
line.

The recovered call's params eventually flow through
_resolve_template_params at execute time, which knows how to substitute
${step_N.field} references. So the parser must preserve those
references through the AST round-trip, not reject lines that contain
them.
"""

from __future__ import annotations

from app.services.origami.orchestrator import _try_parse_function_call_syntax


def test_simple_call_parses() -> None:
    result = _try_parse_function_call_syntax('create_project(name="origami-bots")')
    assert result is not None
    name, params = result
    assert name == "create_project"
    assert params == {"name": "origami-bots"}


def test_template_reference_preserved() -> None:
    """The user's exact failing line on the 2026-06-12 PROD bug:

    The model degraded to text-mode and emitted create_agent calls with
    ${step_1.project_id} template refs. ast.parse() rejected those as
    invalid Python, so the fallback parser silently no-op'd and the
    plan card never rendered.

    After the fix, the parser preprocesses ${...} to a quoted string
    before ast.parse, then the downstream _resolve_template_params
    handles substitution at execute time.
    """
    line = (
        'create_agent(name="deal-intake", '
        'system_prompt="You are the front door for incoming VC/PE deals.", '
        'model="claude-sonnet-4-5", '
        "project_id=${step_1.project_id})"
    )
    result = _try_parse_function_call_syntax(line)
    assert result is not None, (
        "Template-ref line must parse — preprocessing should convert "
        "${step_1.project_id} to a string literal before ast.parse"
    )
    name, params = result
    assert name == "create_agent"
    assert params["name"] == "deal-intake"
    assert params["model"] == "claude-sonnet-4-5"
    # Critical: template ref preserved as a string. _resolve_template_params
    # will detect the ${...} pattern at execute time and substitute the
    # actual project_id from step_1's tool result.
    assert params["project_id"] == "${step_1.project_id}", (
        f"template ref dropped or rewritten: got {params['project_id']!r}"
    )


def test_nested_template_references() -> None:
    """A single call referencing multiple prior steps."""
    line = (
        "link_kb_to_agent("
        "agent_id=${step_3.agent_id}, "
        "kb_id=${step_2.kb_id})"
    )
    result = _try_parse_function_call_syntax(line)
    assert result is not None
    _, params = result
    assert params["agent_id"] == "${step_3.agent_id}"
    assert params["kb_id"] == "${step_2.kb_id}"


def test_prev_template_reference() -> None:
    """The ${prev.field} form is also supported by the resolver."""
    line = "update_agent(agent_id=${prev.agent_id}, model=\"claude-sonnet-4-5\")"
    result = _try_parse_function_call_syntax(line)
    assert result is not None
    _, params = result
    assert params["agent_id"] == "${prev.agent_id}"
    assert params["model"] == "claude-sonnet-4-5"


def test_non_template_dollar_signs_left_alone() -> None:
    """Dollar signs that aren't ${name.field} pattern shouldn't be
    rewritten — e.g. a system_prompt that mentions cost in USD."""
    line = (
        'create_agent(name="pricing-bot", '
        'system_prompt="Always quote prices in $ USD, not other currencies.")'
    )
    result = _try_parse_function_call_syntax(line)
    assert result is not None
    _, params = result
    assert "$ USD" in params["system_prompt"]


def test_malformed_line_returns_none() -> None:
    """Genuinely broken syntax (not template refs) still returns None."""
    assert _try_parse_function_call_syntax("create_agent(name=, unterminated") is None
    assert _try_parse_function_call_syntax("not a call") is None
    assert _try_parse_function_call_syntax("") is None


def test_positional_args_rejected() -> None:
    """Origami tools require named args; positional-only calls bail."""
    assert _try_parse_function_call_syntax('create_kb("just-a-name")') is None
