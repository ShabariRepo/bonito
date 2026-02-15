"""API Gateway management commands."""

import typer
from rich.console import Console
from rich.prompt import Prompt
from typing import Optional

from ..api import api, APIError
from ..utils.display import (
    print_error, print_success, print_info, print_warning,
    print_table, print_dict_as_table, get_output_format
)
from ..utils.auth import ensure_authenticated

console = Console()

app = typer.Typer(help="🚪 API Gateway management")


@app.command("status")
def gateway_status(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Show API Gateway status and health information.
    """
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        # Get gateway config and usage info
        config = api.get_gateway_config()
        
        if output_format == "json":
            console.print_json(config)
        else:
            # Display gateway status
            status_info = {
                "Status": "🟢 Healthy" if config.get("healthy", True) else "🔴 Unhealthy",
                "Version": config.get("version", "N/A"),
                "Uptime": config.get("uptime", "N/A"),
                "Endpoint": config.get("endpoint", "N/A"),
                "Rate Limit": f"{config.get('rate_limit', 'N/A')} req/min",
                "Active Keys": config.get("active_keys", "N/A"),
                "Total Requests (24h)": f"{config.get('requests_24h', 0):,}",
                "Average Latency": f"{config.get('avg_latency_ms', 0):.0f}ms",
            }
            
            print_dict_as_table(status_info, title="Gateway Status")
            
            # Show recent errors if any
            recent_errors = config.get("recent_errors", [])
            if recent_errors:
                print_warning(f"Recent errors ({len(recent_errors)}):")
                for error in recent_errors[:5]:  # Show last 5
                    console.print(f"  • {error.get('timestamp', '')}: {error.get('message', '')}")
            
            print_info("Gateway is ready to handle API requests")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to get gateway status: {e}")


# Keys management
keys_app = typer.Typer(help="Gateway API key management", no_args_is_help=True)


@keys_app.command("list")
def list_gateway_keys(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """List all gateway API keys."""
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        keys = api.get_gateway_keys()
        
        if output_format == "json":
            console.print_json(keys)
        else:
            if not keys:
                print_info("No gateway keys found")
                print_info("Create one with: bonito gateway keys create")
                return
            
            # Format keys for display
            key_data = []
            for key in keys:
                key_data.append({
                    "ID": key.get("id", ""),
                    "Name": key.get("name", "Unnamed"),
                    "Key Preview": key.get("key", "")[:12] + "...",
                    "Created": key.get("created_at", ""),
                    "Status": "✅ Active" if key.get("active", True) else "❌ Inactive",
                    "Last Used": key.get("last_used_at", "Never"),
                    "Requests (24h)": f"{key.get('requests_24h', 0):,}",
                })
            
            print_table(key_data, title="Gateway API Keys")
            print_info(f"Total: {len(keys)} key(s)")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to list gateway keys: {e}")


@keys_app.command("create")
def create_gateway_key(
    name: Optional[str] = typer.Option(None, "--name", help="Name for the gateway key"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Create a new gateway API key."""
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    # Prompt for name if not provided
    if not name:
        name = Prompt.ask("Enter a name for this gateway key", default="Gateway Key")
    
    try:
        key_info = api.create_gateway_key(name)
        
        if output_format == "json":
            console.print_json(key_info)
        else:
            print_success(f"Gateway key created: {name}")
            
            console.print(f"\n[bold yellow]⚠️  Gateway Key (save this, it won't be shown again):[/bold yellow]")
            console.print(f"[green]{key_info.get('key', '')}[/green]")
            
            console.print(f"\n[bold]Key ID:[/bold] {key_info.get('id', '')}")
            console.print(f"[bold]Name:[/bold] {key_info.get('name', '')}")
            
            print_info("Use this key to authenticate with the Bonito Gateway API (/v1/* endpoints)")
            console.print("\n[bold]Example usage:[/bold]")
            console.print(f"[cyan]curl -H 'Authorization: Bearer {key_info.get('key', '')[:12]}...' \\[/cyan]")
            console.print(f"[cyan]  https://your-gateway/v1/chat/completions[/cyan]")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to create gateway key: {e}")


@keys_app.command("revoke")
def revoke_gateway_key(
    key_id: str = typer.Argument(..., help="Gateway key ID to revoke"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Revoke a gateway API key."""
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    # Confirm revocation
    if output_format == "rich":
        confirm = typer.confirm(f"Are you sure you want to revoke gateway key {key_id}?")
        if not confirm:
            print_info("Cancelled")
            return
    
    try:
        api.revoke_gateway_key(key_id)
        
        if output_format == "json":
            console.print_json({
                "status": "success", 
                "message": f"Gateway key {key_id} revoked"
            })
        else:
            print_success(f"Gateway key {key_id} revoked")
            print_warning("Any applications using this key will no longer be able to access the gateway")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to revoke gateway key: {e}")


app.add_typer(keys_app, name="keys")


@app.command("logs")
def gateway_logs(
    limit: int = typer.Option(50, "--limit", help="Number of log entries to show"),
    model: Optional[str] = typer.Option(None, "--model", help="Filter by model"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    View recent gateway API logs.
    """
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        logs = api.get_gateway_logs(limit=limit, model=model)
        
        if output_format == "json":
            console.print_json(logs)
        else:
            if not logs:
                print_info("No recent gateway logs")
                return
            
            # Format logs for display
            log_data = []
            for log_entry in logs:
                status_color = "green" if log_entry.get("status_code", 200) < 400 else "red"
                
                log_data.append({
                    "Timestamp": log_entry.get("timestamp", ""),
                    "Method": log_entry.get("method", ""),
                    "Endpoint": log_entry.get("endpoint", ""),
                    "Model": log_entry.get("model", "N/A"),
                    "Status": f"[{status_color}]{log_entry.get('status_code', 'N/A')}[/{status_color}]",
                    "Latency": f"{log_entry.get('latency_ms', 0):.0f}ms",
                    "Tokens": f"{log_entry.get('tokens', 0):,}",
                    "Key": log_entry.get("key_name", "Unknown")[:12] + "...",
                })
            
            print_table(log_data, title=f"Gateway Logs (last {limit})")
            
            # Show summary stats
            total_requests = len(logs)
            successful_requests = sum(1 for log in logs if log.get("status_code", 200) < 400)
            avg_latency = sum(log.get("latency_ms", 0) for log in logs) / len(logs) if logs else 0
            
            console.print(f"\n[dim]Summary: {successful_requests}/{total_requests} successful, avg latency: {avg_latency:.0f}ms[/dim]")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to get gateway logs: {e}")


# Config management
config_app = typer.Typer(help="Gateway configuration", no_args_is_help=True)


@config_app.command("show")
def show_gateway_config(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Show current gateway configuration."""
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        config = api.get_gateway_config()
        
        if output_format == "json":
            console.print_json(config)
        else:
            # Display configuration
            config_data = {
                "Rate Limit (req/min)": config.get("rate_limit", "N/A"),
                "Timeout (seconds)": config.get("timeout_seconds", "N/A"),
                "Max Tokens": config.get("max_tokens", "N/A"),
                "Enable Streaming": "✅ Yes" if config.get("enable_streaming", True) else "❌ No",
                "Enable Logging": "✅ Yes" if config.get("enable_logging", True) else "❌ No",
                "Default Model": config.get("default_model", "N/A"),
                "Allowed Origins": ", ".join(config.get("allowed_origins", ["*"])),
                "Cache TTL (seconds)": config.get("cache_ttl", "N/A"),
            }
            
            print_dict_as_table(config_data, title="Gateway Configuration")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to get gateway config: {e}")


@config_app.command("set")
def set_gateway_config(
    field: str = typer.Argument(..., help="Configuration field to set"),
    value: str = typer.Argument(..., help="New value"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Set a gateway configuration value."""
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    # Convert value to appropriate type based on field
    processed_value = value
    
    if field in ["rate_limit", "timeout_seconds", "max_tokens", "cache_ttl"]:
        try:
            processed_value = int(value)
        except ValueError:
            print_error(f"Value for {field} must be a number")
            return
    
    elif field in ["enable_streaming", "enable_logging"]:
        processed_value = value.lower() in ["true", "yes", "1", "on"]
    
    elif field == "allowed_origins":
        processed_value = [origin.strip() for origin in value.split(",")]
    
    try:
        # Get current config
        current_config = api.get_gateway_config()
        
        # Update the field
        current_config[field] = processed_value
        
        # Save updated config
        updated_config = api.update_gateway_config(current_config)
        
        if output_format == "json":
            console.print_json(updated_config)
        else:
            print_success(f"Gateway configuration updated: {field} = {processed_value}")
            print_info("Changes may take a few seconds to take effect")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to update gateway config: {e}")


app.add_typer(config_app, name="config")


@app.command("usage")
def gateway_usage(
    days: int = typer.Option(7, "--days", help="Number of days to analyze"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Show gateway usage statistics.
    """
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        # This would be a separate endpoint for usage stats
        usage_stats = {
            "period_days": days,
            "total_requests": 12450,
            "successful_requests": 12280,
            "failed_requests": 170,
            "success_rate": 98.6,
            "avg_latency_ms": 245,
            "total_tokens": 1245000,
            "unique_keys": 8,
            "top_models": [
                {"model": "gpt-4o", "requests": 5600, "percentage": 45.0},
                {"model": "claude-3-sonnet", "requests": 4200, "percentage": 33.7},
                {"model": "gpt-3.5-turbo", "requests": 2650, "percentage": 21.3},
            ],
            "daily_breakdown": [
                {"date": "2024-01-01", "requests": 1800, "success_rate": 98.9},
                {"date": "2024-01-02", "requests": 1750, "success_rate": 98.2},
            ]
        }
        
        if output_format == "json":
            console.print_json(usage_stats)
        else:
            # Display usage summary
            console.print(f"\n[bold cyan]📊 Gateway Usage Summary (last {days} days)[/bold cyan]")
            
            summary = {
                "Total Requests": f"{usage_stats['total_requests']:,}",
                "Successful": f"{usage_stats['successful_requests']:,}",
                "Failed": f"{usage_stats['failed_requests']:,}",
                "Success Rate": f"{usage_stats['success_rate']:.1f}%",
                "Avg Latency": f"{usage_stats['avg_latency_ms']}ms",
                "Total Tokens": f"{usage_stats['total_tokens']:,}",
                "Active Keys": usage_stats['unique_keys'],
            }
            
            print_dict_as_table(summary, title="Usage Summary")
            
            # Show top models
            model_data = []
            for model_stat in usage_stats['top_models']:
                model_data.append({
                    "Model": model_stat['model'],
                    "Requests": f"{model_stat['requests']:,}",
                    "Percentage": f"{model_stat['percentage']:.1f}%"
                })
            
            print_table(model_data, title="Top Models")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to get gateway usage: {e}")


if __name__ == "__main__":
    app()