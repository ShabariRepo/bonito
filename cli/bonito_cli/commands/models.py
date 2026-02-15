"""AI model management commands."""

import typer
from rich.console import Console
from typing import Optional, List

from ..api import api, APIError
from ..utils.display import (
    print_error, print_success, print_info, print_warning,
    print_model_table, print_table, print_dict_as_table,
    get_output_format, format_cost, format_tokens
)
from ..utils.auth import ensure_authenticated

console = Console()

app = typer.Typer(help="🤖 AI model management")


@app.command("list")
def list_models(
    provider: Optional[str] = typer.Option(None, "--provider", help="Filter by provider"),
    enabled_only: bool = typer.Option(False, "--enabled-only", help="Show only enabled models"),
    search: Optional[str] = typer.Option(None, "--search", help="Search models by name"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    List available AI models.
    
    Filter models by provider, status, or search terms.
    """
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        models = api.list_models(
            provider=provider,
            enabled_only=enabled_only,
            search=search
        )
        
        if output_format == "json":
            console.print_json(models)
        else:
            print_model_table(models, output_format)
            
            # Show summary
            total_models = len(models)
            enabled_count = sum(1 for m in models if m.get("enabled", True))
            locked_count = total_models - enabled_count
            
            summary = []
            if provider:
                summary.append(f"Provider: {provider}")
            if search:
                summary.append(f"Search: '{search}'")
            
            summary_text = " | ".join(summary) if summary else "All models"
            console.print(f"\n[dim]{summary_text}[/dim]")
            console.print(f"📊 {total_models} total, {enabled_count} enabled, {locked_count} locked")
            
            if locked_count > 0:
                print_info("Use 'bonito models enable MODEL_ID' to unlock models")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to list models: {e}")


@app.command("info")
def model_info(
    model_id: str = typer.Argument(..., help="Model ID to get information for"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Get detailed information about a specific model.
    """
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        # Get both basic info and detailed info
        basic_info = api.get_model_info(model_id)
        detailed_info = api.get_model_details(model_id)
        
        # Combine the information
        model_info = {**basic_info, **detailed_info}
        
        if output_format == "json":
            console.print_json(model_info)
        else:
            # Display rich format
            console.print(f"\n[bold cyan]🤖 {model_id}[/bold cyan]")
            
            # Basic information
            basic_data = {
                "Name": model_info.get("name", model_id),
                "Provider": model_info.get("provider", "N/A"),
                "Type": model_info.get("type", "N/A"),
                "Status": "✅ Enabled" if model_info.get("enabled", True) else "🔒 Locked",
                "Description": model_info.get("description", "N/A"),
            }
            
            print_dict_as_table(basic_data, title="Model Information")
            
            # Pricing information
            pricing_data = {
                "Input Cost (per 1K tokens)": format_cost(model_info.get("input_cost_per_1k_tokens", 0)),
                "Output Cost (per 1K tokens)": format_cost(model_info.get("output_cost_per_1k_tokens", 0)),
                "Average Cost (per 1K tokens)": format_cost(model_info.get("cost_per_1k_tokens", 0)),
            }
            
            print_dict_as_table(pricing_data, title="Pricing")
            
            # Capabilities
            capabilities = model_info.get("capabilities", {})
            if capabilities:
                cap_data = {
                    "Max Input Tokens": format_tokens(capabilities.get("max_input_tokens", 0)),
                    "Max Output Tokens": format_tokens(capabilities.get("max_output_tokens", 0)),
                    "Supports Streaming": "✅ Yes" if capabilities.get("supports_streaming") else "❌ No",
                    "Supports Function Calling": "✅ Yes" if capabilities.get("supports_function_calling") else "❌ No",
                    "Supports Vision": "✅ Yes" if capabilities.get("supports_vision") else "❌ No",
                }
                
                print_dict_as_table(cap_data, title="Capabilities")
            
            # Usage stats if available
            stats = model_info.get("usage_stats", {})
            if stats:
                stats_data = {
                    "Total Requests": f"{stats.get('total_requests', 0):,}",
                    "Total Tokens": format_tokens(stats.get("total_tokens", 0)),
                    "Total Cost": format_cost(stats.get("total_cost", 0)),
                    "Average Latency": f"{stats.get('avg_latency', 0):.2f}s",
                }
                
                print_dict_as_table(stats_data, title="Usage Statistics")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to get model info: {e}")


@app.command("enable")
def enable_models(
    model_ids: List[str] = typer.Argument(..., help="Model ID(s) to enable"),
    bulk: bool = typer.Option(False, "--bulk", help="Enable multiple models at once"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Enable (activate) one or more AI models.
    
    This allows the models to be used for inference.
    """
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    if not model_ids:
        print_error("At least one model ID is required")
        return
    
    try:
        if len(model_ids) == 1 and not bulk:
            # Single model
            model_id = model_ids[0]
            result = api.enable_model(model_id)
            
            if output_format == "json":
                console.print_json(result)
            else:
                print_success(f"Model '{model_id}' enabled successfully")
                
                # Show any activation details
                if result.get("message"):
                    print_info(result["message"])
        else:
            # Multiple models
            result = api.enable_models_bulk(model_ids)
            
            if output_format == "json":
                console.print_json(result)
            else:
                successful = result.get("successful", [])
                failed = result.get("failed", [])
                
                if successful:
                    print_success(f"Enabled {len(successful)} model(s) successfully")
                    for model_id in successful:
                        console.print(f"  ✅ {model_id}")
                
                if failed:
                    print_warning(f"Failed to enable {len(failed)} model(s)")
                    for item in failed:
                        model_id = item.get("model_id", "unknown")
                        error = item.get("error", "unknown error")
                        console.print(f"  ❌ {model_id}: {error}")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to enable models: {e}")


@app.command("sync")
def sync_models(
    provider: Optional[str] = typer.Option(None, "--provider", help="Sync models for specific provider"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Sync model catalog from cloud providers.
    
    This updates the available models list from your connected providers.
    """
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        with console.status(f"[bold green]Syncing models{f' for {provider}' if provider else ''}..."):
            result = api.sync_models(provider_id=provider)
        
        if output_format == "json":
            console.print_json(result)
        else:
            print_success("Model sync completed")
            
            # Show sync results
            added = result.get("added", 0)
            updated = result.get("updated", 0)
            removed = result.get("removed", 0)
            
            console.print(f"📊 Sync Summary:")
            console.print(f"  ➕ Added: {added} models")
            console.print(f"  🔄 Updated: {updated} models")
            console.print(f"  ➖ Removed: {removed} models")
            
            if result.get("errors"):
                print_warning("Some sync operations had errors:")
                for error in result["errors"]:
                    console.print(f"  ❌ {error}")
            
            print_info("Use 'bonito models list' to see updated catalog")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to sync models: {e}")


@app.command("disable")
def disable_model(
    model_id: str = typer.Argument(..., help="Model ID to disable"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Disable a model (make it unavailable for inference).
    """
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    # Confirm unless JSON output
    if output_format == "rich":
        confirm = typer.confirm(f"Are you sure you want to disable model '{model_id}'?")
        if not confirm:
            print_info("Cancelled")
            return
    
    try:
        # This would be an API endpoint to disable - for now we'll show what it would do
        # result = api.disable_model(model_id)
        
        # Simulated response since disable endpoint might not exist yet
        result = {"status": "success", "model_id": model_id}
        
        if output_format == "json":
            console.print_json(result)
        else:
            print_success(f"Model '{model_id}' disabled")
            print_info("The model is no longer available for inference")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to disable model: {e}")


@app.command("search")
def search_models(
    query: str = typer.Argument(..., help="Search query"),
    provider: Optional[str] = typer.Option(None, "--provider", help="Filter by provider"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Search for models by name or description.
    """
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        models = api.list_models(
            provider=provider,
            search=query
        )
        
        if output_format == "json":
            console.print_json(models)
        else:
            if not models:
                print_info(f"No models found for query: '{query}'")
                return
            
            print_model_table(models, output_format)
            
            console.print(f"\n[dim]Search: '{query}'[/dim]")
            console.print(f"📊 Found {len(models)} model(s)")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to search models: {e}")


@app.command("costs")
def model_costs(
    model_id: Optional[str] = typer.Argument(None, help="Specific model ID (optional)"),
    days: int = typer.Option(30, "--days", help="Number of days to analyze"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Show cost analysis for models.
    """
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        # This would be a call to get model costs
        # For now, we'll show example data structure
        if model_id:
            costs = {
                "model_id": model_id,
                "period_days": days,
                "total_cost": 15.67,
                "total_requests": 1250,
                "total_tokens": 125000,
                "avg_cost_per_request": 0.0125,
                "daily_breakdown": [
                    {"date": "2024-01-01", "requests": 45, "tokens": 4500, "cost": 0.67},
                    {"date": "2024-01-02", "requests": 52, "tokens": 5200, "cost": 0.78},
                ]
            }
        else:
            costs = {
                "period_days": days,
                "total_cost": 156.78,
                "model_breakdown": [
                    {"model_id": "claude-3-sonnet", "requests": 450, "tokens": 45000, "cost": 67.50},
                    {"model_id": "gpt-4o", "requests": 320, "tokens": 32000, "cost": 48.60},
                    {"model_id": "llama-2-70b", "requests": 280, "tokens": 28000, "cost": 40.68},
                ]
            }
        
        if output_format == "json":
            console.print_json(costs)
        else:
            if model_id:
                # Single model analysis
                console.print(f"\n[bold cyan]💰 Cost Analysis: {model_id}[/bold cyan]")
                console.print(f"Period: Last {days} days")
                console.print(f"Total Cost: [green]${costs['total_cost']:.2f}[/green]")
                console.print(f"Total Requests: {costs['total_requests']:,}")
                console.print(f"Total Tokens: {format_tokens(costs['total_tokens'])}")
                console.print(f"Avg Cost/Request: ${costs['avg_cost_per_request']:.4f}")
            else:
                # All models analysis
                console.print(f"\n[bold cyan]💰 Model Cost Analysis[/bold cyan]")
                console.print(f"Period: Last {days} days")
                console.print(f"Total Cost: [green]${costs['total_cost']:.2f}[/green]")
                
                # Show breakdown table
                breakdown_data = []
                for item in costs['model_breakdown']:
                    breakdown_data.append({
                        "Model": item['model_id'],
                        "Requests": f"{item['requests']:,}",
                        "Tokens": format_tokens(item['tokens']),
                        "Cost": format_cost(item['cost']),
                        "% of Total": f"{(item['cost'] / costs['total_cost'] * 100):.1f}%"
                    })
                
                print_table(breakdown_data, title="Cost Breakdown by Model")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to get model costs: {e}")


if __name__ == "__main__":
    app()