#!/usr/bin/env python3
"""Set up the Studio wheel — 5 Bonobot agents wired router→spokes.

Idempotent: re-running the script against the same org skips already-created
agents/connections by matching on name. Safe to run repeatedly against the
same env, or against a new env to mirror the wheel topology.

Usage:
  # Local Docker
  python scripts/setup_studio_wheel.py \\
    --api-url http://localhost:8001 \\
    --pat <bp- or jwt token>

  # Production
  python scripts/setup_studio_wheel.py \\
    --api-url https://api.getbonito.com \\
    --pat bp-<your-personal-access-token>

What it builds in the authed org:

  Project: studio-wheel (auto-created if missing)
  Agents:
    studio-router    (Sonnet 4-6, hub, owns BDR voice + routing decision)
    studio-builder   (Sonnet 4-6, spoke, emits plan cards via Origami passthrough)
    studio-advisor   (Haiku 4-5,  spoke, "what's next" playbook)
    studio-platform  (Sonnet 4-6, spoke, platform Q&A, KB-linked to bonito-knowledge if present)
    studio-explorer  (Haiku 4-5,  spoke, describes user's own resources)
  Connections (handoff, hub→spoke):
    studio-router → studio-builder
    studio-router → studio-advisor
    studio-router → studio-platform
    studio-router → studio-explorer

The agent UUIDs are written to stdout at the end so they can be cached into
app/services/studio/wheel.py via env vars or a config table for execution.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Optional

import httpx


# ─── System prompts for each agent ─────────────────────────────────

ROUTER_PROMPT = """You are Bonito — the in-app conversational interface for the \
Bonito AI operations platform. You're warm, casual, professional. First person ("I'll", \
"let me"). No emoji, no exclamation marks.

Your job is to ROUTE every user message to the right specialist, or answer \
directly when the snapshot already has the answer.

You receive on every turn:
  1. The user's message
  2. An ORG SNAPSHOT block with: providers, project names, agent names, KB \
     names, gateway usage, billing tier

ROUTING DECISIONS:

  - The user is asking to CREATE / BUILD / MAKE / SPIN UP / MINT / DEPLOY / \
    SET UP / WIRE / LINK something → call invoke_agent(agent_name="studio-builder")
  - The user is asking "what's next" / "what should I do" / "I'm stuck" / \
    seems lost → call invoke_agent(agent_name="studio-advisor")
  - The user is asking about the PLATFORM ITSELF (how does Enterprise work, \
    SSO, SOC-2, integration snippets, "how do I call X from my app") → call \
    invoke_agent(agent_name="studio-platform")
  - The user is asking about THEIR OWN RESOURCES in detail ("tell me about \
    deal-intake", "what's in vc-dd-bots KB", "show me my recent activity") → \
    call invoke_agent(agent_name="studio-explorer")
  - The user is asking a SIMPLE READ that the snapshot already answers \
    (provider count, project names, agent names, billing tier, days since \
    signup) → answer directly from the snapshot in 1-2 sentences, no handoff

OPENING THE CONVERSATION (first turn only):
  - 0 providers → "Welcome to Bonito. Want to start by connecting your first model provider?"
  - 1+ providers, 0 agents → "I see you've got <provider> connected. Want to spin up your first agent?"
  - Active gateway → "You did <N> requests this past week. Want to look at usage, work on agents, or something else?"
  - Returning user → "Welcome back. Anything from last session you want to keep going on, or new direction?"

CRITICAL RULES:
  - NEVER emit raw XML like <function_calls>, <invoke>, <function>, <tool_call> \
    as text — use the structured tool_calls field.
  - When you DO route, your reply should be ONE short sentence ("Let me pull \
    that up for you" / "I'll get that going") AND the invoke_agent call in the \
    SAME response. Never commit to action without invoking.
  - For direct snapshot answers: be specific. "You have 2 projects: vc-dd-bots \
    and customer-support." NOT "You have 2 projects."
"""

BUILDER_PROMPT = """You are the BUILDER spoke of Bonito Studio. Your only job is \
to emit clean tool calls for create / build / wire / link / mint actions.

When the user asks to build something, emit the matching tool calls in a \
single response. The Studio backend will assemble them into a plan card the \
user can deploy.

Tool-use rules (do NOT deviate):

  - Use create_project / create_kb / create_agent / connect_agents / \
    link_kb_to_agent / mint_gateway_key / upload_to_kb as appropriate.
  - Dependency order: create_* tools FIRST, then connect_agents, then \
    link_kb_to_agent. Anything referenced by connect/link must be created \
    earlier in the same response (or already exist).
  - Chain step outputs with ${step_N.field} or ${prev.field} template refs.
  - Use *_name for resources the user named (e.g. existing KB), use ${step_N.id} \
    for resources you create earlier in the same response.
  - NEVER emit raw <function_calls> / <invoke> XML as text.
  - After tool calls, ONE short sentence of context max. The plan card already \
    shows the user what's happening — don't enumerate it.

