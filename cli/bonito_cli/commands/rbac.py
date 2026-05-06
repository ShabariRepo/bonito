"""RBAC (Role-Based Access Control) management commands."""

from __future__ import annotations

import json as _json
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Confirm

from ..api import api, APIError
from ..utils.auth import ensure_authenticated
from ..utils.display import (
    get_output_format,
    print_error,
    print_info,
    print_success,
    print_table,
    print_dict_as_table,
)

console = Console()
app = typer.Typer(help="Role-based access control management")


# -- list-roles --------------------------------------------------------


@app.command("list-roles")
def list_roles(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all roles in the organization."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching roles...[/cyan]"):
            roles = api.get("/roles")

        if fmt == "json":
            console.print_json(_json.dumps(roles, default=str))
        else:
            if roles:
                data = [
                    {
                        "ID": str(r.get("id", ""))[:8] + "...",
                        "Name": r.get("name", ""),
                        "Description": (r.get("description") or "")[:40] or "",
                        "Managed": "Yes" if r.get("is_managed") else "No",
                        "Permissions": str(len(r.get("permissions", []))),
                    }
                    for r in roles
                ]
                print_table(data, title="Roles")
                print_info(f"{len(roles)} role(s)")
            else:
                print_info("No roles found.")
    except APIError as exc:
        print_error(f"Failed to list roles: {exc}")


# -- assign-role -------------------------------------------------------


@app.command("assign-role")
def assign_role(
    user_id: str = typer.Option(..., "--user", "-u", help="User ID"),
    role_id: str = typer.Option(..., "--role", "-r", help="Role ID"),
    scope_type: str = typer.Option("org", "--scope-type", help="Scope type: org, project, or group"),
    scope_id: Optional[str] = typer.Option(None, "--scope-id", help="Scope ID (required for project/group scope)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Assign a role to a user."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    body = {
        "user_id": user_id,
        "role_id": role_id,
        "scope_type": scope_type,
    }
    if scope_id:
        body["scope_id"] = scope_id

    try:
        with console.status("[cyan]Assigning role...[/cyan]"):
            result = api.post("/role-assignments", body)

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            print_success(f"Role assigned successfully (assignment ID: {result.get('id', 'N/A')})")
    except APIError as exc:
        print_error(f"Failed to assign role: {exc}")


# -- remove-role -------------------------------------------------------


@app.command("remove-role")
def remove_role(
    assignment_id: str = typer.Argument(..., help="Role assignment ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Remove a role assignment."""
    ensure_authenticated()

    if not yes:
        confirmed = Confirm.ask(f"[yellow]Remove role assignment '{assignment_id}'?[/yellow]")
        if not confirmed:
            print_info("Cancelled")
            raise typer.Exit(0)

    try:
        with console.status("[cyan]Removing role assignment...[/cyan]"):
            api.delete(f"/role-assignments/{assignment_id}")

        print_success("Role assignment removed successfully")
    except APIError as exc:
        print_error(f"Failed to remove role assignment: {exc}")


# -- list-permissions --------------------------------------------------


@app.command("list-permissions")
def list_permissions(
    user_id: str = typer.Argument(..., help="User ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List effective permissions for a user."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching permissions...[/cyan]"):
            result = api.get(f"/users/{user_id}/permissions")

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            permissions = result.get("permissions", [])
            if permissions:
                data = [
                    {
                        "Resource": p.get("resource", ""),
                        "Action": p.get("action", ""),
                        "Scope Type": p.get("scope", {}).get("type", ""),
                        "Scope ID": str(p.get("scope", {}).get("id", ""))[:8] + "..." if p.get("scope", {}).get("id") else "all",
                    }
                    for p in permissions
                ]
                print_table(data, title="User Permissions")
            else:
                print_info("No permissions found for this user.")

            assignments = result.get("role_assignments", [])
            if assignments:
                assign_data = [
                    {
                        "Role": a.get("role_name", ""),
                        "Scope Type": a.get("scope_type", ""),
                        "Scope Name": a.get("scope_name", "") or "all",
                    }
                    for a in assignments
                ]
                print_table(assign_data, title="Role Assignments")
    except APIError as exc:
        print_error(f"Failed to list permissions: {exc}")
