"""Main Bonito CLI application with Typer."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
import sys

from . import __version__
from .commands.auth import app as auth_app
from .commands.providers import app as providers_app
from .commands.models import app as models_app
from .commands.chat import app as chat_app
from .commands.gateway import app as gateway_app
from .commands.policies import app as policies_app
from .commands.analytics import app as analytics_app
from .commands.deployments import app as deployments_app
from .commands.kb import app as kb_app

console = Console()

# ── Bonito fish ASCII art ──────────────────────────────────────
FISH_ART = (
    "[bold cyan]        ___...---\"\"\"---...__              [/bold cyan]\n"
    "[bold cyan]    .-\"\"                   \"\"-._          [/bold cyan]\n"
    "[bold cyan]   /                            \\         [/bold cyan]\n"
    "[bold cyan]  |    [bold white]●[/bold white][bold cyan]          __.._          |        [/bold cyan]\n"
    "[bold cyan]  |           _.-\"    \"-.       /\\        [/bold cyan]\n"
    "[bold cyan]   \\       .-\"          \"-.  _.' /        [/bold cyan]\n"
    "[bold cyan]    \"---.-\"  [dim cyan]bonito[/dim cyan]        \"-\"  _/         [/bold cyan]\n"
    "[bold cyan]        \\    [dim cyan]  CLI [/dim cyan]          _.-\"           [/bold cyan]\n"
    "[bold cyan]         \"-.__       __.-\"                [/bold cyan]\n"
    "[bold cyan]              \"\"\"---\"\"\"                    [/bold cyan]"
)

LOGO_COMPACT = "[bold cyan]  ><(((º>  [/bold cyan][bold white]Bonito CLI[/bold white] [dim]v{version}[/dim]"


def _get_banner() -> str:
    """Get the full CLI banner with fish art."""
    return (
        FISH_ART
        + f"\n  [bold white]Bonito CLI[/bold white] [dim]v{__version__}[/dim]"
        + "\n  [dim]Unified multi-cloud AI management from your terminal[/dim]\n"
    )


def _get_mini_banner() -> str:
    """Get compact one-line banner."""
    return LOGO_COMPACT.format(version=__version__)


# ── Main Typer app ─────────────────────────────────────────────
app = typer.Typer(
    name="bonito",
    help="🐟 Bonito CLI — Unified multi-cloud AI management from your terminal",
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True,
)

# ── Subcommand groups ──────────────────────────────────────────
app.add_typer(auth_app,        name="auth",        help="🔐 Authentication & API keys")
app.add_typer(providers_app,   name="providers",   help="☁️  Cloud provider management")
app.add_typer(models_app,      name="models",      help="🤖 AI model catalogue")
app.add_typer(deployments_app, name="deployments",  help="🚀 Deployment management")
app.add_typer(chat_app,        name="chat",        help="💬 Interactive AI chat")
app.add_typer(gateway_app,     name="gateway",     help="🌐 API gateway management")
app.add_typer(policies_app,    name="policies",    help="🎯 Routing policies")
app.add_typer(analytics_app,   name="analytics",   help="📊 Usage analytics & costs")
app.add_typer(kb_app,          name="kb",          help="📚 Knowledge base (RAG)")


# ── Callbacks ──────────────────────────────────────────────────
def version_callback(value: bool):
    """Show version and exit."""
    if value:
        console.print(_get_banner())
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
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
    [bold cyan]🐟 Bonito CLI[/bold cyan] — Unified multi-cloud AI management from your terminal.

    Bonito gives enterprise AI teams a single CLI to manage models, costs,
    and workloads across AWS Bedrock, Azure OpenAI, Google Vertex AI, and more.

    [bold]Quick start:[/bold]

        bonito auth login
        bonito models list
        bonito chat

    [bold]Get help on any command:[/bold]

        bonito providers --help
        bonito chat --help
    """
    # When invoked with no subcommand and not --version, show help
    if ctx.invoked_subcommand is None:
        console.print(_get_banner())
        console.print(ctx.get_help())
        raise typer.Exit()


if __name__ == "__main__":
    app()
