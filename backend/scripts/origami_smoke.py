"""Origami smoke test — verify orchestrator emits tool_use, not text fallback.

Runs a non-destructive `list_org_state` prompt against POST /api/origami/turn,
streams the SSE response, and asserts that the orchestrator either invoked
a tool OR materialized a plan card. Fails loudly if it hits the silent-
response fallback ("I didn't quite catch that...") that KNOWN-ISSUES #38
documents.

Background
----------
This was the regression that bit prod hard on 2026-06-09: model alias gap +
bare-function-call parser miss + Bedrock fallback path all combined to make
Origami return its hardcoded fallback line for nearly every prompt. The fix
(commit 904eae5) landed three small changes. This smoke test prevents the
same class of bug from sneaking back in unnoticed.

Usage
-----
  # Against local dev (default)
  python -m scripts.origami_smoke

  # Against prod
  BONITO_API_URL=https://api.getbonito.com \
    BONITO_SMOKE_PAT=bp-... \
    python -m scripts.origami_smoke

  # Wired into a post-deploy step
  python -m scripts.origami_smoke --quiet || alert_on_call_team

Exit codes
----------
  0 — passed (orchestrator invoked a tool OR produced a plan card)
  1 — failed (silent-response fallback fired, or stream errored)
  2 — config error (missing token, unreachable host)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from typing import Optional

import httpx


# A prompt with one clear right answer: invoke the read-only list_org_state
# tool. Read-only on purpose so the smoke test never mutates anything.
SMOKE_PROMPT = "what providers do I have connected?"

# Hard cap: a healthy Origami turn finishes in under 20s for a single tool.
DEFAULT_TIMEOUT_S = 60.0


async def run_smoke(
    base_url: str,
    pat: str,
    timeout_s: float,
    verbose: bool,
) -> dict:
    """POST a smoke prompt, stream SSE, return a verdict dict."""
    url = f"{base_url.rstrip('/')}/api/origami/turn"
    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    body = {
        "message": SMOKE_PROMPT,
        "conversation_id": None,
    }

    verdict = {
        "pass": False,
        "reason": "no events received",
        "events_seen": [],
        "elapsed_s": 0.0,
        "fallback_emitted": False,
        "tool_started": False,
        "plan_ready": False,
        "error_event": None,
    }
    start = time.time()

    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            async with client.stream("POST", url, headers=headers, json=body) as resp:
                if resp.status_code != 200:
                    body_text = (await resp.aread()).decode("utf-8", errors="replace")[:300]
                    verdict["reason"] = f"HTTP {resp.status_code}: {body_text}"
                    return verdict

                current_event: Optional[str] = None
                async for raw_line in resp.aiter_lines():
                    line = raw_line.strip()
                    if not line:
                        current_event = None
                        continue
                    if line.startswith("event:"):
                        current_event = line[len("event:"):].strip()
                        continue
                    if not line.startswith("data:"):
                        continue
                    data_str = line[len("data:"):].strip()
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    if current_event:
                        verdict["events_seen"].append(current_event)

                    if verbose:
                        snippet = json.dumps(data)[:120]
                        print(f"  [{current_event or '?'}] {snippet}")

                    if current_event == "tool_started":
                        verdict["tool_started"] = True
                    elif current_event == "plan_ready":
                        verdict["plan_ready"] = True
                    elif current_event == "message_complete" and data.get("fallback"):
                        verdict["fallback_emitted"] = True
                    elif current_event == "error":
                        verdict["error_event"] = data.get("error") or data.get("message")

                    if current_event == "done":
                        break

    except httpx.ConnectError as e:
        verdict["reason"] = f"connect error: {e}"
        return verdict
    except httpx.ReadTimeout:
        verdict["reason"] = f"stream timed out after {timeout_s}s"
        return verdict
    except Exception as e:
        verdict["reason"] = f"{type(e).__name__}: {e}"
        return verdict
    finally:
        verdict["elapsed_s"] = round(time.time() - start, 2)

    # Pass condition: at least one tool invocation OR a plan card emission,
    # AND no fallback message, AND no error event.
    if verdict["fallback_emitted"]:
        verdict["reason"] = "fallback message emitted — silent-response regression"
    elif verdict["error_event"]:
        verdict["reason"] = f"error event: {verdict['error_event']}"
    elif verdict["tool_started"] or verdict["plan_ready"]:
        verdict["pass"] = True
        verdict["reason"] = (
            "tool_started seen" if verdict["tool_started"] else "plan_ready seen"
        )
    else:
        verdict["reason"] = (
            "no tool_started, no plan_ready, no fallback — orchestrator did nothing"
        )

    return verdict


def print_verdict(verdict: dict, quiet: bool):
    status = "✅ PASS" if verdict["pass"] else "❌ FAIL"
    if quiet and verdict["pass"]:
        return
    print(f"\n{'='*60}")
    print(f"  Origami smoke test: {status}")
    print(f"{'='*60}")
    print(f"  Reason:           {verdict['reason']}")
    print(f"  Elapsed:          {verdict['elapsed_s']}s")
    print(f"  Tool started:     {verdict['tool_started']}")
    print(f"  Plan ready:       {verdict['plan_ready']}")
    print(f"  Fallback fired:   {verdict['fallback_emitted']}")
    print(f"  Error event:      {verdict['error_event'] or '—'}")
    if verdict["events_seen"]:
        counts: dict[str, int] = {}
        for e in verdict["events_seen"]:
            counts[e] = counts.get(e, 0) + 1
        print(f"  Events seen:      " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    print()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--url",
        default=os.environ.get("BONITO_API_URL", "http://localhost:8001"),
        help="Bonito backend base URL (env: BONITO_API_URL)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("BONITO_SMOKE_PAT"),
        help="bp- PAT to authenticate the smoke turn (env: BONITO_SMOKE_PAT)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_S,
        help=f"Max seconds to wait for the stream (default {DEFAULT_TIMEOUT_S})",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print each SSE event as it arrives",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="On success, print nothing. On failure, print the verdict and exit 1.",
    )
    args = parser.parse_args()

    if not args.token:
        print(
            "✗ no token provided. Set BONITO_SMOKE_PAT (a bp- PAT) or pass --token.",
            file=sys.stderr,
        )
        sys.exit(2)
    if not args.token.startswith("bp-"):
        print(
            f"✗ token must start with 'bp-' (got prefix '{args.token[:3]}').",
            file=sys.stderr,
        )
        sys.exit(2)

    verdict = asyncio.run(
        run_smoke(args.url, args.token, args.timeout, args.verbose)
    )
    print_verdict(verdict, args.quiet)
    sys.exit(0 if verdict["pass"] else 1)


if __name__ == "__main__":
    main()
