"""Rich display utilities for Bonito CLI."""

import json
from typing import Any, Dict, List, Optional, Union
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.live import Live
import typer
from datetime import datetime

console = Console()


def print_json(data: Any, output_format: str = "rich"):
    """Print data as JSON or rich format based on --json flag."""
    if output_format == "json":
        console.print(json.dumps(data, indent=2, default=str))
    else:
        # Rich formatted output depends on data type
        if isinstance(data, dict):
            print_dict_as_table(data)
        elif isinstance(data, list):
            print_list_as_table(data)
        else:
            console.print(data)


def print_table(
    data: List[Dict[str, Any]], 
    title: Optional[str] = None,
    columns: Optional[List[str]] = None,
    output_format: str = "rich"
) -> None:
    """Print data as a rich table or JSON."""
    if output_format == "json":
        console.print(json.dumps(data, indent=2, default=str))
        return
    
    if not data:
        console.print("[dim]No data available[/dim]")
        return
    
    # Create table
    table = Table(title=title, show_header=True, header_style="bold cyan")
    
    # Determine columns
    if columns:
        table_columns = columns
    else:
        # Use all keys from first item
        table_columns = list(data[0].keys()) if data else []
    
    # Add columns to table
    for col in table_columns:
        table.add_column(col.replace("_", " ").title())
    
    # Add rows
    for item in data:
        row = []
        for col in table_columns:
            value = item.get(col, "")
            # Format special values
            if col in ["created_at", "updated_at", "timestamp"] and value:
                value = format_timestamp(value)
            elif col in ["cost", "price"] and isinstance(value, (int, float)):
                value = format_cost(value)
            elif col in ["tokens"] and isinstance(value, int):
                value = format_tokens(value)
            elif col == "enabled" and isinstance(value, bool):
                value = "✅" if value else "❌"
            elif col == "status":
                value = format_status(value)
            row.append(str(value))
        table.add_row(*row)
    
    console.print(table)


def print_list_as_table(data: List[Any], title: Optional[str] = None):
    """Print a list as a table."""
    if not data:
        console.print("[dim]No items[/dim]")
        return
    
    if isinstance(data[0], dict):
        print_table(data, title=title)
    else:
        # Simple list
        table = Table(title=title, show_header=False)
        table.add_column("Items")
        for item in data:
            table.add_row(str(item))
        console.print(table)


def print_dict_as_table(data: Dict[str, Any], title: Optional[str] = None):
    """Print a dictionary as a two-column table."""
    table = Table(title=title, show_header=True)
    table.add_column("Key", style="cyan")
    table.add_column("Value")
    
    for key, value in data.items():
        # Format special values
        if key in ["created_at", "updated_at", "timestamp"] and value:
            value = format_timestamp(value)
        elif key in ["cost", "price"] and isinstance(value, (int, float)):
            value = format_cost(value)
        elif key in ["tokens"] and isinstance(value, int):
            value = format_tokens(value)
        elif key == "enabled" and isinstance(value, bool):
            value = "✅ Yes" if value else "❌ No"
        elif isinstance(value, (dict, list)):
            value = json.dumps(value, indent=2)
        
        table.add_row(key.replace("_", " ").title(), str(value))
    
    console.print(table)


def print_panel(
    content: str, 
    title: Optional[str] = None,
    style: str = "cyan",
    expand: bool = False
) -> None:
    """Print content in a rich panel."""
    console.print(Panel(content, title=title, border_style=style, expand=expand))


def print_error(message: str, exit_code: int = 1) -> None:
    """Print error message and exit."""
    console.print(f"[red]❌ Error: {message}[/red]", err=True)
    if exit_code > 0:
        raise typer.Exit(exit_code)


def print_success(message: str) -> None:
    """Print success message."""
    console.print(f"[green]✅ {message}[/green]")


def print_warning(message: str) -> None:
    """Print warning message."""
    console.print(f"[yellow]⚠️  {message}[/yellow]")


def print_info(message: str) -> None:
    """Print info message."""
    console.print(f"[blue]ℹ️  {message}[/blue]")


def format_cost(amount: Union[int, float]) -> str:
    """Format cost as currency."""
    if amount == 0:
        return "$0.00"
    elif amount < 0.01:
        return f"${amount:.4f}"
    else:
        return f"${amount:.2f}"


def format_tokens(count: int) -> str:
    """Format token count with abbreviations."""
    if count < 1000:
        return str(count)
    elif count < 1_000_000:
        return f"{count/1000:.1f}K"
    else:
        return f"{count/1_000_000:.1f}M"


def format_latency(seconds: float) -> str:
    """Format latency in human readable form."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    else:
        return f"{seconds:.1f}s"


def format_timestamp(timestamp: str) -> str:
    """Format timestamp for display."""
    try:
        # Try to parse ISO format
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return timestamp


def format_status(status: str) -> str:
    """Format status with colored indicators."""
    status_colors = {
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
        "warning": "yellow",
    }
    
    color = status_colors.get(status.lower(), "white")
    return f"[{color}]{status}[/{color}]"


def create_progress() -> Progress:
    """Create a standard progress bar."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    )


