"""Deployment management commands for Bonito CLI."""

import typer
from rich.console import Console
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.table import Table
from rich.panel import Panel
from typing import Optional, Dict, List

from ..api import api, APIError
from ..config import is_authenticated
from ..utils.display import (
    print_error, print_success, print_info, print_warning,
    print_table, get_output_format
)
from ..utils.auth import ensure_authenticated

console = Console()

app = typer.Typer(help="🚀 Deployment management")


@app.command("list")
def list_deployments(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """List all deployments."""
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        deployments = api.get("/deployments/")
        
        if output_format == "json":
            console.print_json(deployments)
        else:
            if not deployments:
                print_info("No deployments found")
                print_info("Create one with: bonito deployments create")
                return
            
            # Format deployments for display
            deployment_data = []
            for deployment in deployments:
                status = deployment.get("status", "unknown")
                status_emoji = {
                    "running": "🟢",
                    "stopped": "🔴", 
                    "pending": "🟡",
                    "failed": "❌"
                }.get(status.lower(), "⚪")
                
                deployment_data.append({
                    "ID": deployment.get("id", "")[:8],
                    "Name": deployment.get("config", {}).get("name", "Unnamed"),
                    "Model": deployment.get("model_name", "N/A"),
                    "Status": f"{status_emoji} {status.title()}",
                    "Units": deployment.get("config", {}).get("model_units", "N/A"),
                    "TPM": deployment.get("config", {}).get("tpm", "N/A"),
                    "Tier": deployment.get("config", {}).get("tier", "N/A"),
                    "Created": deployment.get("created_at", "")[:10]
                })
            
            print_table(deployment_data, title="Deployments")
            print_info(f"Found {len(deployments)} deployment(s)")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to list deployments: {e}")


@app.command("create")
def create_deployment(
    model_id: Optional[str] = typer.Option(None, "--model-id", help="Model ID to deploy"),
    name: Optional[str] = typer.Option(None, "--name", help="Deployment name"),
    model_units: Optional[int] = typer.Option(None, "--units", help="Model units to provision"),
    tpm: Optional[int] = typer.Option(None, "--tpm", help="Tokens per minute limit"),
    tier: Optional[str] = typer.Option(None, "--tier", help="Deployment tier"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Create a new deployment."""
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    # Interactive prompts for missing parameters
    if not model_id:
        try:
            # Show available models
            models = api.get("/models/")
            if models:
                print_info("Available models:")
                for i, model in enumerate(models[:10], 1):  # Show first 10
                    console.print(f"  {i}. {model.get('id', '')} - {model.get('name', '')}")
            
            model_id = Prompt.ask("\nEnter model ID to deploy")
        except Exception:
            model_id = Prompt.ask("Enter model ID to deploy")
    
    if not name:
        name = Prompt.ask("Enter deployment name", default=f"deployment-{model_id[:8]}")
    
    if not model_units:
        model_units = IntPrompt.ask("Enter model units to provision", default=1)
    
    if not tpm:
        tpm = IntPrompt.ask("Enter tokens per minute limit", default=1000)
    
    if not tier:
        tier = Prompt.ask("Enter deployment tier", default="standard", 
                          choices=["standard", "premium", "enterprise"])
    
    deployment_data = {
        "model_id": model_id,
        "config": {
            "name": name,
            "model_units": model_units,
            "tpm": tpm,
            "tier": tier
        }
    }
    
    # Show deployment summary
    if output_format == "rich":
        console.print("\n[bold]Deployment Summary:[/bold]")
        summary_table = Table(show_header=False)
        summary_table.add_column("Field", style="cyan")
        summary_table.add_column("Value", style="white")
        
        summary_table.add_row("Model ID", model_id)
        summary_table.add_row("Name", name)
        summary_table.add_row("Model Units", str(model_units))
        summary_table.add_row("TPM Limit", str(tpm))
        summary_table.add_row("Tier", tier.title())
        
        console.print(summary_table)
        
        if not Confirm.ask("\nCreate this deployment?"):
            print_info("Cancelled")
            return
    
    try:
        result = api.post("/deployments/", deployment_data)
        
        if output_format == "json":
            console.print_json(result)
        else:
            print_success(f"Deployment '{name}' created successfully!")
            deployment_id = result.get("id", "")
            if deployment_id:
                console.print(f"[bold]Deployment ID:[/bold] {deployment_id}")
                console.print(f"[bold]Status:[/bold] {result.get('status', 'Unknown')}")
                
                print_info("Track deployment status with: bonito deployments status " + deployment_id[:8])
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to create deployment: {e}")


@app.command("delete")
def delete_deployment(
    deployment_id: str = typer.Argument(..., help="Deployment ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Delete a deployment."""
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    # Confirm deletion unless forced
    if not force and output_format == "rich":
        confirm = Confirm.ask(f"Are you sure you want to delete deployment {deployment_id}?")
        if not confirm:
            print_info("Cancelled")
            return
    
    try:
        # Find full deployment ID if partial was provided
        deployments = api.get("/deployments/")
        full_deployment_id = None
        
        for deployment in deployments:
            if deployment.get("id", "").startswith(deployment_id):
                full_deployment_id = deployment.get("id")
                break
        
        if not full_deployment_id:
            raise APIError(f"Deployment {deployment_id} not found")
        
        api.delete(f"/deployments/{full_deployment_id}")
        
        if output_format == "json":
            console.print_json({
                "status": "success", 
                "message": f"Deployment {deployment_id} deleted"
            })
        else:
            print_success(f"Deployment {deployment_id} deleted successfully")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to delete deployment: {e}")


@app.command("status")
def deployment_status(
    deployment_id: Optional[str] = typer.Argument(None, help="Deployment ID to check status"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Check deployment status."""
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        if deployment_id:
            # Get specific deployment status
            deployments = api.get("/deployments/")
            deployment = None
            
            for dep in deployments:
                if dep.get("id", "").startswith(deployment_id):
                    deployment = dep
                    break
            
            if not deployment:
                raise APIError(f"Deployment {deployment_id} not found")
            
            if output_format == "json":
                console.print_json(deployment)
            else:
                # Show detailed deployment info
                status = deployment.get("status", "unknown")
                status_emoji = {
                    "running": "🟢",
                    "stopped": "🔴",
                    "pending": "🟡",
                    "failed": "❌"
                }.get(status.lower(), "⚪")
                
                console.print(f"\n[bold]Deployment Status: {status_emoji} {status.title()}[/bold]")
                
                # Create info table
                info_table = Table(show_header=False, box=None)
                info_table.add_column("Field", style="cyan", width=15)
                info_table.add_column("Value", style="white")
                
                config = deployment.get("config", {})
                info_table.add_row("ID", deployment.get("id", "")[:12] + "...")
                info_table.add_row("Name", config.get("name", "N/A"))
                info_table.add_row("Model", deployment.get("model_name", "N/A"))
                info_table.add_row("Model Units", str(config.get("model_units", "N/A")))
                info_table.add_row("TPM Limit", str(config.get("tpm", "N/A")))
                info_table.add_row("Tier", config.get("tier", "N/A").title())
                info_table.add_row("Created", deployment.get("created_at", "N/A")[:19])
                info_table.add_row("Updated", deployment.get("updated_at", "N/A")[:19])
                
                console.print(info_table)
                
                # Show any error messages
                if deployment.get("error_message"):
                    print_error(f"Error: {deployment.get('error_message')}")
        
        else:
            # Show status summary for all deployments
            deployments = api.get("/deployments/")
            
            if output_format == "json":
                console.print_json(deployments)
            else:
                if not deployments:
                    print_info("No deployments found")
                    return
                
                status_counts = {}
                for deployment in deployments:
                    status = deployment.get("status", "unknown")
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                console.print("[bold]Deployment Status Summary:[/bold]")
                for status, count in status_counts.items():
                    status_emoji = {
                        "running": "🟢",
                        "stopped": "🔴",
                        "pending": "🟡", 
                        "failed": "❌"
                    }.get(status.lower(), "⚪")
                    
                    console.print(f"  {status_emoji} {status.title()}: {count}")
                
                print_info(f"Total deployments: {len(deployments)}")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to get deployment status: {e}")


if __name__ == "__main__":
    app()