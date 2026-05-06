"""Agent approval workflow commands."""

from __future__ import annotations

import json as _json
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Prompt

from ..api import api, APIError
from ..utils.auth import ensure_authenticated
from ..utils.display import (
    get_output_format,
    print_error,
    print_info,
    print_success,
    print_table,
    print_dict_as_table,
    format_timestamp,
)

console = Console()
app = typer.Typer(help="Agent approval queue and human-in-the-loop workflows")


# -- list-pending ------------------------------------------------------


@app.command("list-pending")
def list_pending(
    org_id: str = typer.Option(..., "--org", help="Organization ID"),
    agent_id: Optional[str] = typer.Option(None, "--agent", help="Filter by agent ID"),
    risk_level: Optional[str] = typer.Option(None, "--risk", help="Filter by risk level (low/medium/high/critical)"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max results"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List pending approval actions."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    params = {"limit": limit}
    if agent_id:
        params["agent_id"] = agent_id
    if risk_level:
        params["risk_level"] = risk_level

    try:
        with console.status("[cyan]Fetching pending approvals...[/cyan]"):
            items = api.get(f"/organizations/{org_id}/approvals/queue", params=params)

        if fmt == "json":
            console.print_json(_json.dumps(items, default=str))
        else:
            if items:
                data = [
                    {
                        "ID": str(i.get("id", ""))[:8] + "...",
                        "Agent": i.get("agent_name", ""),
                        "Action": i.get("action_type", ""),
                        "Risk": i.get("risk_level", ""),
                        "Requester": i.get("requester_name", "") or "",
                        "Created": format_timestamp(i.get("created_at")),
                    }
                    for i in items
                ]
                print_table(data, title="Pending Approvals")
                print_info(f"{len(items)} pending action(s)")
            else:
                print_info("No pending approvals.")
    except APIError as exc:
        print_error(f"Failed to list pending approvals: {exc}")


# -- approve -----------------------------------------------------------


@app.command("approve")
def approve(
    action_id: str = typer.Argument(..., help="Approval action ID"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="Review notes"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Approve a pending action."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    body = {"action": "approve"}
    if notes:
        body["review_notes"] = notes

    try:
        with console.status("[cyan]Approving action...[/cyan]"):
            result = api.post(f"/approvals/{action_id}/review", body)

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            print_success(f"Action {action_id} approved")
    except APIError as exc:
        print_error(f"Failed to approve action: {exc}")


# -- reject ------------------------------------------------------------


@app.command("reject")
def reject(
    action_id: str = typer.Argument(..., help="Approval action ID"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="Rejection reason"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Reject a pending action."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    body = {"action": "reject"}
    if notes:
        body["review_notes"] = notes

    try:
        with console.status("[cyan]Rejecting action...[/cyan]"):
            result = api.post(f"/approvals/{action_id}/review", body)

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            print_success(f"Action {action_id} rejected")
    except APIError as exc:
        print_error(f"Failed to reject action: {exc}")


# -- get-config --------------------------------------------------------


@app.command("get-config")
def get_config(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List approval configs for an agent."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching approval configs...[/cyan]"):
            configs = api.get(f"/agents/{agent_id}/approval-configs")

        if fmt == "json":
            console.print_json(_json.dumps(configs, default=str))
        else:
            if configs:
                data = [
                    {
                        "ID": str(c.get("id", ""))[:8] + "...",
                        "Action Type": c.get("action_type", ""),
                        "Requires Approval": "Yes" if c.get("requires_approval") else "No",
                        "Timeout (hrs)": str(c.get("timeout_hours", "")),
                        "Required Approvers": str(c.get("required_approvers", 1)),
                    }
                    for c in configs
                ]
                print_table(data, title="Approval Configs")
            else:
                print_info("No approval configs found for this agent.")
    except APIError as exc:
        print_error(f"Failed to get approval configs: {exc}")


# -- update-config -----------------------------------------------------


@app.command("update-config")
def update_config(
    config_id: str = typer.Argument(..., help="Approval config ID"),
    requires_approval: Optional[bool] = typer.Option(None, "--requires-approval", help="Whether approval is required"),
    timeout_hours: Optional[int] = typer.Option(None, "--timeout-hours", help="Approval timeout in hours"),
    required_approvers: Optional[int] = typer.Option(None, "--required-approvers", help="Number of required approvers"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Update an approval configuration."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    body = {}
    if requires_approval is not None:
        body["requires_approval"] = requires_approval
    if timeout_hours is not None:
        body["timeout_hours"] = timeout_hours
    if required_approvers is not None:
        body["required_approvers"] = required_approvers

    if not body:
        print_error("No updates specified")
        return

    try:
        with console.status("[cyan]Updating approval config...[/cyan]"):
            result = api.put(f"/approval-configs/{config_id}", body)

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            print_success("Approval config updated successfully")
    except APIError as exc:
        print_error(f"Failed to update approval config: {exc}")
