"""show_integration_guide — copy-paste-ready code to call a Bonito agent.

Origami's differentiator: "how do I call this agent from my prod app?"
gets answered inline with the user's actual endpoint, agent_id, and a
recommended auth pattern — no tab-switching to docs.

Returns: endpoint URL, request shape, ready-to-paste snippets for curl,
Python, and TypeScript with the agent's UUID and the user's tier-appropriate
rate limit pre-filled. Auth recommendation tracks the user's tier (PAT for
all tiers; project tokens highlighted for Pro+).

Read-only tool — executes inline, no plan card. Does NOT include the actual
PAT value (never emit credentials in chat). Tells the user where to mint
one and what prefix to look for.
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.origami.tools.base import OrigamiTool, register_tool


_VALID_LANGUAGES = {"curl", "python", "typescript", "all"}


def _api_base() -> str:
    return os.getenv("BONITO_API_BASE_URL", "https://api.getbonito.com").rstrip("/")


def _curl_snippet(*, base: str, agent_id: str) -> str:
    return f"""curl -X POST {base}/api/agents/{agent_id}/execute \\
  -H "Authorization: Bearer $BONITO_PAT" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "message": "Your prompt to the agent goes here."
  }}'"""


def _python_snippet(*, base: str, agent_id: str) -> str:
    return f"""import os, requests

BONITO_PAT = os.environ["BONITO_PAT"]  # bp-... PAT from Settings → Tokens
AGENT_ID = "{agent_id}"

resp = requests.post(
    f"{base}/api/agents/{{AGENT_ID}}/execute",
    headers={{"Authorization": f"Bearer {{BONITO_PAT}}"}},
    json={{"message": "Your prompt to the agent goes here."}},
    timeout=60,
)
resp.raise_for_status()
data = resp.json()
print(data["content"])           # agent reply
print(data["tokens"], data["cost"])  # billing telemetry
print(data["session_id"])        # pass back as session_id for multi-turn"""


def _typescript_snippet(*, base: str, agent_id: str) -> str:
    return f"""const BONITO_PAT = process.env.BONITO_PAT!;   // bp-... PAT
const AGENT_ID = "{agent_id}";

const res = await fetch(
  `{base}/api/agents/${{AGENT_ID}}/execute`,
  {{
    method: "POST",
    headers: {{
      "Authorization": `Bearer ${{BONITO_PAT}}`,
      "Content-Type": "application/json",
    }},
    body: JSON.stringify({{ message: "Your prompt to the agent goes here." }}),
  }},
);
if (!res.ok) throw new Error(await res.text());
const data = await res.json();
console.log(data.content);           // agent reply
console.log(data.session_id);        // pass back for multi-turn"""