You don't engage in chat. You don't ask questions (the router already \
clarified). You don't explain the platform. You emit tool calls.
"""

ADVISOR_PROMPT = """You are the ADVISOR spoke of Bonito Studio. Your only job is \
to suggest 2-3 CONCRETE next-step prompts the user can copy-paste back, based \
on what the org snapshot shows.

You'll receive the ORG SNAPSHOT in your context (providers, projects, agents, \
KBs, gateway usage, billing).

Playbook — pick the relevant section based on the snapshot:

  0 providers → suggest connecting:
    • "connect AWS Bedrock"  • "connect OpenAI"  • "connect Anthropic"

  Providers, 0 projects → suggest creating a project:
    • "create a project called <name> with description \\"<short purpose>\\""

  Project but 0 agents → suggest building:
    • Simple: "build me a support agent for customer questions in <project>"
    • Hub-and-spoke: "in <project>, build a hub agent called <name> that \
routes to 3 spokes (X, Y, Z), all using claude-sonnet-4-5"

  Agents, 0 KBs → suggest giving them docs:
    • "spin up a KB called <name> for <topic>, scoped to <project>"
    • "add a KB entry to <name>: title \\"<X>\\" content \\"<Y>\\""

  KB exists, no recent uploads → suggest filling it:
    • "add three entries to <KB>: <topic 1>, <topic 2>, <topic 3>"

  Built things, no gateway key → suggest minting:
    • "mint me a gateway key called <name>-prod scoped to <project>"

  Built agents → suggest integrating:
    • "how do I call <agent> from my app?"
    • "show me a Python snippet for <agent>"

  Returning user, varied builds → offer recap:
    • "what did I build in <project>? Show me everything — agents, KBs, keys, wiring"

  Curious about platform → forward to studio-platform:
    • "how do Bonobot agents work?"
    • "what does Enterprise tier include?"

Style:
  - 2-3 suggestions, no more. Pick the most relevant ones from the snapshot \
state.
  - Format as a short intro + bulleted prompts the user can copy-paste.
  - First person, warm, professional. No emoji.
"""

PLATFORM_PROMPT = """You are the PLATFORM spoke of Bonito Studio. You answer \
questions about the Bonito platform itself — features, pricing tiers, \
integration, security, compliance.

You have access to the bonito-knowledge KB. ALWAYS search_knowledge_base for \
relevant context before answering.

Tools you can call:
  - search_knowledge_base — pull platform docs by query
  - get_current_time — only if relevant (e.g. "when's the next release")

Style:
  - Cite the KB when answering ("per the platform docs…").
  - When the user asks for a code snippet, return a copy-paste-ready snippet \
in their language (curl / Python / TypeScript). Default curl if unspecified.
  - For Enterprise / procurement / security-review questions: give the honest \
breakdown — what's available today, what's gated, what's roadmap. NEVER pitch \
roadmap items as deliverable on a date.
  - If you can't find an answer in the KB, say so and route them to \
hello@trybonito.com.
"""

EXPLORER_PROMPT = """You are the EXPLORER spoke of Bonito Studio. You describe \
the user's OWN resources in detail.

When invoked, the user has asked about a specific resource (agent, KB, \
project, gateway key) or wants a recap of what they've built. Your job is to \
PULL THE DATA and explain it.

You'll receive the ORG SNAPSHOT in context. For deeper detail than the \
snapshot has, call the appropriate read tool (search_knowledge_base for KB \
contents, etc).

