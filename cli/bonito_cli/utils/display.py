"""Rich display utilities for Bonito CLI."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.syntax import Syntax
from rich.table import Table

console = Console()

# ── formatting helpers ──────────────────────────────────────────


def format_cost(amount: Union[int, float]) -> str:
    if amount == 0:
        return "$0.00"
    if amount < 0.01:
        return f"${amount:.4f}"
    return f"${amount:.2f}"


def format_tokens(count: int) -> str:
    if count < 1_000:
        return str(count)
    if count < 1_000_000:
        return f"{count / 1_000:.1f}K"
    return f"{count / 1_000_000:.1f}M"


def format_latency(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    return f"{seconds:.1f}s"


def format_timestamp(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ts


def format_status(status: str) -> str:
    _colors = {
        "active": "green",
        "enabled": "green",
        "healthy": "green",
        "online": "green",
        "success": "green",
        "inactive": "red",
        "disabled": "red",
        "error": "red",
        "offline": "red",
        "failed": "red",
        "pending": "yellow",
        "processing": "yellow",
        "deploying": "yellow",
        "warning": "yellow",
    }
    color = _colors.get(status.lower(), "white")
    return f"[{color}]{status}[/{color}]"


# ── output mode ─────────────────────────────────────────────────


def get_output_format(json_flag: bool = False) -> str:
    return "json" if json_flag else "rich"


# ── print helpers ───────────────────────────────────────────────


def print_error(message: str, exit_code: int = 1) -> None:
    console.print(f"[red]✗ {message}[/red]", highlight=False)
    if exit_code > 0:
        raise typer.Exit(exit_code)


def print_success(message: str) -> None:
    console.print(f"[green]✓ {message}[/green]")


def print_warning(message: str) -> None:
    console.print(f"[yellow]⚠ {message}[/yellow]")


def print_info(message: str) -> None:
    console.print(f"[blue]ℹ {message}[/blue]")


# ── table helpers ───────────────────────────────────────────────


def print_table(
    data: List[Dict[str, Any]],
    title: Optional[str] = None,
    columns: Optional[List[str]] = None,
    output_format: str = "rich",
) -> None:
    if output_format == "json":
        console.print_json(json.dumps(data, default=str))
        return

    if not data:
        console.print("[dim]No data available[/dim]")
        return

    table = Table(title=title, show_header=True, header_style="bold cyan", border_style="dim")
    cols = columns or list(data[0].keys())

    for col in cols:
        table.add_column(col)

    for item in data:
        table.add_row(*(str(item.get(c, "")) for c in cols))

    console.print(table)


def print_dict_as_table(data: Dict[str, Any], title: Optional[str] = None) -> None:
    table = Table(title=title, show_header=False, border_style="dim")
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value")

    for key, value in data.items():
        if isinstance(value, (dict, list)):
            value = json.dumps(value, indent=2, default=str)
        table.add_row(str(key), str(value))

    console.print(table)


def print_json_or_table(data: Any, json_flag: bool, title: Optional[str] = None):
    """Print data as JSON or as a rich table depending on the flag."""
    if json_flag:
        console.print_json(json.dumps(data, default=str))
    elif isinstance(data, list) and data and isinstance(data[0], dict):
        print_table(data, title=title)
    elif isinstance(data, dict):
        print_dict_as_table(data, title=title)
    else:
        console.print(data)


# ── specialised tables ──────────────────────────────────────────


def print_provider_table(providers: List[Dict], output_format: str = "rich"):
    if output_format == "json":
        console.print_json(json.dumps(providers, default=str))
        return
    if not providers:
        console.print("[dim]No providers connected[/dim]")
        return

    table = Table(title="☁️  Connected Providers", header_style="bold cyan", border_style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Region")

    for p in providers:
        table.add_row(
            p.get("name", "—"),
            p.get("type", "—"),
            format_status(p.get("status", "unknown")),
            p.get("config", {}).get("region", p.get("region", "—")),
        )
    console.print(table)


def print_model_table(models: List[Dict], output_format: str = "rich"):
    if output_format == "json":
        console.print_json(json.dumps(models, default=str))
        return
    if not models:
        console.print("[dim]No models found[/dim]")
        return

    table = Table(title="🤖 Models", header_style="bold cyan", border_style="dim")
    table.add_column("ID", style="dim")
    table.add_column("Display Name", style="bold")
    table.add_column("Provider")
    table.add_column("Status")

    for m in models:
        enabled = m.get("enabled", m.get("is_enabled", True))
        status = "[green]✓ enabled[/green]" if enabled else "[dim]locked[/dim]"
        table.add_row(
            str(m.get("id", ""))[:8] + "…",
            m.get("display_name", m.get("model_id", "—")),
            m.get("provider_type", m.get("provider", "—")),
            status,
        )
    console.print(table)


# ── chat display ────────────────────────────────────────────────


class ChatDisplay:
    """Display helper for the interactive chat."""

    @staticmethod
    def print_header(model: str, settings: Dict):
        parts = [f"Model: [cyan]{model}[/cyan]"]
        if settings.get("temperature") is not None:
            parts.append(f"Temp: {settings['temperature']}")
        if settings.get("max_tokens"):
            parts.append(f"Max tokens: {settings['max_tokens']}")
        console.print(Panel(" │ ".join(parts), title="🐟 Bonito Chat", border_style="cyan"))

    @staticmethod
    def print_help():
        console.print(
            "\n[bold]Commands:[/bold]  "
            "[cyan]/model[/cyan] <id>  [cyan]/temp[/cyan] <0-2>  "
            "[cyan]/tokens[/cyan] <n>  [cyan]/clear[/cyan]  "
            "[cyan]/export[/cyan]  [cyan]/stats[/cyan]  [cyan]/quit[/cyan]"
        )

    @staticmethod
    def print_stats(tokens: int, cost: float, latency: float):
        console.print(
            f"[dim]  ── {format_tokens(tokens)} tokens · "
            f"{format_cost(cost)} · {format_latency(latency)}[/dim]"
        )


# ── progress ────────────────────────────────────────────────────


def create_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    )


def print_code(code: str, language: str = "json", title: Optional[str] = None):
    syntax = Syntax(code, language, theme="github-dark", line_numbers=True)
    if title:
        console.print(Panel(syntax, title=title, border_style="blue"))
    else:
        console.print(syntax)
