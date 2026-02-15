"""Cloud provider management commands."""

import typer
from rich.console import Console
from rich.prompt import Prompt
from typing import Optional

from ..api import api, APIError
from ..utils.display import (
    print_error, print_success, print_info, print_warning,
    print_provider_table, print_table, get_output_format
)
from ..utils.auth import ensure_authenticated

console = Console()

app = typer.Typer(help="☁️  Cloud provider management")


@app.command("list")
def list_providers(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """List all connected cloud providers."""
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        providers = api.get("/providers/")
        
        if output_format == "json":
            console.print_json(providers)
        else:
            print_provider_table(providers, output_format)
            
            if providers:
                print_info(f"Found {len(providers)} connected provider(s)")
            else:
                print_info("No providers connected")
                print_info("Add one with: bonito providers add aws")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to list providers: {e}")


# Add subcommand for different cloud providers
add_app = typer.Typer(help="Connect cloud providers", no_args_is_help=True)


@add_app.command("aws")
def add_aws(
    access_key: Optional[str] = typer.Option(None, "--access-key", help="AWS Access Key ID"),
    secret_key: Optional[str] = typer.Option(None, "--secret-key", help="AWS Secret Access Key"),
    region: str = typer.Option("us-east-1", "--region", help="AWS region"),
    name: Optional[str] = typer.Option(None, "--name", help="Provider name"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Connect AWS Bedrock provider."""
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    # Prompt for missing credentials
    if not access_key:
        access_key = Prompt.ask("AWS Access Key ID", password=True)
    
    if not secret_key:
        secret_key = Prompt.ask("AWS Secret Access Key", password=True)
    
    if not name:
        name = f"AWS Bedrock ({region})"
    
    provider_data = {
        "type": "aws_bedrock",
        "name": name,
        "config": {
            "access_key_id": access_key,
            "secret_access_key": secret_key,
            "region": region
        }
    }
    
    try:
        result = api.post("/providers/connect", provider_data)
        
        if output_format == "json":
            console.print_json(result)
        else:
            print_success(f"AWS provider '{name}' connected successfully")
            
            # Test the connection
            provider_id = result.get("id")
            if provider_id:
                print_info("Testing connection...")
                try:
                    test_result = api.post(f"/providers/{provider_id}/verify")
                    if test_result.get("status") == "success":
                        print_success("✅ Connection test passed")
                    else:
                        print_warning("⚠️ Connection test had issues")
                except:
                    print_warning("⚠️ Could not test connection")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to connect AWS provider: {e}")


@add_app.command("azure")
def add_azure(
    tenant_id: Optional[str] = typer.Option(None, "--tenant-id", help="Azure Tenant ID"),
    client_id: Optional[str] = typer.Option(None, "--client-id", help="Azure Client ID"),
    client_secret: Optional[str] = typer.Option(None, "--client-secret", help="Azure Client Secret"),
    subscription_id: Optional[str] = typer.Option(None, "--subscription-id", help="Azure Subscription ID"),
    endpoint: Optional[str] = typer.Option(None, "--endpoint", help="Azure OpenAI endpoint"),
    region: str = typer.Option("eastus", "--region", help="Azure region"),
    name: Optional[str] = typer.Option(None, "--name", help="Provider name"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Connect Azure OpenAI provider."""
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    # Prompt for missing credentials
    if not tenant_id:
        tenant_id = Prompt.ask("Azure Tenant ID")
    
    if not client_id:
        client_id = Prompt.ask("Azure Client ID")
    
    if not client_secret:
        client_secret = Prompt.ask("Azure Client Secret", password=True)
    
    if not subscription_id:
        subscription_id = Prompt.ask("Azure Subscription ID")
    
    if not endpoint:
        endpoint = Prompt.ask("Azure OpenAI Endpoint URL")
    
    if not name:
        name = f"Azure OpenAI ({region})"
    
    provider_data = {
        "type": "azure_openai",
        "name": name,
        "config": {
            "tenant_id": tenant_id,
            "client_id": client_id,
            "client_secret": client_secret,
            "subscription_id": subscription_id,
            "endpoint": endpoint,
            "region": region
        }
    }
    
    try:
        result = api.post("/providers/connect", provider_data)
        
        if output_format == "json":
            console.print_json(result)
        else:
            print_success(f"Azure provider '{name}' connected successfully")
            
            # Test the connection
            provider_id = result.get("id")
            if provider_id:
                print_info("Testing connection...")
                try:
                    test_result = api.post(f"/providers/{provider_id}/verify")
                    if test_result.get("status") == "success":
                        print_success("✅ Connection test passed")
                    else:
                        print_warning("⚠️ Connection test had issues")
                except:
                    print_warning("⚠️ Could not test connection")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to connect Azure provider: {e}")


@add_app.command("gcp")
def add_gcp(
    project_id: Optional[str] = typer.Option(None, "--project-id", help="GCP Project ID"),
    service_account_json: Optional[str] = typer.Option(None, "--service-account-json", help="Path to service account JSON file"),
    region: str = typer.Option("us-central1", "--region", help="GCP region"),
    name: Optional[str] = typer.Option(None, "--name", help="Provider name"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Connect Google Cloud (Vertex AI) provider."""
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    # Prompt for missing credentials
    if not project_id:
        project_id = Prompt.ask("GCP Project ID")
    
    if not service_account_json:
        service_account_json = Prompt.ask("Path to service account JSON file")
    
    if not name:
        name = f"Google Vertex AI ({region})"
    
    # Read service account JSON
    try:
        with open(service_account_json, 'r') as f:
            service_account_data = f.read()
    except Exception as e:
        print_error(f"Could not read service account file: {e}")
        return
    
    provider_data = {
        "type": "gcp_vertex",
        "name": name,
        "config": {
            "project_id": project_id,
            "service_account_json": service_account_data,
            "region": region
        }
    }
    
    try:
        result = api.post("/providers/connect", provider_data)
        
        if output_format == "json":
            console.print_json(result)
        else:
            print_success(f"GCP provider '{name}' connected successfully")
            
            # Test the connection
            provider_id = result.get("id")
            if provider_id:
                print_info("Testing connection...")
                try:
                    test_result = api.post(f"/providers/{provider_id}/verify")
                    if test_result.get("status") == "success":
                        print_success("✅ Connection test passed")
                    else:
                        print_warning("⚠️ Connection test had issues")
                except:
                    print_warning("⚠️ Could not test connection")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to connect GCP provider: {e}")


app.add_typer(add_app, name="add")


@app.command("test")
def test_provider(
    provider_id: str = typer.Argument(..., help="Provider ID to test"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Test provider credentials and connectivity."""
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        with console.status(f"[bold green]Testing provider {provider_id}..."):
            result = api.post(f"/providers/{provider_id}/verify")
        
        if output_format == "json":
            console.print_json(result)
        else:
            if result.get("status") == "success":
                print_success("✅ Provider test passed")
                
                # Show test details
                details = result.get("details", {})
                if details:
                    test_info = {
                        "Provider": result.get("provider_name", provider_id),
                        "Status": "✅ Healthy",
                        "Region": details.get("region", "N/A"),
                        "Available Models": details.get("model_count", "N/A"),
                        "Test Time": details.get("test_time", "N/A"),
                    }
                    print_table([test_info], title="Test Results")
            else:
                print_error("❌ Provider test failed")
                error_msg = result.get("error", "Unknown error")
                console.print(f"[red]Error: {error_msg}[/red]")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to test provider: {e}")


@app.command("remove")
def remove_provider(
    provider_id: str = typer.Argument(..., help="Provider ID to remove"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Remove (disconnect) a cloud provider."""
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    # Confirm removal unless forced
    if not force and output_format == "rich":
        confirm = typer.confirm(f"Are you sure you want to remove provider {provider_id}?")
        if not confirm:
            print_info("Cancelled")
            return
    
    try:
        api.delete(f"/providers/{provider_id}")
        
        if output_format == "json":
            console.print_json({
                "status": "success",
                "message": f"Provider {provider_id} removed"
            })
        else:
            print_success(f"Provider {provider_id} removed successfully")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to remove provider: {e}")


@app.command("models")
def provider_models(
    provider_id: str = typer.Argument(..., help="Provider ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """List available models for a provider."""
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        models = api.get(f"/providers/{provider_id}/models")
        
        if output_format == "json":
            console.print_json(models)
        else:
            if not models:
                print_info(f"No models found for provider {provider_id}")
                return
            
            # Format models for display
            model_data = []
            for model in models:
                model_data.append({
                    "Model ID": model.get("id", ""),
                    "Name": model.get("name", ""),
                    "Type": model.get("type", ""),
                    "Status": "✅ Available" if model.get("available", True) else "❌ Unavailable",
                    "Cost/1K": f"${model.get('cost_per_1k_tokens', 0):.4f}"
                })
            
            print_table(model_data, title=f"Models for Provider {provider_id}")
            print_info(f"Found {len(models)} model(s)")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to get provider models: {e}")


@app.command("costs")
def provider_costs(
    provider_id: str = typer.Argument(..., help="Provider ID"),
    days: int = typer.Option(30, "--days", help="Number of days to analyze"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Show cost analysis for a provider."""
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        costs = api.get_provider_costs(provider_id, days)
        
        if output_format == "json":
            console.print_json(costs)
        else:
            # Show cost summary
            total_cost = costs.get("total_cost", 0)
            print_success(f"Cost analysis for provider {provider_id} (last {days} days)")
            
            console.print(f"💰 Total Cost: [green]${total_cost:.2f}[/green]")
            
            # Show breakdown by model if available
            breakdown = costs.get("breakdown_by_model", [])
            if breakdown:
                cost_data = []
                for item in breakdown:
                    cost_data.append({
                        "Model": item.get("model", ""),
                        "Requests": item.get("requests", 0),
                        "Tokens": f"{item.get('tokens', 0):,}",
                        "Cost": f"${item.get('cost', 0):.2f}",
                        "Avg Cost/Request": f"${item.get('avg_cost_per_request', 0):.4f}"
                    })
                
                print_table(cost_data, title="Cost Breakdown by Model")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to get provider costs: {e}")


if __name__ == "__main__":
    app()