@register_tool
class ShowIntegrationGuideTool(OrigamiTool):
    name = "show_integration_guide"
    description = (
        "Show the user how to call one of their Bonito agents from "
        "their own application. Returns the live endpoint URL, the "
        "request body shape, the auth pattern (PAT-based), the agent's "
        "current rate limit, and copy-paste code snippets for curl, "
        "Python, and TypeScript with the agent's UUID pre-filled. Use "
        "this whenever the user asks 'how do I call this from my app', "
        "'how do I integrate <agent>', 'show me a snippet for <agent>', "
        "or anything similar. Read-only, no plan card."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "string",
                "description": "UUID of the agent. If you only know the name, pass `agent_name` instead.",
            },
            "agent_name": {
                "type": "string",
                "description": "Display name of the agent — resolved to a UUID server-side.",
            },
            "language": {
                "type": "string",
                "enum": sorted(_VALID_LANGUAGES),
                "description": "Snippet language to emphasize. Defaults to 'all'.",
            },
        },
        "required": [],
        "additionalProperties": False,
    }
    is_write = False

    async def execute(
        self,
        *,
        org_id: uuid.UUID,
        user: User,
        params: dict[str, Any],
        db: AsyncSession,
    ) -> dict[str, Any]:
        from app.models.agent import Agent
        from app.services.feature_gate import feature_gate

        # Resolve agent (UUID or name, org-scoped)
        agent_id_raw = params.get("agent_id")
        agent_name = (params.get("agent_name") or "").strip()
        agent: Optional[Agent] = None
        if agent_id_raw:
            try:
                aid = uuid.UUID(str(agent_id_raw))
            except (TypeError, ValueError):
                return {"success": False, "error": "invalid_agent_id",
                        "message": "agent_id must be a valid UUID."}
            row = await db.execute(select(Agent).where(Agent.id == aid, Agent.org_id == org_id))
            agent = row.scalar_one_or_none()
        elif agent_name:
            row = await db.execute(
                select(Agent).where(Agent.name == agent_name, Agent.org_id == org_id)
            )
            agent = row.scalar_one_or_none()
        else:
            row = await db.execute(
                select(Agent).where(Agent.org_id == org_id).limit(1)
            )
            agent = row.scalar_one_or_none()
            if not agent:
                return {"success": False, "error": "no_agent",
                        "message": "Create an agent first, then ask for an integration guide."}

        if not agent:
            ref = agent_id_raw or agent_name
            return {"success": False, "error": "agent_not_found",
                    "message": f"Agent '{ref}' not found in your organization."}

        language = (params.get("language") or "all").lower()
        if language not in _VALID_LANGUAGES:
            language = "all"

        # Tier-aware token guidance
        try:
            sub = await feature_gate.get_organization_subscription(db, str(org_id))
            tier = (sub["tier"].value if hasattr(sub["tier"], "value") else str(sub["tier"])).lower()
        except Exception:
            tier = "free"

        pat_caps = {"free": 2, "starter": 5, "builder": 5, "pro": 10, "growth": 10}
        pat_cap = pat_caps.get(tier, "unlimited")
        supports_project_tokens = tier in {"pro", "growth", "enterprise", "scale"}

        base = _api_base()
        agent_id_str = str(agent.id)

        snippets: dict[str, str] = {}
        if language in ("curl", "all"):
            snippets["curl"] = _curl_snippet(base=base, agent_id=agent_id_str)
        if language in ("python", "all"):
            snippets["python"] = _python_snippet(base=base, agent_id=agent_id_str)
        if language in ("typescript", "all"):
            snippets["typescript"] = _typescript_snippet(base=base, agent_id=agent_id_str)

        return {
            "success": True,
            "agent_id": agent_id_str,
            "agent_name": agent.name,
            "model_id": agent.model_id,
            "endpoint": f"{base}/api/agents/{agent_id_str}/execute",
            "method": "POST",
            "auth": {
                "header": "Authorization: Bearer <BONITO_PAT>",
                "token_type": "PAT (bp- prefix)",
                "where_to_get_one": "Settings → Personal Access Tokens",
                "tier_pat_cap": pat_cap,
                "tier": tier,
                "project_tokens_supported": supports_project_tokens,
                "project_token_note": (
                    "Pro+ also supports project tokens (bj- prefix) that "
                    "scope to a single project — useful for least-privilege "
                    "per-app credentials."
                ) if supports_project_tokens else None,
            },
            "request_body_shape": {
                "message": "<string, 1-100000 chars>",
                "session_id": "<UUID, optional — pass back for multi-turn>",
                "parent_agent_id": "<UUID, optional — for orchestrator pipelines>",
            },
            "response_shape": {
                "content": "<agent reply string>",
                "session_id": "<UUID for follow-up turns>",
                "run_id": "<UUID for tracing>",
                "tokens": "<int>",
                "cost": "<decimal USD>",
                "model_used": "<resolved model id>",
                "security": "<tools used, budgets, audit_id, rate-limit info>",
            },
            "rate_limit_rpm": agent.rate_limit_rpm,
            "knowledge_base_ids": list(agent.knowledge_base_ids or []),
            "snippets": snippets,
            "next_step": (
                "Mint a PAT under Settings → Personal Access Tokens, set "
                "BONITO_PAT in your env, and paste the snippet. For multi-turn, "
                "echo the returned session_id back on each call."
            ),
        }
