"""Compliance checks and reporting commands."""

from __future__ import annotations

import json as _json

import typer
from rich.console import Console

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
app = typer.Typer(help="Compliance checks and reporting")


# -- run-check ---------------------------------------------------------


@app.command("run-check")
def run_check(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Run a compliance scan across all providers."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Running compliance scan...[/cyan]"):
            result = api.post("/compliance/scan")

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            print_success("Compliance scan completed")
            if isinstance(result, dict):
                print_dict_as_table(result, title="Scan Results")
    except APIError as exc:
        print_error(f"Failed to run compliance scan: {exc}")


# -- list-checks -------------------------------------------------------


@app.command("list-checks")
def list_checks(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all compliance checks and their status."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching compliance checks...[/cyan]"):
            checks = api.get("/compliance/checks")

        if fmt == "json":
            console.print_json(_json.dumps(checks, default=str))
        else:
            if checks:
                data = [
                    {
                        "Check": c.get("name", c.get("check_id", "")),
                        "Framework": c.get("framework", ""),
                        "Status": c.get("status", ""),
                        "Severity": c.get("severity", ""),
                        "Last Run": str(c.get("last_checked_at", ""))[:10] if c.get("last_checked_at") else "",
                    }
                    for c in checks
                ]
                print_table(data, title="Compliance Checks")
                print_info(f"{len(checks)} check(s)")
            else:
                print_info("No compliance checks found.")
    except APIError as exc:
        print_error(f"Failed to list compliance checks: {exc}")


# -- get-report --------------------------------------------------------


@app.command("get-report")
def get_report(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Get the full compliance report."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Generating compliance report...[/cyan]"):
            report = api.get("/compliance/report")

        if fmt == "json":
            console.print_json(_json.dumps(report, default=str))
        else:
            if isinstance(report, dict):
                print_dict_as_table(report, title="Compliance Report")
            else:
                console.print(report)
    except APIError as exc:
        print_error(f"Failed to get compliance report: {exc}")