def with_spinner(func):
    """Decorator to show spinner during function execution."""
    def wrapper(*args, **kwargs):
        with console.status("[bold green]Working..."):
            return func(*args, **kwargs)
    return wrapper


def print_code(code: str, language: str = "json", title: Optional[str] = None):
    """Print code with syntax highlighting."""
    syntax = Syntax(code, language, theme="github-dark", line_numbers=True)
    if title:
        console.print(Panel(syntax, title=title, border_style="blue"))
    else:
        console.print(syntax)


def confirm(message: str, default: bool = False) -> bool:
    """Ask for user confirmation."""
    suffix = " [Y/n]" if default else " [y/N]"
    response = typer.prompt(f"{message}{suffix}", default="y" if default else "n")
    return response.lower().startswith('y')


def prompt_select(choices: List[str], message: str = "Select an option") -> str:
    """Prompt user to select from a list of choices."""
    console.print(f"\n[bold]{message}:[/bold]")
    for i, choice in enumerate(choices, 1):
        console.print(f"  {i}. {choice}")
    
    while True:
        try:
            selection = typer.prompt("\nEnter number")
            idx = int(selection) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
            else:
                console.print("[red]Invalid selection[/red]")
        except ValueError:
            console.print("[red]Please enter a number[/red]")


def format_model_name(model_id: str, enabled: bool = True) -> str:
    """Format model name with status indicator."""
    if enabled:
        return f"[green]{model_id}[/green]"
    else:
        return f"[dim]{model_id} 🔒[/dim]"


def print_model_table(models: List[Dict], output_format: str = "rich"):
    """Print models in a formatted table."""
    if output_format == "json":
        console.print(json.dumps(models, indent=2, default=str))
        return
    
    if not models:
        console.print("[dim]No models found[/dim]")
        return
    
    table = Table(title="Available Models", show_header=True, header_style="bold cyan")
    table.add_column("Model", style="cyan")
    table.add_column("Provider")
    table.add_column("Status")
    table.add_column("Type")
    table.add_column("Cost/1K tokens")
    
    for model in models:
        status = "✅ Enabled" if model.get("enabled", True) else "🔒 Locked"
        cost = format_cost(model.get("cost_per_1k_tokens", 0))
        
        table.add_row(
            model.get("id", ""),
            model.get("provider", ""),
            status,
            model.get("type", ""),
            cost
        )
    
    console.print(table)


def print_provider_table(providers: List[Dict], output_format: str = "rich"):
    """Print providers in a formatted table."""
    if output_format == "json":
        console.print(json.dumps(providers, indent=2, default=str))
        return
    
    if not providers:
        console.print("[dim]No providers connected[/dim]")
        return
    
    table = Table(title="Connected Providers", show_header=True, header_style="bold cyan")
    table.add_column("Provider", style="cyan")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Models")
    table.add_column("Region")
    
    for provider in providers:
        status = format_status(provider.get("status", "unknown"))
        
        table.add_row(
            provider.get("name", ""),
            provider.get("type", ""),
            status,
            str(provider.get("model_count", 0)),
            provider.get("region", "")
        )
    
    console.print(table)


class ChatDisplay:
    """Display helper for chat interface."""
    
    @staticmethod
    def print_header(model_id: str, settings: Dict):
        """Print chat session header."""
        header_text = f"Model: [cyan]{model_id}[/cyan]"
        if settings.get("temperature"):
            header_text += f" │ Temperature: {settings['temperature']}"
        if settings.get("max_tokens"):
            header_text += f" │ Max Tokens: {settings['max_tokens']}"
        
        console.print(Panel(header_text, title="Bonito Chat", border_style="cyan"))
    
    @staticmethod
    def print_message(role: str, content: str):
        """Print a chat message."""
        if role == "user":
            console.print(f"\n[bold blue]You:[/bold blue] {content}")
        else:
            console.print(f"\n[bold green]{role.title()}:[/bold green] {content}")
    
    @staticmethod
    def print_stats(tokens: int, cost: float, latency: float):
        """Print response statistics."""
        stats = f"[dim]tokens: {format_tokens(tokens)} | cost: {format_cost(cost)} | latency: {format_latency(latency)}[/dim]"
        console.print(stats)
    
    @staticmethod
    def print_help():
        """Print chat help."""
        help_text = """
[bold]Chat Commands:[/bold]
  /model <name>    Switch to different model
  /temp <0-2>      Set temperature (creativity)
  /tokens <n>      Set max tokens
  /clear           Clear conversation history
  /export          Export conversation to file
  /help            Show this help
  /quit            Exit chat
        """
        console.print(help_text.strip())


# Global output format helper
def get_output_format(json_flag: bool = False) -> str:
    """Get output format based on --json flag."""
    return "json" if json_flag else "rich"