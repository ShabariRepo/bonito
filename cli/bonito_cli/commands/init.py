"""Initialization wizard command."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text

from ..api import api, APIError
from ..config import is_authenticated, load_credentials
from ..utils.auth import ensure_authenticated
from ..utils.display import print_error, print_success, print_info, print_warning

console = Console()
app = typer.Typer(help="🚀 Setup wizard")


def _detect_terraform_provider_type(tf_path: Path) -> str:
    """Detect provider type from Terraform directory name."""
    dir_name = tf_path.name.lower()
    if "aws" in dir_name:
        return "aws"
    elif "azure" in dir_name:
        return "azure"
    elif "gcp" in dir_name or "google" in dir_name:
        return "gcp"
    else:
        raise ValueError(f"Cannot detect provider type from directory: {tf_path}")


def _read_terraform_outputs(tf_path: Path) -> Dict[str, Any]:
    """Read Terraform outputs from a directory."""
    try:
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=tf_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        console.print(f"[red]✗ Failed to read Terraform outputs from {tf_path}: {e}[/red]")
        raise typer.Exit(1)


def _extract_aws_credentials(outputs: Dict[str, Any]) -> Dict[str, str]:
    """Extract AWS credentials from Terraform outputs."""
    try:
        return {
            "access_key_id": outputs["access_key_id"]["value"],
            "secret_access_key": outputs["secret_access_key"]["value"],
            "region": outputs.get("region", {}).get("value", "us-east-1"),
        }
    except KeyError as e:
        console.print(f"[red]✗ Missing AWS credential in Terraform output: {e}[/red]")
        raise typer.Exit(1)


def _extract_azure_credentials(outputs: Dict[str, Any]) -> Dict[str, str]:
    """Extract Azure credentials from Terraform outputs."""
    try:
        return {
            "tenant_id": outputs["tenant_id"]["value"],
            "client_id": outputs["client_id"]["value"],
            "client_secret": outputs["client_secret"]["value"],
            "subscription_id": outputs["subscription_id"]["value"],
        }
    except KeyError as e:
        console.print(f"[red]✗ Missing Azure credential in Terraform output: {e}[/red]")
        raise typer.Exit(1)


def _extract_gcp_credentials(outputs: Dict[str, Any], tf_path: Path) -> Dict[str, str]:
    """Extract GCP credentials from Terraform outputs."""
    try:
        project_id = outputs["project_id"]["value"]
        
        # Look for the service account key file
        sa_key_path = tf_path / "bonito-sa-key.json"
        if not sa_key_path.exists():
            console.print(f"[red]✗ Service account key file not found at: {sa_key_path}[/red]")
            raise typer.Exit(1)
        
        with open(sa_key_path, 'r') as f:
            service_account_key = json.load(f)
        
        return {
            "project_id": project_id,
            "service_account_key": service_account_key,
        }
    except KeyError as e:
        console.print(f"[red]✗ Missing GCP credential in Terraform output: {e}[/red]")
        raise typer.Exit(1)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        console.print(f"[red]✗ Failed to read GCP service account key: {e}[/red]")
        raise typer.Exit(1)


def _prompt_for_credentials(provider: str) -> Dict[str, str]:
    """Prompt user for provider credentials interactively."""
    if provider == "aws":
        return {
            "access_key_id": Prompt.ask("[cyan]AWS Access Key ID[/cyan]"),
            "secret_access_key": Prompt.ask("[cyan]AWS Secret Access Key[/cyan]", password=True),
            "region": Prompt.ask("[cyan]AWS Region[/cyan]", default="us-east-1"),
        }
    elif provider == "azure":
        return {
            "tenant_id": Prompt.ask("[cyan]Azure Tenant ID[/cyan]"),
            "client_id": Prompt.ask("[cyan]Azure Client ID[/cyan]"),
            "client_secret": Prompt.ask("[cyan]Azure Client Secret[/cyan]", password=True),
            "subscription_id": Prompt.ask("[cyan]Azure Subscription ID[/cyan]"),
        }
    elif provider == "gcp":
        sa_key_path = Prompt.ask("[cyan]Path to GCP Service Account Key JSON file[/cyan]")
        try:
            with open(sa_key_path, 'r') as f:
                service_account_key = json.load(f)
            return {
                "project_id": service_account_key.get("project_id", Prompt.ask("[cyan]GCP Project ID[/cyan]")),
                "service_account_key": service_account_key,
            }
        except (FileNotFoundError, json.JSONDecodeError) as e:
            console.print(f"[red]✗ Failed to read service account key: {e}[/red]")
            raise typer.Exit(1)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _connect_provider(provider: str, credentials: Dict[str, str]) -> Dict[str, Any]:
    """Connect a provider via the API."""
    provider_map = {
        "aws": "aws_bedrock",
        "azure": "azure_openai", 
        "gcp": "gcp_vertex",
    }
    
    try:
        with console.status(f"[cyan]Connecting {provider.upper()}…[/cyan]"):
            result = api.post(f"/providers/{provider_map[provider]}/connect", credentials)
        console.print(f"[green]✓ Connected {provider.upper()}[/green]")
        return result
    except APIError as e:
        console.print(f"[red]✗ Failed to connect {provider.upper()}: {e}[/red]")
        raise typer.Exit(1)


def _sync_models() -> List[Dict[str, Any]]:
    """Sync and list available models."""
    try:
        with console.status("[cyan]Syncing models…[/cyan]"):
            sync_result = api.post("/models/sync")
        
        with console.status("[cyan]Fetching available models…[/cyan]"):
            models = api.get("/models/")
        
        console.print(f"[green]✓ Synced {len(models)} models[/green]")
        return models
    except APIError as e:
        console.print(f"[red]✗ Failed to sync models: {e}[/red]")
        raise typer.Exit(1)


def _enable_models(models: List[Dict[str, Any]], selected_model_ids: List[str]):
    """Enable selected models."""
    for model_id in selected_model_ids:
        try:
            with console.status(f"[cyan]Enabling {model_id}…[/cyan]"):
                api.patch(f"/models/{model_id}", {"enabled": True})
        except APIError as e:
            console.print(f"[red]✗ Failed to enable {model_id}: {e}[/red]")


def _generate_api_key() -> str:
    """Generate an API key for gateway access."""
    try:
        with console.status("[cyan]Generating API key…[/cyan]"):
            result = api.post("/auth/api-keys", {"name": "Bonito CLI Setup"})
        return result["key"]
    except APIError as e:
        console.print(f"[red]✗ Failed to generate API key: {e}[/red]")
        raise typer.Exit(1)


@app.command("init")
def init_wizard(
    from_terraform: Optional[str] = typer.Option(None, "--from-terraform", help="Path to Terraform infrastructure directory"),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Non-interactive mode"),
    providers: Optional[str] = typer.Option(None, "--providers", help="Comma-separated list of providers (aws,azure,gcp)"),
    enable_all_models: bool = typer.Option(False, "--enable-all-models", help="Enable all available models"),
):
    """
    🚀 One-liner setup wizard for Bonito.

    This command will:
    1. Ensure you're authenticated (or help you sign up/login)
    2. Connect cloud providers
    3. Sync available models
    4. Enable selected models
    5. Generate an API key
    6. Show you how to use the gateway

    Examples:
        bonito init
        bonito init --from-terraform ./bonito-infra
        bonito init --non-interactive --providers aws,azure --enable-all-models
    """
    
    console.print(Panel(
        "[bold cyan]🚀 Bonito Setup Wizard[/bold cyan]\n\n"
        "This wizard will help you get started with Bonito by:\n"
        "• Connecting your cloud providers\n"
        "• Syncing available AI models\n"
        "• Generating API keys\n"
        "• Showing you example usage",
        border_style="cyan"
    ))
    
    # Step 1: Check authentication
    if not is_authenticated():
        if non_interactive:
            console.print("[red]✗ Not authenticated. In non-interactive mode, please login first:[/red]")
            console.print("  [cyan]bonito auth login[/cyan] or [cyan]bonito auth signup[/cyan]")
            raise typer.Exit(1)
        
        console.print("\n[yellow]⚠ You need to be logged in to continue.[/yellow]")
        choice = Prompt.ask(
            "Would you like to",
            choices=["signup", "login", "quit"],
            default="signup"
        )
        
        if choice == "quit":
            raise typer.Exit(0)
        elif choice == "signup":
            console.print("\nLet's create your account:")
            from .auth import signup
            # Call signup interactively
            signup()
        elif choice == "login":
            console.print("\nPlease login:")
            from .auth import login
            login()
    
    # Now we should be authenticated
    ensure_authenticated()
    
    # Step 2: Determine which providers to connect
    selected_providers = []
    
    if from_terraform:
        terraform_path = Path(from_terraform)
        if not terraform_path.exists():
            console.print(f"[red]✗ Terraform path does not exist: {terraform_path}[/red]")
            raise typer.Exit(1)
        
        # Look for provider subdirectories
        for provider_dir in ["aws", "azure", "gcp"]:
            provider_path = terraform_path / provider_dir
            if provider_path.exists():
                selected_providers.append(provider_dir)
        
        if not selected_providers:
            console.print(f"[red]✗ No provider directories found in: {terraform_path}[/red]")
            console.print("  Expected: aws/, azure/, or gcp/ subdirectories")
            raise typer.Exit(1)
        
        console.print(f"\n[green]✓ Found providers in Terraform directory:[/green] {', '.join(selected_providers)}")
    
    elif providers:
        selected_providers = [p.strip() for p in providers.split(",")]
        invalid_providers = [p for p in selected_providers if p not in ["aws", "azure", "gcp"]]
        if invalid_providers:
            console.print(f"[red]✗ Invalid providers: {invalid_providers}[/red]")
            console.print("  Valid options: aws, azure, gcp")
            raise typer.Exit(1)
    
    elif not non_interactive:
        console.print("\n[cyan]Which cloud providers would you like to connect?[/cyan]")
        available_providers = {
            "aws": "☁️  AWS Bedrock",
            "azure": "🔷 Azure OpenAI", 
            "gcp": "🔺 GCP Vertex AI"
        }
        
        selected_providers = []
        for provider, display_name in available_providers.items():
            if Confirm.ask(f"Connect {display_name}?", default=True):
                selected_providers.append(provider)
    
    else:
        console.print("[red]✗ In non-interactive mode, --providers is required[/red]")
        raise typer.Exit(1)
    
    if not selected_providers:
        console.print("[red]✗ No providers selected[/red]")
        raise typer.Exit(1)
    
    # Step 3: Connect providers
    console.print(f"\n[cyan]🔗 Connecting {len(selected_providers)} provider(s)...[/cyan]")
    
    connected_providers = []
    for provider in selected_providers:
        try:
            if from_terraform:
                # Extract credentials from Terraform
                tf_provider_path = Path(from_terraform) / provider
                outputs = _read_terraform_outputs(tf_provider_path)
                
                if provider == "aws":
                    creds = _extract_aws_credentials(outputs)
                elif provider == "azure":
                    creds = _extract_azure_credentials(outputs)
                elif provider == "gcp":
                    creds = _extract_gcp_credentials(outputs, tf_provider_path)
                else:
                    raise ValueError(f"Unknown provider: {provider}")
            
            elif not non_interactive:
                # Interactive credential collection
                console.print(f"\n[cyan]📝 Enter credentials for {provider.upper()}:[/cyan]")
                creds = _prompt_for_credentials(provider)
            
            else:
                console.print(f"[red]✗ Non-interactive mode requires --from-terraform for credential collection[/red]")
                raise typer.Exit(1)
            
            # Connect the provider
            result = _connect_provider(provider, creds)
            connected_providers.append(provider)
            
        except Exception as e:
            console.print(f"[yellow]⚠ Skipped {provider.upper()}: {e}[/yellow]")
    
    if not connected_providers:
        console.print("[red]✗ No providers connected successfully[/red]")
        raise typer.Exit(1)
    
    # Step 4: Sync models
    console.print(f"\n[cyan]🤖 Syncing AI models from connected providers...[/cyan]")
    models = _sync_models()
    
    # Step 5: Enable models
    if enable_all_models or non_interactive:
        # Enable all models
        console.print("[cyan]Enabling all available models...[/cyan]")
        model_ids = [model["id"] for model in models if not model.get("enabled", False)]
        _enable_models(models, model_ids)
        console.print(f"[green]✓ Enabled {len(model_ids)} models[/green]")
    
    elif not non_interactive:
        # Interactive model selection
        console.print(f"\n[cyan]Found {len(models)} available models. Which would you like to enable?[/cyan]")
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("ID", style="dim")
        table.add_column("Name")
        table.add_column("Provider")
        table.add_column("Enabled", justify="center")
        
        for model in models[:10]:  # Show first 10 for brevity
            enabled = "✓" if model.get("enabled", False) else "✗"
            table.add_row(
                model["id"],
                model.get("name", "—"),
                model.get("provider", "—"),
                enabled
            )
        
        console.print(table)
        if len(models) > 10:
            console.print(f"[dim]... and {len(models) - 10} more models[/dim]")
        
        # Simple enable all option for now
        if Confirm.ask("Enable all models?", default=True):
            model_ids = [model["id"] for model in models if not model.get("enabled", False)]
            _enable_models(models, model_ids)
            console.print(f"[green]✓ Enabled {len(model_ids)} models[/green]")
    
    # Step 6: Generate API key
    console.print(f"\n[cyan]🔑 Generating API key for gateway access...[/cyan]")
    api_key = _generate_api_key()
    console.print(f"[green]✓ Generated API key[/green]")
    
    # Step 7: Print summary
    console.print("\n" + "="*60)
    console.print(Panel(
        f"[bold green]🎉 Bonito setup complete![/bold green]\n\n"
        f"[bold]Connected providers:[/bold] {', '.join(p.upper() for p in connected_providers)}\n"
        f"[bold]Available models:[/bold] {len(models)}\n"
        f"[bold]API key:[/bold] {api_key[:8]}••••••••\n\n"
        f"[bold cyan]Try it now:[/bold cyan]\n"
        f"[white]curl -X POST https://gateway.bonito.ai/v1/chat/completions \\\n"
        f"  -H 'Authorization: Bearer {api_key}' \\\n"
        f"  -H 'Content-Type: application/json' \\\n"
        f"  -d '{{\n"
        f'    "model": "gpt-4",\n'
        f'    "messages": [{{"role": "user", "content": "Hello!"}}]\n'
        f"  }}'[/white]\n\n"
        f"Or use the CLI: [cyan]bonito chat[/cyan]",
        title="🚀 Setup Complete",
        border_style="green"
    ))
    
    console.print(f"\n[bold]Next steps:[/bold]")
    console.print("• Store your API key: [cyan]export BONITO_API_KEY={api_key}[/cyan]")
    console.print("• Start chatting: [cyan]bonito chat[/cyan]")
    console.print("• View usage: [cyan]bonito analytics usage[/cyan]")
    console.print("• Manage models: [cyan]bonito models list[/cyan]")