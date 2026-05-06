"""Agent scheduling commands."""

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
    format_timestamp,
)

console = Console()
app = typer.Typer(help="Agent schedule management")


# -- list-schedules ----------------------------------------------------


@app.command("list")
def list_schedules(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all schedules for an agent."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching schedules...[/cyan]"):
            schedules = api.get(f"/agents/{agent_id}/schedules")

        if fmt == "json":
            console.print_json(_json.dumps(schedules, default=str))
        else:
            if schedules:
                data = [
                    {
                        "ID": str(s.get("id", ""))[:8] + "...",
                        "Name": s.get("name", ""),
                        "Cron": s.get("cron_expression", ""),
                        "Timezone": s.get("timezone", "UTC"),
                        "Enabled": "Yes" if s.get("enabled") else "No",
                        "Runs": str(s.get("run_count", 0)),
                        "Next Run": format_timestamp(s.get("next_run_at")),
                    }
                    for s in schedules
                ]
                print_table(data, title="Agent Schedules")
                print_info(f"{len(schedules)} schedule(s)")
            else:
                print_info("No schedules found for this agent.")
    except APIError as exc:
        print_error(f"Failed to list schedules: {exc}")


# -- create ------------------------------------------------------------


@app.command("create")
def create_schedule(
    agent_id: str = typer.Option(..., "--agent", "-a", help="Agent ID"),
    name: str = typer.Option(..., "--name", "-n", help="Schedule name"),
    cron: str = typer.Option(..., "--cron", "-c", help="Cron expression (e.g. '0 9 * * 1-5')"),
    prompt: str = typer.Option(..., "--prompt", "-p", help="Task prompt"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Schedule description"),
    timezone: str = typer.Option("UTC", "--timezone", help="Timezone (e.g. America/New_York)"),
    enabled: bool = typer.Option(True, "--enabled/--disabled", help="Enable the schedule"),
    max_retries: int = typer.Option(0, "--max-retries", help="Maximum retry attempts"),
    timeout_minutes: int = typer.Option(30, "--timeout", help="Execution timeout in minutes"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Create a new agent schedule."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    body = {
        "name": name,
        "cron_expression": cron,
        "task_prompt": prompt,
        "timezone": timezone,
        "enabled": enabled,
        "max_retries": max_retries,
        "timeout_minutes": timeout_minutes,
    }
    if description:
        body["description"] = description

    try:
        with console.status("[cyan]Creating schedule...[/cyan]"):
            result = api.post(f"/agents/{agent_id}/schedules", body)

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            print_success(f"Schedule '{name}' created (ID: {result.get('id', 'N/A')})")
    except APIError as exc:
        print_error(f"Failed to create schedule: {exc}")


# -- update ------------------------------------------------------------


@app.command("update")
def update_schedule(
    schedule_id: str = typer.Argument(..., help="Schedule ID"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Update name"),
    cron: Optional[str] = typer.Option(None, "--cron", "-c", help="Update cron expression"),
    prompt: Optional[str] = typer.Option(None, "--prompt", "-p", help="Update task prompt"),
    timezone: Optional[str] = typer.Option(None, "--timezone", help="Update timezone"),
    enabled: Optional[bool] = typer.Option(None, "--enabled/--disabled", help="Enable or disable"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Update an existing schedule."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    body = {}
    if name is not None:
        body["name"] = name
    if cron is not None:
        body["cron_expression"] = cron
    if prompt is not None:
        body["task_prompt"] = prompt
    if timezone is not None:
        body["timezone"] = timezone
    if enabled is not None:
        body["enabled"] = enabled

    if not body:
        print_error("No updates specified")
        return

    try:
        with console.status("[cyan]Updating schedule...[/cyan]"):
            result = api.put(f"/schedules/{schedule_id}", body)

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            print_success("Schedule updated successfully")
    except APIError as exc:
        print_error(f"Failed to update schedule: {exc}")


# -- delete ------------------------------------------------------------


@app.command("delete")
def delete_schedule(
    schedule_id: str = typer.Argument(..., help="Schedule ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete a schedule."""
    ensure_authenticated()

    if not yes:
        confirmed = Confirm.ask(f"[yellow]Delete schedule '{schedule_id}'?[/yellow]")
        if not confirmed:
            print_info("Cancelled")
            raise typer.Exit(0)

    try:
        with console.status("[cyan]Deleting schedule...[/cyan]"):
            api.delete(f"/schedules/{schedule_id}")

        print_success("Schedule deleted successfully")
    except APIError as exc:
        print_error(f"Failed to delete schedule: {exc}")


# -- list-runs ---------------------------------------------------------


@app.command("list-runs")
def list_runs(
    schedule_id: str = typer.Argument(..., help="Schedule ID"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max results"),
    status_filter: Optional[str] = typer.Option(None, "--status", help="Filter by status (pending/running/completed/failed/timeout)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List execution history for a schedule."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    params = {"limit": limit}
    if status_filter:
        params["status"] = status_filter

    try:
        with console.status("[cyan]Fetching executions...[/cyan]"):
            runs = api.get(f"/schedules/{schedule_id}/executions", params=params)

        if fmt == "json":
            console.print_json(_json.dumps(runs, default=str))
        else:
            if runs:
                data = [
                    {
                        "ID": str(r.get("id", ""))[:8] + "...",
                        "Status": r.get("status", ""),
                        "Scheduled At": format_timestamp(r.get("scheduled_at")),
                        "Completed At": format_timestamp(r.get("completed_at")),
                        "Tokens": str(r.get("tokens_used", 0)),
                        "Cost": str(r.get("cost", "")),
                    }
                    for r in runs
                ]
                print_table(data, title="Schedule Executions")
                print_info(f"{len(runs)} execution(s)")
            else:
                print_info("No executions found for this schedule.")
    except APIError as exc:
        print_error(f"Failed to list executions: {exc}")


# -- trigger -----------------------------------------------------------


@app.command("trigger")
def trigger(
    schedule_id: str = typer.Argument(..., help="Schedule ID"),
    override_prompt: Optional[str] = typer.Option(None, "--prompt", "-p", help="Override the task prompt for this execution"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Manually trigger a schedule execution."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    body = {}
    if override_prompt:
        body["override_prompt"] = override_prompt

    try:
        with console.status("[cyan]Triggering schedule execution...[/cyan]"):
            result = api.post(f"/schedules/{schedule_id}/trigger", body)

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            print_success(f"Schedule triggered (execution ID: {result.get('id', 'N/A')})")
    except APIError as exc:
        print_error(f"Failed to trigger schedule: {exc}")
