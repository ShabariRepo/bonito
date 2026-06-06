"""Stub Origami tools for the SDK spike.

These mirror two of the 12 build/write tools in the Origami MVP plan
(docs/ORIGAMI-MVP-PLAN.md §"Tool surface (MVP)") — `create_agent` and
`create_kb`. They DON'T touch the database or call the real Bonito API; they
print what they would do and return a structured result dict.

The point of the stubs:
- Exercise the @tool decorator + create_sdk_mcp_server pattern
- Show what the SDK's tool call payload + result shape looks like
- Give the model something to actually invoke on the "yes" path
"""

from __future__ import annotations

from typing import Annotated, Any

from claude_agent_sdk import tool


# ─── stub create_agent ──────────────────────────────────────────────────────


@tool(
    "create_agent",
    "Create a new Bonobot agent in the user's org. WRITE action — requires a "
    "user-confirmed plan card before invoking. Returns the new agent_id.",
    {
        "name": str,
        "system_prompt": str,
        "model_id": str,
        "kb_ids": list,  # list[str] of KB IDs to attach
    },
)
async def create_agent(args: dict[str, Any]) -> dict[str, Any]:
    name = args["name"]
    model_id = args["model_id"]
    kb_ids = args.get("kb_ids", []) or []

    # TODO: replace with real call into Bonito's internal API once we wire up.
    # In the real impl this would POST /api/agents with org_id sourced server-side
    # from the og- token (see ORIGAMI-MVP-PLAN.md §"`org_id` injection").
    print(f"\n[stub_tools] create_agent CALLED: name={name!r} model={model_id!r} kbs={kb_ids}")

    fake_agent_id = f"agent-stub-{name.lower().replace(' ', '-')}"
    return {
        "content": [
            {
                "type": "text",
                "text": (
                    f"Created agent {name!r} (id={fake_agent_id}) on model "
                    f"{model_id} with {len(kb_ids)} KB(s) attached."
                ),
            }
        ],
        # The SDK surfaces this dict back to the model. Keeping the structure
        # tight so the next turn can reference agent_id without re-reading prose.
        "structured_content": {"agent_id": fake_agent_id, "name": name, "model_id": model_id},
    }


# ─── stub create_kb ─────────────────────────────────────────────────────────


@tool(
    "create_kb",
    "Create a new knowledge base in the user's org. WRITE action — requires a "
    "user-confirmed plan card before invoking. Returns the new kb_id.",
    {
        "name": str,
        "dimensions": int,  # 768 or 1024 — see CLAUDE.md KB vector dimension fix
    },
)
async def create_kb(args: dict[str, Any]) -> dict[str, Any]:
    name = args["name"]
    dims = args.get("dimensions", 1024)

    # TODO: replace with real call into Bonito's KB service.
    print(f"\n[stub_tools] create_kb CALLED: name={name!r} dimensions={dims}")

    fake_kb_id = f"kb-stub-{name.lower().replace(' ', '-')}"
    return {
        "content": [
            {
                "type": "text",
                "text": f"Created KB {name!r} (id={fake_kb_id}) at {dims} dims.",
            }
        ],
        "structured_content": {"kb_id": fake_kb_id, "name": name, "dimensions": dims},
    }


ALL_TOOLS = [create_agent, create_kb]
