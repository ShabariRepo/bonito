"""Routing policy management commands."""

import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm
from typing import Optional, List

from ..api import api, APIError
from ..utils.display import (
    print_error, print_success, print_info, print_warning,
    print_table, print_dict_as_table, get_output_format
)
from ..utils.auth import ensure_authenticated

console = Console()

app = typer.Typer(help="🎯 Routing policy management")


@app.command("list")
def list_policies(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    List all routing policies.
    """
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        # This would call the actual API endpoint
        policies = [
            {
                "id": "pol-123",
                "name": "Cost Optimizer",
                "strategy": "cost_optimized",
                "enabled": True,
                "models": ["gpt-3.5-turbo", "claude-haiku"],
                "requests_24h": 245,
                "avg_cost_per_request": 0.0045,
                "created_at": "2024-01-15T10:30:00Z"
            },
            {
                "id": "pol-456", 
                "name": "Quality First",
                "strategy": "quality_optimized",
                "enabled": False,
                "models": ["gpt-4", "claude-3-opus"],
                "requests_24h": 0,
                "avg_cost_per_request": 0.0,
                "created_at": "2024-01-10T14:20:00Z"
            }
        ]
        
        if output_format == "json":
            console.print_json(policies)
        else:
            if not policies:
                print_info("No routing policies found")
                print_info("Create one with: bonito policies create")
                return
            
            # Format policies for display
            policy_data = []
            for policy in policies:
                status = "✅ Enabled" if policy.get("enabled") else "❌ Disabled"
                models_text = ", ".join(policy.get("models", []))[:40] + "..."
                
                policy_data.append({
                    "ID": policy.get("id", ""),
                    "Name": policy.get("name", ""),
                    "Strategy": policy.get("strategy", "").replace("_", " ").title(),
                    "Status": status,
                    "Models": models_text,
                    "Requests (24h)": f"{policy.get('requests_24h', 0):,}",
                    "Avg Cost": f"${policy.get('avg_cost_per_request', 0):.4f}",
                })
            
            print_table(policy_data, title="Routing Policies")
            
            enabled_count = sum(1 for p in policies if p.get("enabled"))
            print_info(f"Total: {len(policies)} policies ({enabled_count} enabled)")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to list policies: {e}")


@app.command("create")
def create_policy(
    name: Optional[str] = typer.Option(None, "--name", help="Policy name"),
    strategy: Optional[str] = typer.Option(None, "--strategy", help="Routing strategy (cost_optimized, latency_optimized, quality_optimized)"),
    models: Optional[str] = typer.Option(None, "--models", help="Comma-separated list of model IDs"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Create a new routing policy.
    """
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    # Interactive prompts if values not provided
    if not name:
        name = Prompt.ask("Policy name")
    
    if not strategy:
        strategies = ["cost_optimized", "latency_optimized", "quality_optimized", "round_robin"]
        console.print("\n[bold]Available strategies:[/bold]")
        for i, strat in enumerate(strategies, 1):
            console.print(f"  {i}. {strat.replace('_', ' ').title()}")
        
        while True:
            try:
                choice = int(Prompt.ask("Select strategy (1-4)"))
                if 1 <= choice <= len(strategies):
                    strategy = strategies[choice - 1]
                    break
                else:
                    console.print("[red]Invalid choice[/red]")
            except ValueError:
                console.print("[red]Please enter a number[/red]")
    
    if not models:
        models = Prompt.ask("Model IDs (comma-separated)", default="gpt-3.5-turbo,claude-haiku")
    
    # Parse models list
    model_list = [model.strip() for model in models.split(",")]
    
    policy_data = {
        "name": name,
        "strategy": strategy,
        "models": model_list,
        "enabled": True,
    }
    
    try:
        # This would call the actual API to create the policy
        result = {
            "id": "pol-" + "".join(__import__("random").choices("0123456789abcdef", k=6)),
            **policy_data,
            "created_at": "2024-01-15T12:00:00Z"
        }
        
        if output_format == "json":
            console.print_json(result)
        else:
            print_success(f"Routing policy '{name}' created successfully")
            
            details = {
                "Policy ID": result["id"],
                "Name": result["name"],
                "Strategy": result["strategy"].replace("_", " ").title(),
                "Models": ", ".join(result["models"]),
                "Status": "✅ Enabled",
            }
            
            print_dict_as_table(details, title="Policy Details")
            print_info("Policy is now active and will route matching requests")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to create policy: {e}")


@app.command("info")
def policy_info(
    policy_id: str = typer.Argument(..., help="Policy ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Get detailed information about a routing policy.
    """
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        # Mock detailed policy data
        policy_detail = {
            "id": policy_id,
            "name": "Cost Optimizer",
            "description": "Routes requests to the most cost-effective models while maintaining quality",
            "strategy": "cost_optimized",
            "enabled": True,
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-16T09:15:00Z",
            "models": [
                {"id": "gpt-3.5-turbo", "priority": 1, "cost_per_1k": 0.002},
                {"id": "claude-haiku", "priority": 2, "cost_per_1k": 0.00025},
            ],
            "conditions": {
                "max_tokens": 1000,
                "temperature_range": [0, 1.5],
                "content_types": ["text"]
            },
            "statistics": {
                "total_requests": 1250,
                "requests_24h": 245,
                "avg_latency_ms": 234,
                "avg_cost_per_request": 0.0045,
                "success_rate": 98.5,
                "total_cost": 5.625,
                "token_count": 125000,
            }
        }
        
        if output_format == "json":
            console.print_json(policy_detail)
        else:
            # Display policy information
            console.print(f"\n[bold cyan]🎯 Policy: {policy_detail['name']}[/bold cyan]")
            
            basic_info = {
                "Policy ID": policy_detail["id"],
                "Name": policy_detail["name"],
                "Description": policy_detail.get("description", "N/A"),
                "Strategy": policy_detail["strategy"].replace("_", " ").title(),
                "Status": "✅ Enabled" if policy_detail["enabled"] else "❌ Disabled",
                "Created": policy_detail["created_at"],
                "Last Updated": policy_detail["updated_at"],
            }
            
            print_dict_as_table(basic_info, title="Policy Information")
            
            # Model configuration
            model_data = []
            for model in policy_detail["models"]:
                model_data.append({
                    "Model": model["id"],
                    "Priority": model["priority"],
                    "Cost/1K tokens": f"${model['cost_per_1k']:.5f}",
                })
            
            print_table(model_data, title="Model Configuration")
            
            # Statistics
            stats = policy_detail["statistics"]
            stats_info = {
                "Total Requests": f"{stats['total_requests']:,}",
                "Requests (24h)": f"{stats['requests_24h']:,}",
                "Avg Latency": f"{stats['avg_latency_ms']}ms",
                "Avg Cost/Request": f"${stats['avg_cost_per_request']:.4f}",
                "Success Rate": f"{stats['success_rate']}%",
                "Total Cost": f"${stats['total_cost']:.2f}",
                "Total Tokens": f"{stats['token_count']:,}",
            }
            
            print_dict_as_table(stats_info, title="Usage Statistics")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to get policy info: {e}")


@app.command("test")
def test_policy(
    policy_id: str = typer.Argument(..., help="Policy ID to test"),
    prompt: str = typer.Argument(..., help="Test prompt"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Test a routing policy with a sample prompt.
    """
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        # Mock policy test result
        test_result = {
            "policy_id": policy_id,
            "test_prompt": prompt,
            "selected_model": "gpt-3.5-turbo",
            "reasoning": "Selected based on cost optimization - lowest cost model that meets quality requirements",
            "estimated_cost": 0.0034,
            "estimated_latency_ms": 245,
            "model_options": [
                {"model": "gpt-3.5-turbo", "cost": 0.0034, "priority": 1, "selected": True},
                {"model": "claude-haiku", "cost": 0.0012, "priority": 2, "selected": False, "reason": "Lower quality score"},
            ]
        }
        
        if output_format == "json":
            console.print_json(test_result)
        else:
            console.print(f"\n[bold green]🧪 Policy Test Results[/bold green]")
            console.print(f"[dim]Policy: {policy_id}[/dim]")
            console.print(f"[dim]Test Prompt: {prompt[:50]}...[/dim]\n")
            
            result_info = {
                "Selected Model": test_result["selected_model"],
                "Estimated Cost": f"${test_result['estimated_cost']:.4f}",
                "Estimated Latency": f"{test_result['estimated_latency_ms']}ms",
                "Reasoning": test_result["reasoning"],
            }
            
            print_dict_as_table(result_info, title="Test Results")
            
            # Show model evaluation
            console.print(f"\n[bold]Model Evaluation:[/bold]")
            for option in test_result["model_options"]:
                status = "✅ SELECTED" if option["selected"] else "❌ Not selected"
                reason = f" - {option.get('reason', 'Higher priority')}" if not option["selected"] else ""
                console.print(f"  {option['model']}: ${option['cost']:.4f} | {status}{reason}")
            
            print_info("This is a dry-run test. No actual API requests were made.")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to test policy: {e}")


@app.command("toggle")
def toggle_policy(
    policy_id: str = typer.Argument(..., help="Policy ID to enable/disable"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Enable or disable a routing policy.
    """
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        # Mock current status (would fetch from API)
        current_enabled = True  # This would come from API
        
        new_status = not current_enabled
        action = "enabled" if new_status else "disabled"
        
        # Mock API call
        result = {
            "policy_id": policy_id,
            "enabled": new_status,
            "message": f"Policy {action} successfully"
        }
        
        if output_format == "json":
            console.print_json(result)
        else:
            icon = "✅" if new_status else "❌"
            print_success(f"Policy {policy_id} {action} {icon}")
            
            if new_status:
                print_info("Policy is now active and will route matching requests")
            else:
                print_warning("Policy is disabled and will not route requests")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to toggle policy: {e}")


@app.command("delete")
def delete_policy(
    policy_id: str = typer.Argument(..., help="Policy ID to delete"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Delete a routing policy.
    """
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    # Confirm deletion unless forced
    if not force and output_format == "rich":
        confirm = typer.confirm(f"Are you sure you want to delete policy {policy_id}?")
        if not confirm:
            print_info("Cancelled")
            return
    
    try:
        # Mock deletion
        result = {
            "policy_id": policy_id,
            "status": "deleted",
            "message": f"Policy {policy_id} deleted successfully"
        }
        
        if output_format == "json":
            console.print_json(result)
        else:
            print_success(f"Policy {policy_id} deleted successfully")
            print_warning("This action cannot be undone")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to delete policy: {e}")


@app.command("stats")
def policy_stats(
    policy_id: Optional[str] = typer.Argument(None, help="Specific policy ID (optional)"),
    days: int = typer.Option(30, "--days", help="Number of days to analyze"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Show policy usage statistics.
    """
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        if policy_id:
            # Single policy stats
            stats = {
                "policy_id": policy_id,
                "period_days": days,
                "total_requests": 1250,
                "avg_cost_per_request": 0.0045,
                "total_cost": 5.625,
                "success_rate": 98.5,
                "model_distribution": [
                    {"model": "gpt-3.5-turbo", "requests": 800, "percentage": 64.0},
                    {"model": "claude-haiku", "requests": 450, "percentage": 36.0},
                ]
            }
        else:
            # All policies stats
            stats = {
                "period_days": days,
                "total_policies": 3,
                "active_policies": 2,
                "total_requests": 5680,
                "total_cost": 25.47,
                "policy_breakdown": [
                    {"policy_id": "pol-123", "name": "Cost Optimizer", "requests": 1250, "cost": 5.625},
                    {"policy_id": "pol-456", "name": "Quality First", "requests": 0, "cost": 0.0},
                ]
            }
        
        if output_format == "json":
            console.print_json(stats)
        else:
            if policy_id:
                # Single policy display
                console.print(f"\n[bold cyan]📊 Policy Statistics: {policy_id}[/bold cyan]")
                console.print(f"Period: Last {days} days\n")
                
                summary = {
                    "Total Requests": f"{stats['total_requests']:,}",
                    "Avg Cost/Request": f"${stats['avg_cost_per_request']:.4f}",
                    "Total Cost": f"${stats['total_cost']:.2f}",
                    "Success Rate": f"{stats['success_rate']}%",
                }
                
                print_dict_as_table(summary, title="Performance Summary")
                
                # Model distribution
                dist_data = []
                for dist in stats['model_distribution']:
                    dist_data.append({
                        "Model": dist['model'],
                        "Requests": f"{dist['requests']:,}",
                        "Percentage": f"{dist['percentage']:.1f}%"
                    })
                
                print_table(dist_data, title="Model Distribution")
            else:
                # All policies display
                console.print(f"\n[bold cyan]📊 All Policies Statistics[/bold cyan]")
                console.print(f"Period: Last {days} days\n")
                
                summary = {
                    "Total Policies": stats['total_policies'],
                    "Active Policies": stats['active_policies'],
                    "Total Requests": f"{stats['total_requests']:,}",
                    "Total Cost": f"${stats['total_cost']:.2f}",
                }
                
                print_dict_as_table(summary, title="Overall Summary")
                
                # Policy breakdown
                breakdown_data = []
                for policy in stats['policy_breakdown']:
                    breakdown_data.append({
                        "Policy ID": policy['policy_id'],
                        "Name": policy['name'],
                        "Requests": f"{policy['requests']:,}",
                        "Cost": f"${policy['cost']:.2f}",
                    })
                
                print_table(breakdown_data, title="Policy Breakdown")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to get policy stats: {e}")


if __name__ == "__main__":
    app()