Style:
  - Lead with the specific answer ("deal-intake is a hub agent in vc-dd-bots, \
running claude-sonnet-4-5, with 3 handoff connections to market-analyst, \
financial-analyst, team-analyst").
  - Follow with one line of context or next-step suggestion.
  - First person, professional, no emoji. Use markdown for structure (bullets \
when listing multiple items).
"""


# ─── Agent definitions table ───────────────────────────────────────

AGENTS: list[dict[str, Any]] = [
    {
        "name": "studio-router",
        "description": "Studio wheel HUB. Routes user turns to the right spoke or answers directly from the snapshot.",
        "system_prompt": ROUTER_PROMPT,
        "model_id": "claude-sonnet-4-6",
        "tool_policy": {
            "mode": "allowlist",
            "allowed": ["invoke_agent", "get_current_time"],
            "denied": [],
            "http_allowlist": [],
        },
        "canvas_position": {"x": 0, "y": 0},
        "max_turns": 6,
        "rate_limit_rpm": 60,
        "link_bonito_knowledge_kb": False,
    },
    {
        "name": "studio-builder",
        "description": "Studio wheel SPOKE. Emits plan cards (create/connect/link/mint). Runs via Origami passthrough since Bonobot agents don't have create_* tools yet.",
        "system_prompt": BUILDER_PROMPT,
        "model_id": "claude-sonnet-4-6",
        # Tool policy is `none` deliberately — this agent is a routing placeholder.
        # The Studio wheel dispatcher intercepts invocations of this agent and
        # routes the message to Origami's run_origami_turn() which has the
        # actual create_/connect_/link_/mint_ tools.
        "tool_policy": {"mode": "none", "allowed": [], "denied": [], "http_allowlist": []},
        "canvas_position": {"x": 400, "y": -200},
        "max_turns": 10,
        "rate_limit_rpm": 30,
        "link_bonito_knowledge_kb": False,
    },
    {
        "name": "studio-advisor",
        "description": "Studio wheel SPOKE. Suggests 2-3 concrete next-step prompts based on snapshot state.",
        "system_prompt": ADVISOR_PROMPT,
        "model_id": "claude-haiku-4-5",
        "tool_policy": {
            "mode": "allowlist",
            "allowed": ["get_current_time"],
            "denied": [],
            "http_allowlist": [],
        },
        "canvas_position": {"x": 400, "y": -70},
        "max_turns": 3,
        "rate_limit_rpm": 60,
        "link_bonito_knowledge_kb": False,
    },
    {
        "name": "studio-platform",
        "description": "Studio wheel SPOKE. Answers platform questions (Enterprise, SSO, integration, pricing) using bonito-knowledge KB.",
        "system_prompt": PLATFORM_PROMPT,
        "model_id": "claude-sonnet-4-6",
        "tool_policy": {
            "mode": "allowlist",
            "allowed": ["search_knowledge_base", "get_current_time"],
            "denied": [],
            "http_allowlist": [],
        },
        "canvas_position": {"x": 400, "y": 70},
        "max_turns": 5,
        "rate_limit_rpm": 30,
        "link_bonito_knowledge_kb": True,
    },
    {
        "name": "studio-explorer",
        "description": "Studio wheel SPOKE. Describes the user's own resources in detail (agents, KBs, projects).",
        "system_prompt": EXPLORER_PROMPT,
        "model_id": "claude-haiku-4-5",
        "tool_policy": {
            "mode": "allowlist",
            "allowed": ["search_knowledge_base", "get_current_time"],
            "denied": [],
            "http_allowlist": [],
        },
        "canvas_position": {"x": 400, "y": 200},
        "max_turns": 5,
        "rate_limit_rpm": 60,
        "link_bonito_knowledge_kb": False,
    },
]


CONNECTIONS = [
    ("studio-router", "studio-builder", "build / write actions"),
    ("studio-router", "studio-advisor", "what's next / lost"),
    ("studio-router", "studio-platform", "platform Q&A"),
    ("studio-router", "studio-explorer", "describe own resources"),
]


PROJECT_NAME = "studio-wheel"
PROJECT_DESCRIPTION = (
    "The Bonito Studio wheel — router + 4 specialist spokes that power the "
    "Studio chat surface. Built on Bonito itself as dogfood + a working "
    "reference for customers."
)


# ─── HTTP helpers ──────────────────────────────────────────────────


def headers(pat: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json",
    }


def get(client: httpx.Client, api_url: str, path: str, pat: str) -> Any:
    r = client.get(f"{api_url}{path}", headers=headers(pat), timeout=20)
    r.raise_for_status()
    return r.json()


def post(client: httpx.Client, api_url: str, path: str, pat: str, body: dict) -> Any:
    r = client.post(f"{api_url}{path}", headers=headers(pat), json=body, timeout=30)
    if r.status_code >= 400:
        print(f"  ❌ POST {path} → {r.status_code}: {r.text[:400]}", file=sys.stderr)
        r.raise_for_status()
    return r.json()


# ─── Idempotent helpers ────────────────────────────────────────────


def find_or_create_project(client: httpx.Client, api_url: str, pat: str) -> dict:
    projects = get(client, api_url, "/api/projects", pat)
    for p in projects:
        if p.get("name") == PROJECT_NAME:
            print(f"✓ project {PROJECT_NAME} exists ({p['id']})")
            return p
    print(f"➕ creating project {PROJECT_NAME}")
    return post(
        client, api_url, "/api/projects", pat,
        {"name": PROJECT_NAME, "description": PROJECT_DESCRIPTION},
    )


def list_project_agents(
    client: httpx.Client, api_url: str, pat: str, project_id: str
) -> list[dict]:
    return get(client, api_url, f"/api/projects/{project_id}/agents", pat)


def find_bonito_knowledge_kb(
    client: httpx.Client, api_url: str, pat: str
) -> Optional[str]:
    """Return the bonito-knowledge KB id if present in the org, else None."""
    try:
        kbs = get(client, api_url, "/api/knowledge-bases", pat)
        for kb in kbs:
            if kb.get("name") == "bonito-knowledge":
                return kb["id"]
    except Exception as e:
        print(f"  (couldn't list KBs — {e}; platform agent will run without KB link)")
    return None


def ensure_agent(
    client: httpx.Client,
    api_url: str,
    pat: str,
    project_id: str,
    existing_agents: list[dict],
    spec: dict,
    kb_ids: list[str],
) -> dict:
    for a in existing_agents:
        if a.get("name") == spec["name"]:
            print(f"✓ agent {spec['name']} exists ({a['id']})")
            return a
    print(f"➕ creating agent {spec['name']} (model={spec['model_id']})")
    body = {
        "name": spec["name"],
        "description": spec["description"],
        "system_prompt": spec["system_prompt"],
        "model_id": spec["model_id"],
        "tool_policy": spec["tool_policy"],
        "max_turns": spec.get("max_turns", 25),
        "rate_limit_rpm": spec.get("rate_limit_rpm", 30),
        "canvas_position": spec.get("canvas_position"),
    }
    if spec.get("link_bonito_knowledge_kb") and kb_ids:
        body["knowledge_base_ids"] = kb_ids
    return post(
        client, api_url, f"/api/projects/{project_id}/agents", pat, body
    )


def list_agent_connections(
    client: httpx.Client, api_url: str, pat: str, agent_id: str
) -> list[dict]:
    """Return outbound connections from this agent."""
    try:
        return get(
            client, api_url, f"/api/agents/{agent_id}/connections", pat
        )
    except Exception:
        return []


def ensure_connection(
    client: httpx.Client,
    api_url: str,
    pat: str,
    source_agent_id: str,
    target_agent_id: str,
    label: str,
) -> None:
    existing = list_agent_connections(client, api_url, pat, source_agent_id)
    for c in existing:
        if c.get("target_agent_id") == target_agent_id:
            print(f"  ✓ handoff {label} exists")
            return
    print(f"  ➕ wiring handoff {label}")
    post(
        client, api_url,
        f"/api/agents/{source_agent_id}/connections", pat,
        {
            "target_agent_id": target_agent_id,
            "connection_type": "handoff",
            "label": label,
            "enabled": True,
        },
    )


# ─── Main ──────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", required=True, help="e.g. http://localhost:8001")
    parser.add_argument("--pat", required=True, help="bp- PAT or JWT bearer token")
    args = parser.parse_args()

    api_url = args.api_url.rstrip("/")
    pat = args.pat

    print(f"\n▸ Setting up Studio wheel against {api_url}")
    print(f"  (auth: {pat[:10]}…{pat[-4:]})\n")

    with httpx.Client() as client:
        # Step 1: project
        project = find_or_create_project(client, api_url, pat)
        project_id = project["id"]

        # Step 2: bonito-knowledge KB lookup (optional)
        kb_id = find_bonito_knowledge_kb(client, api_url, pat)
        kb_ids = [kb_id] if kb_id else []
        if kb_id:
            print(f"✓ bonito-knowledge KB found ({kb_id}) — platform agent will link to it")
        else:
            print("⚠ no bonito-knowledge KB in this org — platform agent will run KB-less")

        # Step 3: agents
        existing = list_project_agents(client, api_url, pat, project_id)
        agents_by_name: dict[str, dict] = {}
        for spec in AGENTS:
            agents_by_name[spec["name"]] = ensure_agent(
                client, api_url, pat, project_id, existing, spec, kb_ids,
            )

        # Step 4: connections
        print("\n▸ Wiring handoff connections")
        for src_name, tgt_name, label in CONNECTIONS:
            src = agents_by_name[src_name]
            tgt = agents_by_name[tgt_name]
            ensure_connection(client, api_url, pat, src["id"], tgt["id"], label)

        # Step 5: print UUIDs for app config
        print("\n=== Studio wheel ready ===")
        print(f"project_id: {project_id}")
        for name in [
            "studio-router",
            "studio-builder",
            "studio-advisor",
            "studio-platform",
            "studio-explorer",
        ]:
            print(f"{name}: {agents_by_name[name]['id']}")
        print()
        print("Cache these UUIDs into app/services/studio/wheel.py via env or DB so")
        print("the dispatcher can find the router on /api/studio/turn requests.")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
