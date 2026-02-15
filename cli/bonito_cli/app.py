"""Main Bonito CLI application with Typer."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import sys
from pathlib import Path

from . import __version__
from .commands import (
    auth,
    providers,
    models,
    chat,
    gateway,
    policies,
    analytics,
    costs,
    config_cmd
)

console = Console()

# Create the main app
app = typer.Typer(
    name="bonito",
    help="🍌 Unified multi-cloud AI management from your terminal",
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True,
)

# Add subcommand groups
app.add_typer(auth.app, name="auth", help="🔐 Authentication & API keys")
app.add_typer(providers.app, name="providers", help="☁️  Cloud provider management")
app.add_typer(models.app, name="models", help="🤖 AI model management")
app.add_typer(chat.app, name="chat", help="💬 Interactive AI chat")
app.add_typer(gateway.app, name="gateway", help="🚪 API Gateway management")
app.add_typer(policies.app, name="policies", help="🎯 Routing policies")
app.add_typer(analytics.app, name="analytics", help="📊 Usage analytics")
app.add_typer(costs.app, name="costs", help="💰 Cost intelligence")
app.add_typer(config_cmd.app, name="config", help="⚙️  CLI configuration")


def version_callback(value: bool):
    """Show version and exit."""
    if value:
        console.print(_get_banner())
        console.print(f"\nBonito CLI v{__version__}")
        raise typer.Exit()


def _get_banner():
    """Get the CLI banner."""
    banner_text = Text()
    banner_text.append("🍌 ", style="yellow")
    banner_text.append("Bonito CLI", style="bold cyan")
    banner_text.append(" — Unified multi-cloud AI management", style="dim")
    
    return Panel(
        banner_text,
        border_style="cyan",
        padding=(0, 1),
        width=60
    )


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
):
    """
    🍌 Bonito CLI — Unified multi-cloud AI management from your terminal.
    
    Bonito gives enterprise AI teams a single CLI to manage models, costs,
    and workloads across AWS Bedrock, Azure OpenAI, Google Vertex AI, and more.
    
    Get started:
    
        bonito auth login
        bonito models list
        bonito chat
    
    For help with any command, use --help:
    
        bonito providers --help
        bonito chat --help
    """
    pass


if __name__ == "__main__":
    app()