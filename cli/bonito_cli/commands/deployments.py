"""Deployment management commands."""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from typing import Optional

from ..api import api, APIError
from ..config import is_authenticated

console = Console()
app = typer.Typer(help="🚀 Deployment management")

PROVIDER_EMOJI = {"aws": "☁️", "azure": "🔷", "gcp": "🔺"}


@app.command("list")
def list_deployments():
    """List all deployments."""
    if not is_authenticated():
        console.print("[yellow]Not logged in. Run: bonito auth login[/yellow]")
        raise typer.Exit(1)
    
    try:
        with console.status("[cyan]Fetching deployments...[/cyan]"):
            deployments = api.get("/deployments/")
        
        if not deployments:
            console.print(Panel(
                "[dim]No deployments yet.[/dim]\n\n"
                "Create one: [cyan]bonito deployments create[/cyan]",
                title="🚀 Deployments",
                border_style="dim",
            ))
            return
        
        table = Table(title="🚀 Deployments", border_style="dim")
        table.add_column("Name", style="bold")
        table.add_column("Model")
        table.add_column("Provider")
        table.add_column("Type")
        table.add_column("Status")
        table.add_column("Cost")
        
        for d in deployments:
            config = d.get("config", {})
            provider_type = config.get("provider_type", "")
            emoji = PROVIDER_EMOJI.get(provider_type, "☁️")
            deploy_type = config.get("config_applied", {}).get("type", "—")
            estimate = config.get("cost_estimate", {})
            cost = f"${estimate['monthly']:.0f}/mo" if estimate.get("monthly", 0) > 0 else "Pay-per-use"
            
            status_style = "green" if d["status"] == "active" else "yellow" if d["status"] == "deploying" else "red"
            
            table.add_row(
                config.get("name", "—"),
                config.get("model_display_name", "—"),
                f"{emoji} {provider_type.upper()}",
                deploy_type,
                f"[{status_style}]{d['status']}[/{status_style}]",
                cost,
            )
        
        console.print(table)
        console.print(f"\n[dim]{len(deployments)} deployment(s)[/dim]")
    
    except APIError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)


@app.command("create")
def create_deployment(
    model_id: Optional[str] = typer.Option(None, "--model", "-m", help="Model UUID"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Deployment name"),
    model_units: int = typer.Option(0, "--units", help="AWS model units (0 = on-demand)"),
    tpm: int = typer.Option(10, "--tpm", help="Azure tokens per minute (thousands)"),
    tier: str = typer.Option("Standard", "--tier", help="Azure tier (Standard/GlobalStandard/Provisioned)"),
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for model by name"),
):
    """
    Create a new deployment.
    
    Examples:
        bonito deployments create --search "nova pro" --name prod-nova
        bonito deployments create --model <uuid> --name my-deploy
    """
    if not is_authenticated():
        console.print("[yellow]Not logged in. Run: bonito auth login[/yellow]")
        raise typer.Exit(1)
    
    try:
        # If search provided, find the model
        if search and not model_id:
            with console.status(f"[cyan]Searching for '{search}'...[/cyan]"):
                models = api.get("/models/")
            
            matches = [m for m in models if search.lower() in m.get("display_name", "").lower() 
                       or search.lower() in m.get("model_id", "").lower()]
            
            if not matches:
                console.print(f"[red]No models matching '{search}'[/red]")
                raise typer.Exit(1)
            
            if len(matches) == 1:
                model_id = matches[0]["id"]
                console.print(f"[green]Found:[/green] {matches[0]['display_name']} ({matches[0].get('provider_type', '').upper()})")
            else:
                # Show options
                table = Table(title=f"Models matching '{search}'", border_style="dim")
                table.add_column("#", style="bold cyan", width=3)
                table.add_column("Name")
                table.add_column("Provider")
                table.add_column("Model ID", style="dim")
                
                for i, m in enumerate(matches[:10], 1):
                    table.add_row(
                        str(i),
                        m.get("display_name", "—"),
                        m.get("provider_type", "—").upper(),
                        m.get("model_id", "—"),
                    )
                console.print(table)
                
                choice = Prompt.ask("Select model #", default="1")
                idx = int(choice) - 1
                if 0 <= idx < len(matches):
                    model_id = matches[idx]["id"]
                else:
                    console.print("[red]Invalid selection[/red]")
                    raise typer.Exit(1)
        
        if not model_id:
            console.print("[red]Model ID required. Use --model <uuid> or --search <name>[/red]")
            raise typer.Exit(1)
        
        config = {}
        if name:
            config["name"] = name
        if model_units > 0:
            config["model_units"] = model_units
            config["commitment_term"] = "none"
        else:
            config["model_units"] = 0
        if tpm != 10:
            config["tpm"] = tpm
        if tier != "Standard":
            config["tier"] = tier
        
        with console.status("[cyan]Creating deployment...[/cyan]"):
            result = api.post("/deployments/", {"model_id": model_id, "config": config})
        
        rc = result.get("config", {})
        console.print(Panel(
            f"[green]✓ Deployment created[/green]\n\n"
            f"  Name:     [bold]{rc.get('name', '—')}[/bold]\n"
            f"  Model:    {rc.get('model_display_name', '—')}\n"
            f"  Provider: {PROVIDER_EMOJI.get(rc.get('provider_type', ''), '☁️')} {rc.get('provider_type', '').upper()}\n"
            f"  Status:   {result.get('status', '—')}\n"
            f"  Endpoint: {rc.get('endpoint_url', '—')}\n"
            f"\n  [dim]{rc.get('deploy_message', '')}[/dim]",
            title="🚀 Deployment Created",
            border_style="green",
        ))
    
    except APIError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)


@app.command("delete")
def delete_deployment(
    deployment_id: str = typer.Argument(help="Deployment UUID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a deployment."""
    if not is_authenticated():
        console.print("[yellow]Not logged in. Run: bonito auth login[/yellow]")
        raise typer.Exit(1)
    
    if not force:
        if not Confirm.ask(f"[red]Delete deployment {deployment_id[:8]}...?[/red]"):
            console.print("[dim]Cancelled[/dim]")
            return
    
    try:
        with console.status("[cyan]Deleting deployment...[/cyan]"):
            api.delete(f"/deployments/{deployment_id}")
        console.print(f"[green]✓ Deployment {deployment_id[:8]}... deleted[/green]")
    except APIError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)


@app.command("status")
def deployment_status(
    deployment_id: str = typer.Argument(help="Deployment UUID"),
):
    """Refresh deployment status from cloud provider."""
    if not is_authenticated():
        console.print("[yellow]Not logged in. Run: bonito auth login[/yellow]")
        raise typer.Exit(1)
    
    try:
        with console.status("[cyan]Checking status...[/cyan]"):
            result = api.post(f"/deployments/{deployment_id}/status")
        
        status_style = "green" if result.get("status") == "active" else "yellow"
        console.print(f"[{status_style}]Status: {result.get('status', '—')}[/{status_style}]")
        
        cloud = result.get("cloud_status", {})
        if cloud:
            for k, v in cloud.items():
                console.print(f"  [dim]{k}:[/dim] {v}")
    except APIError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)
