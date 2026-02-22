"""Admin CLI commands — user verification, tier management, org operations."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ..api import api, APIError
from ..utils.auth import ensure_authenticated
from ..utils.display import print_error, print_success, print_info, print_warning, get_output_format

console = Console()
app = typer.Typer(help="⚙️  Platform admin commands")


@app.command("verify-user")
def verify_user(
    email: str = typer.Option(..., "--email", "-e", help="Email of user to verify"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
):
    """
    Force-verify a user's email (admin only).

    Examples:
        bonito admin verify-user --email user@company.com
    """
    ensure_authenticated()
    try:
        with console.status("[cyan]Verifying user…[/cyan]"):
            result = api.post("/admin/users/verify-by-email", data={"email": email})
        if json_output:
            import json
            console.print_json(json.dumps(result, default=str))
        else:
            print_success(f"Verified: {result.get('email', email)} ✓")
    except APIError as exc:
        print_error(f"Failed to verify user: {exc}")
        raise typer.Exit(1)


@app.command("set-tier")
def set_tier(
    email: Optional[str] = typer.Option(None, "--email", "-e", help="User email (to look up org)"),
    org_id: Optional[str] = typer.Option(None, "--org", help="Organization ID"),
    tier: str = typer.Option(..., "--tier", "-t", help="Tier: free, pro, enterprise"),
    reason: str = typer.Option("Set via CLI", "--reason", help="Reason for tier change"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
):
    """
    Set an organization's subscription tier (admin only).

    Examples:
        bonito admin set-tier --email user@company.com --tier pro
        bonito admin set-tier --org ORG_UUID --tier enterprise
    """
    ensure_authenticated()

    if tier not in ("free", "pro", "enterprise"):
        print_error("Tier must be: free, pro, or enterprise")
        raise typer.Exit(1)

    if not org_id and not email:
        print_error("Provide --email or --org")
        raise typer.Exit(1)

    # Look up org by email if needed
    if email and not org_id:
        try:
            with console.status("[cyan]Looking up user…[/cyan]"):
                users = api.get("/admin/users")
            found = None
            for u in (users if isinstance(users, list) else users.get("users", [])):
                if u.get("email") == email:
                    found = u
                    break
            if not found:
                print_error(f"User not found: {email}")
                raise typer.Exit(1)
            org_id = found.get("org_id")
            if not org_id:
                print_error(f"No org_id for user {email}")
                raise typer.Exit(1)
            print_info(f"Found org: {org_id} ({found.get('org_name', '')})")
        except APIError as exc:
            print_error(f"Failed to look up user: {exc}")
            raise typer.Exit(1)

    try:
        with console.status(f"[cyan]Setting tier to {tier}…[/cyan]"):
            result = api.post("/subscription/update", data={
                "org_id": org_id,
                "tier": tier,
                "reason": reason,
            })
        if json_output:
            import json as _json
            console.print_json(_json.dumps(result, default=str))
        else:
            print_success(f"Tier set to {tier.upper()} for org {org_id}")
    except APIError as exc:
        print_error(f"Failed to set tier: {exc}")
        raise typer.Exit(1)


@app.command("list-users")
def list_users(
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
):
    """
    List all platform users (admin only).

    Examples:
        bonito admin list-users
        bonito admin list-users --json
    """
    ensure_authenticated()
    try:
        with console.status("[cyan]Fetching users…[/cyan]"):
            users = api.get("/admin/users")

        user_list = users if isinstance(users, list) else users.get("users", [])

        if json_output:
            import json
            console.print_json(json.dumps(user_list, default=str))
        else:
            table = Table(title="Platform Users")
            table.add_column("Email", style="cyan")
            table.add_column("Name")
            table.add_column("Role")
            table.add_column("Verified", justify="center")
            table.add_column("Org")
            table.add_column("Tier")

            for u in user_list:
                verified = "✅" if u.get("email_verified") else "❌"
                table.add_row(
                    u.get("email", ""),
                    u.get("name", ""),
                    u.get("role", ""),
                    verified,
                    u.get("org_name", ""),
                    u.get("subscription_tier", u.get("tier", "")),
                )
            console.print(table)
    except APIError as exc:
        print_error(f"Failed to list users: {exc}")
        raise typer.Exit(1)


@app.command("list-orgs")
def list_orgs(
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
):
    """
    List all organizations (admin only).

    Examples:
        bonito admin list-orgs
    """
    ensure_authenticated()
    try:
        with console.status("[cyan]Fetching organizations…[/cyan]"):
            orgs = api.get("/admin/organizations")

        org_list = orgs if isinstance(orgs, list) else orgs.get("organizations", [])

        if json_output:
            import json
            console.print_json(json.dumps(org_list, default=str))
        else:
            table = Table(title="Organizations")
            table.add_column("Name", style="cyan")
            table.add_column("ID")
            table.add_column("Tier")
            table.add_column("Members")

            for o in org_list:
                table.add_row(
                    o.get("name", ""),
                    str(o.get("id", "")),
                    o.get("subscription_tier", "free"),
                    str(o.get("member_count", "?")),
                )
            console.print(table)
    except APIError as exc:
        print_error(f"Failed to list orgs: {exc}")
        raise typer.Exit(1)


@app.command("delete-user")
def delete_user(
    email: Optional[str] = typer.Option(None, "--email", "-e", help="User email"),
    user_id: Optional[str] = typer.Option(None, "--id", help="User ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """
    Delete a user (admin only).

    Examples:
        bonito admin delete-user --email test@company.com
        bonito admin delete-user --id UUID --force
    """
    ensure_authenticated()

    if not email and not user_id:
        print_error("Provide --email or --id")
        raise typer.Exit(1)

    # Look up by email
    if email and not user_id:
        try:
            users = api.get("/admin/users")
            user_list = users if isinstance(users, list) else users.get("users", [])
            found = next((u for u in user_list if u.get("email") == email), None)
            if not found:
                print_error(f"User not found: {email}")
                raise typer.Exit(1)
            user_id = found["id"]
        except APIError as exc:
            print_error(f"Failed: {exc}")
            raise typer.Exit(1)

    if not force:
        confirm = typer.confirm(f"Delete user {email or user_id}? This cannot be undone")
        if not confirm:
            print_info("Cancelled.")
            raise typer.Exit(0)

    try:
        with console.status("[cyan]Deleting user…[/cyan]"):
            api.delete(f"/admin/users/{user_id}")
        print_success(f"Deleted user {email or user_id}")
    except APIError as exc:
        print_error(f"Failed to delete user: {exc}")
        raise typer.Exit(1)
