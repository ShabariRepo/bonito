#!/usr/bin/env python3
"""care-package.py — generate a sendable customer-care package.

After a discovery call or kickoff, Bonito sends prospects a short package:
intro letter, getting-started guide, contact card, pricing one-pager.
This script scaffolds that bundle so we don't reassemble it by hand each
deal.

Output goes under ~/Desktop/Projects/Bonito AI/documentation/<slug>/
alongside whatever HTML briefs already live there. Safe to re-run — files
are written with a `.generated.md` suffix so manual edits in the same
folder don't get clobbered.

Usage:
    python3 scripts/care-package.py \\
        --customer "Acme Corp" \\
        --contact "Jane Doe" \\
        --email "jane@acme.com" \\
        --tier pro \\
        --notes "Eval focused on multi-cloud failover"

Required flags: --customer
Everything else is optional and falls back to TBD placeholders.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

DOCS_ROOT = Path(
    os.path.expanduser("~/Desktop/Projects/Bonito AI/documentation")
)

TIERS = {
    "free": "Free — 25K requests/mo, 3 providers, 3 seats, 1 agent",
    "starter": "Starter ($199/mo) — 100K requests/mo, 3 providers, 5 seats, 2 agents, RAG (2 KBs)",
    "pro": "Pro ($999/mo) — 500K requests/mo, 5 providers, unlimited seats, 5 agents, advanced routing, RAG (5 KBs)",
    "enterprise": "Enterprise ($10K-$20K/mo) — unlimited everything, SSO/SAML, RBAC, compliance, 99.9% SLA",
    "scale": "Scale (custom, $200K+/yr) — dedicated infra, multi-region, 99.99% SLA, dedicated account team",
}


def slugify(name: str) -> str:
    """Turn 'Acme Corp Ltd.' into 'acme-corp-ltd'."""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s or "customer"


def render(template: str, **kwargs) -> str:
    """Tiny templater. Replaces {{key}} with kwargs[key]."""
    for k, v in kwargs.items():
        template = template.replace("{{" + k + "}}", str(v))
    return template


INTRO_LETTER = dedent("""\
    # Welcome to Bonito, {{customer}}

    Hey {{contact_first}},

    Thanks for the time on the call. This folder has everything you need
    to get rolling: a getting-started guide for the first few hours of
    use, a contact card so you know who to reach for what, and a quick
    pricing reference for the {{tier_name}} tier.

    A few things worth knowing:

    - Bonito routes through your cloud provider credentials, never ours.
      Your inference traffic stays in your AWS / Azure / GCP account.
    - Audit logs are on by default. Everything is queryable per org.
    - The CLI (`bonito-cli` on PyPI) does almost everything the dashboard
      does, plus a few things it doesn't (programmatic agent deploys,
      bulk KB ingestion, etc.).

    {{notes_block}}

    If anything in here is unclear, reply to this thread and we'll fix it.

    Cheers,
    Shabari
    shabari@bonito.ai

    ---
    Package generated {{generated_at}} for {{customer}}.
""")


GETTING_STARTED = dedent("""\
    # Getting Started — {{customer}}

    First-hour checklist. Each step links to where to click.

    ## 1. Connect a cloud provider (5 min)

    Settings → Providers → Connect. We support six:

    - AWS Bedrock (auto cross-region inference)
    - Azure AI Foundry / Azure OpenAI
    - Google Vertex AI
    - OpenAI (direct)
    - Anthropic (direct)
    - Groq

    You can connect more than one. Bonito will route between them based
    on the policy you set.

    ## 2. Mint a gateway key (1 min)

    Settings → API Keys → Create. The key starts with `bn-`. Use it as a
    drop-in OpenAI-compatible API key in any client:

    ```bash
    curl https://api.getbonito.com/v1/chat/completions \\
        -H "Authorization: Bearer $BONITO_KEY" \\
        -H "Content-Type: application/json" \\
        -d '{"model": "claude-sonnet-4-5", "messages": [{"role":"user","content":"hi"}]}'
    ```

    Same shape as OpenAI. No code changes needed if you're already on
    OpenAI's SDK.

    ## 3. Set up a Knowledge Base (5 min)

    Knowledge → New KB → Upload documents (PDF, DOCX, MD, etc). The
    ingestion pipeline chunks and embeds them. Once ready, attach the KB
    to an agent or include it as context in gateway calls.

    ## 4. Deploy your first agent (10 min)

    Agents → New Agent. Pick a model, write a system prompt, attach KBs
    if you have them. The agent gets its own endpoint:

    ```bash
    curl https://api.getbonito.com/api/agents/{{tier_agent_demo_id}}/execute \\
        -H "Authorization: Bearer $BONITO_PAT" \\
        -H "Content-Type: application/json" \\
        -d '{"message": "what does your KB say about X?"}'
    ```

    ## 5. Hook up Origami (optional, 2 min)

    For non-technical teammates who shouldn't touch the dashboard:
    direct them to `/origami`. They can chat their way through creating
    projects, KBs, agents, and gateway keys without learning the UI.

    ## What's available on your tier

    {{tier_summary}}

    Need more headroom? Settings → Billing → Change Plan, or email
    shabari@bonito.ai.
