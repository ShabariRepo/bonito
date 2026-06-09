#!/usr/bin/env python3
"""origami-overage-report.py — dry-run report of Origami turn-overage charges.

Until Stripe is wired in, this is the function ops uses to see what
WOULD be charged for the current month. After Stripe is set up, the
same function is the source of truth for the metered-billing webhook.

Outputs a per-org row showing tier, turns used, cap, overage turns, and
the dollar amount that would be charged. Run on the 1st of each month
for the prior month's reconciliation, or whenever to inspect the
current month so far.

Run from `backend/` so module imports resolve:

    cd backend
    python -m scripts.origami_overage_report                       # all orgs, current month
    python -m scripts.origami_overage_report --month 2026-05      # specific month
    python -m scripts.origami_overage_report --org-id <uuid>      # one org

Docker form:

    docker compose exec backend python -m scripts.origami_overage_report
"""

from __future__ import annotations

import argparse
import asyncio
import calendar
import sys
import uuid
from datetime import datetime, timezone


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--month",
        default=None,
        help="YYYY-MM (e.g. '2026-05'). Default: current month so far.",
    )
    ap.add_argument(
        "--org-id",
        default=None,
        help="Restrict to a single org by UUID. Default: every org with org_id-tagged turns.",
    )
    args = ap.parse_args()

    from app.core.database import async_session
    from app.models.organization import Organization
    from app.models.origami_logs import OrigamiTurnLog
    from app.services.origami.metering import get_period_overage, get_current_month_overage
    from app.services.feature_gate import feature_gate
    from sqlalchemy import select

    async with async_session() as db:
        # Resolve period bounds
        if args.month:
            try:
                y, m = (int(x) for x in args.month.split("-"))
            except (ValueError, IndexError):
                print(f"error: --month must be YYYY-MM, got {args.month!r}", file=sys.stderr)
                return 2
            start = datetime(y, m, 1, tzinfo=timezone.utc)
            last_day = calendar.monthrange(y, m)[1]
            end = datetime(y, m, last_day, 23, 59, 59, tzinfo=timezone.utc)
        else:
            start = None
            end = None

        # Discover orgs to report on
        if args.org_id:
            try:
                org_ids = [uuid.UUID(args.org_id)]
            except ValueError:
                print(f"error: --org-id must be a valid UUID, got {args.org_id!r}", file=sys.stderr)
                return 2
        else:
            r = await db.execute(
                select(OrigamiTurnLog.org_id).distinct()
            )
            org_ids = [row[0] for row in r.all()]

        rows = []
        for oid in org_ids:
            try:
                sub = await feature_gate.get_organization_subscription(db, str(oid))
                tier = (
                    sub["tier"].value
                    if hasattr(sub["tier"], "value")
                    else str(sub["tier"])
                )
            except Exception:
                tier = "free"

            if start and end:
                summary = await get_period_overage(db, oid, tier, start, end)
            else:
                summary = await get_current_month_overage(db, oid, tier)
            rows.append((oid, tier, summary))

        # Render
        print()
        print(f"{'org_id':<38}  {'tier':<10}  {'turns':>6}  {'cap':>6}  {'over':>5}  {'rate':>6}  {'amount':>9}")
        print("-" * 100)
        total_overage = 0.0
        for oid, tier, s in rows:
            cap = s.get("tier_cap")
            cap_s = str(cap) if cap is not None else "∞"
            amount = s.get("overage_amount_usd", 0.0) or 0.0
            print(
                f"{str(oid):<38}  {tier:<10}  "
                f"{s['turns_total']:>6}  {cap_s:>6}  "
                f"{s['overage_turns']:>5}  ${s['overage_rate_usd']:>5.2f}  "
                f"${amount:>8.2f}"
            )
            total_overage += amount
        print("-" * 100)
        print(f"{'TOTAL':<87}  ${total_overage:>8.2f}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
