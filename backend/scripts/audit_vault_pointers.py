"""Audit + backfill provider credentials from Vault into the encrypted DB column.

Background
----------
Before 2026-05-24 the provider connection flow only wrote credentials to Vault
and stored a 'vault:providers/{uuid}' pointer in cloud_providers.credentials_encrypted.
After 2026-05-24 the flow writes to BOTH Vault and the AES-256-GCM encrypted DB
column. The Vault->DB fallback in _get_provider_secrets() explicitly skips rows
whose column starts with 'vault:' — meaning a Vault wipe silently breaks every
old provider with no way to recover (we hit this in dev on 2026-05-31).

This script:
  1. Counts providers vulnerable to a Vault wipe (column starts with 'vault:').
  2. Optionally backfills them — reads the live Vault secret and re-encrypts into
     the DB column. Vault stays the primary store; the DB column becomes the
     durable safety net.

Usage
-----
  # Dry run — count + per-provider report, no writes
  python -m scripts.audit_vault_pointers

  # Backfill (writes to DB, leaves Vault untouched)
  python -m scripts.audit_vault_pointers --apply

  # Limit to a single org for staged rollout
  python -m scripts.audit_vault_pointers --apply --org-id <uuid>
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select

from app.core.database import get_db_session
from app.core.encryption import encrypt_credentials
from app.core.vault import vault_client
from app.models.cloud_provider import CloudProvider


@dataclass
class ProviderRow:
    id: uuid.UUID
    org_id: uuid.UUID
    provider_type: str
    column_state: str  # 'vault_pointer' | 'encrypted' | 'plaintext_json' | 'null'


async def _classify_column(value: Optional[str]) -> str:
    if value is None or value == "":
        return "null"
    if value.startswith("vault:"):
        return "vault_pointer"
    # Plain JSON would parse; encrypted output is base64-ish opaque
    if value.startswith("{") and value.endswith("}"):
        return "plaintext_json"
    return "encrypted"


async def audit(org_id: Optional[uuid.UUID]) -> list[ProviderRow]:
    """Read every active provider, classify the column state."""
    async with get_db_session() as db:
        q = select(CloudProvider).where(CloudProvider.status == "active")
        if org_id:
            q = q.where(CloudProvider.org_id == org_id)
        rows = (await db.execute(q)).scalars().all()

    out: list[ProviderRow] = []
    for r in rows:
        state = await _classify_column(r.credentials_encrypted)
        out.append(ProviderRow(r.id, r.org_id, r.provider_type, state))
    return out


async def backfill(rows: list[ProviderRow], dry_run: bool) -> dict[str, int]:
    """For every vault_pointer row: read Vault, encrypt to DB column.

    Returns a counter dict: backfilled / skipped_empty_vault / errors.
    """
    secret_key = os.getenv("SECRET_KEY") or os.getenv("ENCRYPTION_KEY")
    if not secret_key:
        raise RuntimeError("SECRET_KEY (or ENCRYPTION_KEY) env var is required to encrypt DB column")

    counts = {"backfilled": 0, "skipped_empty_vault": 0, "errors": 0}
    vulnerable = [r for r in rows if r.column_state == "vault_pointer"]

    for row in vulnerable:
        try:
            secrets = await vault_client.get_secrets(f"providers/{row.id}")
        except Exception as e:
            print(f"  [error] {row.id} ({row.provider_type}): Vault read failed: {e}")
            counts["errors"] += 1
            continue

        if not secrets:
            # Vault is empty for this provider — nothing to encrypt. Skip rather
            # than overwrite the pointer with garbage. Customer must reconnect.
            print(f"  [empty]  {row.id} ({row.provider_type}): Vault has no entry — customer needs to reconnect")
            counts["skipped_empty_vault"] += 1
            continue

        if dry_run:
            keys = sorted(secrets.keys()) if isinstance(secrets, dict) else []
            print(f"  [DRY]    {row.id} ({row.provider_type}): would encrypt {len(keys)} keys ({', '.join(keys)})")
            counts["backfilled"] += 1
            continue

        # Apply: encrypt + UPDATE
        try:
            encrypted = encrypt_credentials(secrets, secret_key)
            async with get_db_session() as db:
                p = (await db.execute(
                    select(CloudProvider).where(CloudProvider.id == row.id)
                )).scalar_one()
                p.credentials_encrypted = encrypted
                await db.commit()
            print(f"  [ok]     {row.id} ({row.provider_type}): backfilled to DB column")
            counts["backfilled"] += 1
        except Exception as e:
            print(f"  [error]  {row.id} ({row.provider_type}): write failed: {e}")
            counts["errors"] += 1

    return counts


def _summarize(rows: list[ProviderRow]) -> dict[str, int]:
    counts = {"vault_pointer": 0, "encrypted": 0, "plaintext_json": 0, "null": 0}
    for r in rows:
        counts[r.column_state] += 1
    return counts


async def main(args: argparse.Namespace):
    org_id = uuid.UUID(args.org_id) if args.org_id else None

    print(f"\n{'='*64}")
    print(f"  Provider credential audit  ({'org=' + str(org_id) if org_id else 'all orgs'})")
    print(f"{'='*64}\n")

    rows = await audit(org_id)
    summary = _summarize(rows)
    total = len(rows)

    print(f"Active providers: {total}")
    print(f"  encrypted        {summary['encrypted']:>4}   (safe — DB column has AES-256-GCM creds)")
    print(f"  vault_pointer    {summary['vault_pointer']:>4}   (VULNERABLE — Vault wipe = customer loses gateway)")
    print(f"  plaintext_json   {summary['plaintext_json']:>4}   (legacy — auto-migrates on first read)")
    print(f"  null             {summary['null']:>4}   (no creds in column; reconnect required)")
    print()

    if summary["vault_pointer"] == 0:
        print("No vulnerable providers found. Nothing to backfill.\n")
        return

    if args.apply:
        print(f"Backfilling {summary['vault_pointer']} provider(s) — reading Vault, encrypting to DB column...\n")
    else:
        print(f"Dry run — would backfill {summary['vault_pointer']} provider(s). Pass --apply to write.\n")

    counts = await backfill(rows, dry_run=not args.apply)

    print(f"\n{'='*64}")
    print(f"  Result")
    print(f"{'='*64}")
    action = "Backfilled" if args.apply else "Would backfill"
    print(f"  {action}:                 {counts['backfilled']}")
    print(f"  Skipped (empty Vault):   {counts['skipped_empty_vault']}")
    print(f"  Errors:                  {counts['errors']}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="Write to DB (default is dry-run)")
    parser.add_argument("--org-id", type=str, default=None, help="Limit to a single org UUID")
    args = parser.parse_args()
    asyncio.run(main(args))