""")


CONTACT_CARD = dedent("""\
    # Bonito Contacts — {{customer}}

    | Reason | Who | How |
    |---|---|---|
    | Bugs, integration help, anything urgent | Shabari Shenoy | shabari@bonito.ai |
    | Procurement, pricing, security review | Shabari Shenoy | shabari@bonito.ai |
    | Status page | (auto) | https://status.getbonito.com |
    | Docs | (auto) | https://docs.getbonito.com |

    SLA on your tier: {{sla}}.

    {{contact_extra_block}}
""")


PRICING_REFERENCE = dedent("""\
    # Pricing reference — {{customer}}

    Current tier: **{{tier_name}}**.

    {{tier_summary}}

    ## All tiers

    - **Free** — 25K requests/mo, 3 providers, 3 seats, 1 agent, invite-only
    - **Starter ($199/mo)** — 100K requests/mo, 3 providers, 5 seats, 2 agents, RAG (2 KBs), CLI, email support
    - **Pro ($999/mo)** — 500K requests/mo, 5 providers, unlimited seats, 5 agents, advanced routing, RAG (5 KBs)
    - **Enterprise ($10K-$20K/mo)** — unlimited everything, SSO/SAML, RBAC, compliance, 99.9% SLA, dedicated support
    - **Scale (custom)** — dedicated infra, multi-region, 99.99% SLA, dedicated account team

    Email shabari@bonito.ai for procurement or to negotiate a custom tier.
""")


def write_safe(path: Path, content: str) -> bool:
    """Write only if the target doesn't exist OR has the .generated.md suffix.

    Returns True if we wrote, False if we skipped to protect a manual edit.
    """
    if path.exists() and not str(path).endswith(".generated.md"):
        return False
    path.write_text(content, encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--customer", required=True, help="Company name (e.g. 'Acme Corp')")
    ap.add_argument("--contact", default="", help="Primary contact name")
    ap.add_argument("--email", default="", help="Primary contact email")
    ap.add_argument(
        "--tier",
        choices=sorted(TIERS.keys()),
        default="pro",
        help="Subscription tier (default: pro)",
    )
    ap.add_argument(
        "--notes",
        default="",
        help="Free-text deal context to weave into the intro letter",
    )
    ap.add_argument(
        "--out",
        default=str(DOCS_ROOT),
        help=f"Output root (default: {DOCS_ROOT})",
    )
    args = ap.parse_args()

    slug = slugify(args.customer)
    out_dir = Path(args.out) / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    contact_first = (args.contact.split()[0] if args.contact else "team").strip()
    tier_name = args.tier.capitalize() if args.tier != "pro" else "Pro"
    tier_summary = TIERS.get(args.tier, "TBD")
    sla_map = {
        "free": "Best-effort, community support",
        "starter": "Email support, 48h response target",
        "pro": "Email support, 24h response target",
        "enterprise": "99.9% uptime SLA, priority support",
        "scale": "99.99% uptime SLA, dedicated account team",
    }
    sla = sla_map.get(args.tier, "TBD")

    notes_block = (
        f"On the deal context you shared: {args.notes}"
        if args.notes
        else "Anything specific you want covered in onboarding? Reply with what you need and we'll prep it."
    )

    contact_extra_block = (
        f"Primary contact on your side: **{args.contact}** ({args.email})."
        if args.contact and args.email
        else "Tell us who the technical point person is on your side and we'll flag any issues to them directly."
    )

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    ctx = {
        "customer": args.customer,
        "contact_first": contact_first,
        "tier_name": tier_name,
        "tier_summary": tier_summary,
        "tier_agent_demo_id": "<agent_id>",
        "notes_block": notes_block,
        "sla": sla,
        "contact_extra_block": contact_extra_block,
        "generated_at": generated_at,
    }

    files = {
        "00-intro-letter.generated.md": render(INTRO_LETTER, **ctx),
        "01-getting-started.generated.md": render(GETTING_STARTED, **ctx),
        "02-contacts.generated.md": render(CONTACT_CARD, **ctx),
        "03-pricing-reference.generated.md": render(PRICING_REFERENCE, **ctx),
    }

    written = []
    skipped = []
    for name, content in files.items():
        path = out_dir / name
        if write_safe(path, content):
            written.append(name)
        else:
            skipped.append(name)

    print(f"\nCare package for {args.customer} → {out_dir}\n")
    for name in written:
        print(f"  ✓ {name}")
    for name in skipped:
        print(f"  · {name} (skipped, file exists without .generated.md suffix)")
    if not written:
        print("  (nothing new written)")
    print("\nNext: review the .generated.md files, edit anything that needs")
    print("hand-tuning, then re-export as HTML or PDF if you want to send.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
