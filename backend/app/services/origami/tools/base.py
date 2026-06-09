"""Origami tool abstract base + registry.

Security invariant: every tool's `execute()` receives an explicit `org_id`
argument sourced from `OrigamiContext.org_id` (the og- token record).
Tools NEVER read `org_id` from the model-generated `params` dict — even if
the LLM hallucinates one, it gets stripped before execute() runs.

Tool params are validated against `input_schema` before execute() is called.
`org_id` is intentionally NOT in any tool's input_schema — the framework
injects it server-side.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class OrigamiTool(ABC):
    """Abstract base for an Origami tool.

    Concrete subclasses MUST set:
        name: str — unique slug, e.g. "list_org_state"
        description: str — what the tool does (sent to model)
        input_schema: dict — JSON schema for params (NO org_id field)
        is_write: bool — True if the tool mutates state (requires plan card confirmation)
    """

    name: ClassVar[str]
    description: ClassVar[str]
    input_schema: ClassVar[dict[str, Any]]
    is_write: ClassVar[bool] = False

    @abstractmethod
    async def execute(
        self,
        *,
        org_id: uuid.UUID,
        user: User,
        params: dict[str, Any],
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Run the tool. Returns a dict that goes back to the model as tool_result.

        IMPORTANT: this method MUST read org_id from the kwarg, never from params.
        The orchestrator strips org_id from params before calling.
        """
        raise NotImplementedError

    @classmethod
    def to_anthropic_schema(cls) -> dict[str, Any]:
        """Convert to Anthropic tool-use schema."""
        return {
            "name": cls.name,
            "description": cls.description,
            "input_schema": cls.input_schema,
        }


TOOL_REGISTRY: dict[str, type[OrigamiTool]] = {}


def register_tool(tool_cls: type[OrigamiTool]) -> type[OrigamiTool]:
    """Decorator to register a tool in the global registry."""
    if not tool_cls.name:
        raise ValueError(f"{tool_cls.__name__} is missing `name` ClassVar")
    if tool_cls.name in TOOL_REGISTRY:
        raise ValueError(f"Duplicate tool registration: {tool_cls.name}")
    TOOL_REGISTRY[tool_cls.name] = tool_cls
    return tool_cls


def get_tool(name: str) -> type[OrigamiTool] | None:
    """Look up a tool by name."""
    return TOOL_REGISTRY.get(name)


def list_tools() -> list[type[OrigamiTool]]:
    """Return all registered tools."""
    return list(TOOL_REGISTRY.values())


def sanitize_params(params: dict[str, Any]) -> dict[str, Any]:
    """Strip any field the model is forbidden from setting.

    Currently strips `org_id` (must come from token context). Extend with
    any future fields that must be server-injected.
    """
    return {k: v for k, v in params.items() if k not in {"org_id"}}
