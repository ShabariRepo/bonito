"""Agent Groups CLI commands.

Manage agent groups for RBAC and organization: create, list, update, delete.
Note: This feature requires the RBAC groups backend to be implemented.
"""

import json
from typing import Optional, List
from decimal import Decimal

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from ..api import APIClient
from ..utils.display import (
    success_panel, error_panel, info_panel,
    format_currency, format_datetime
)

console = Console()
app = typer.Typer(help="👥 Groups — Agent group management (RBAC)")


@app.command("list")
def list_groups(
    project_id: Optional[str] = typer.Option(None, "--project", "-p", help="Project ID to filter groups"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """List agent groups in a project or all projects."""
    client = APIClient()
    
    # Note: This endpoint doesn't exist yet in the backend
    try:
        if project_id:
            response = client.get(f"/api/projects/{project_id}/groups")
        else:
            response = client.get("/api/groups")
    except Exception as e:
        if "404" in str(e):
            console.print(error_panel(
                "❌ Agent Groups feature not available yet.\n"
                "This requires the RBAC groups backend implementation."
            ))
            raise typer.Exit(1)
        raise
    
    if json_output:
        console.print(json.dumps(response, indent=2, default=str))
        return
    
    if not response:
        console.print(info_panel("No agent groups found."))
        return
    
    table = Table(title="Agent Groups")
    table.add_column("Name", style="cyan")
    table.add_column("Project", style="blue")
    table.add_column("Agents", justify="right")
    table.add_column("Budget Limit", justify="right")
    table.add_column("KB Count", justify="right")
    table.add_column("Created", style="dim")
    
    for group in response:
        budget_str = format_currency(group.get('budget_limit')) if group.get('budget_limit') else "No limit"
        kb_count = len(group.get('knowledge_base_ids', []))
        
        table.add_row(
            group["name"],
            group.get("project_name", "Unknown"),
            str(group.get("agent_count", 0)),
            budget_str,
            str(kb_count),
            format_datetime(group["created_at"])
        )
    
    console.print(table)


@app.command("create")
def create_group(
    project_id: str = typer.Option(..., "--project", "-p", help="Project ID"),
    name: str = typer.Option(..., "--name", "-n", help="Group name"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Group description"),
    budget_limit: Optional[str] = typer.Option(None, "--budget", "-b", help="Budget limit (e.g., '50.00')"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """Create a new agent group."""
    client = APIClient()
    
    payload = {
        "name": name,
        "description": description,
        "project_id": project_id,
    }
    
    # Parse budget limit
    if budget_limit:
        try:
            payload["budget_limit"] = str(Decimal(budget_limit))
        except ValueError:
            console.print(error_panel(f"Invalid budget format: {budget_limit}. Use decimal format like '50.00'"))
            raise typer.Exit(1)
    
    try:
        response = client.post("/api/groups", json=payload)
    except Exception as e:
        if "404" in str(e):
            console.print(error_panel(
                "❌ Agent Groups feature not available yet.\n"
                "This requires the RBAC groups backend implementation."
            ))
            raise typer.Exit(1)
        raise
    
    if json_output:
        console.print(json.dumps(response, indent=2, default=str))
        return
    
    console.print(success_panel(f"✅ Agent group '{name}' created successfully!"))
    console.print(f"Group ID: [cyan]{response['id']}[/cyan]")


@app.command("info")
def group_info(
    group_id: str = typer.Argument(..., help="Group ID"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """Get detailed information about an agent group."""
    client = APIClient()
    
    try:
        response = client.get(f"/api/groups/{group_id}")
    except Exception as e:
        if "404" in str(e):
            console.print(error_panel(
                "❌ Agent Groups feature not available yet.\n"
                "This requires the RBAC groups backend implementation."
            ))
            raise typer.Exit(1)
        raise
    
    if json_output:
        console.print(json.dumps(response, indent=2, default=str))
        return
    
    # Group details
    group = response
    
    info_text = f"""[bold cyan]Name:[/bold cyan] {group['name']}
[bold cyan]Project ID:[/bold cyan] {group['project_id']}
[bold cyan]Agent Count:[/bold cyan] {group.get('agent_count', 0)}
[bold cyan]Created:[/bold cyan] {format_datetime(group['created_at'])}"""
    
    if group.get("description"):
        info_text = f"[bold cyan]Description:[/bold cyan] {group['description']}\n" + info_text
    
    # Budget info
    if group.get('budget_limit'):
        info_text += f"\n[bold cyan]Budget Limit:[/bold cyan] {format_currency(group['budget_limit'])}"
    
    # Knowledge base count
    kb_count = len(group.get('knowledge_base_ids', []))
    if kb_count > 0:
        info_text += f"\n[bold cyan]Knowledge Bases:[/bold cyan] {kb_count}"
    
    console.print(Panel(info_text, title="Group Details"))
    
    # Tool policy
    if group.get('tool_policy'):
        policy_text = json.dumps(group['tool_policy'], indent=2)
        console.print(Panel(policy_text, title="Tool Policy", border_style="blue"))
    
    # Model allowlist
    if group.get('model_allowlist'):
        models_text = "\n".join(group['model_allowlist'])
        console.print(Panel(models_text, title="Allowed Models", border_style="green"))


@app.command("update")
def update_group(
    group_id: str = typer.Argument(..., help="Group ID"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Update group name"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Update description"),
    budget_limit: Optional[str] = typer.Option(None, "--budget", "-b", help="Update budget limit"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """Update agent group configuration."""
    client = APIClient()
    
    payload = {}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if budget_limit is not None:
        try:
            payload["budget_limit"] = str(Decimal(budget_limit))
        except ValueError:
            console.print(error_panel(f"Invalid budget format: {budget_limit}. Use decimal format like '50.00'"))
            raise typer.Exit(1)
    
    if not payload:
        console.print(error_panel("No updates specified"))
        raise typer.Exit(1)
    
    try:
        response = client.put(f"/api/groups/{group_id}", json=payload)
    except Exception as e:
        if "404" in str(e):
            console.print(error_panel(
                "❌ Agent Groups feature not available yet.\n"
                "This requires the RBAC groups backend implementation."
            ))
            raise typer.Exit(1)
        raise
    
    if json_output:
        console.print(json.dumps(response, indent=2, default=str))
        return
    
    console.print(success_panel("✅ Agent group updated successfully!"))


@app.command("delete")
def delete_group(
    group_id: str = typer.Argument(..., help="Group ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete an agent group."""
    client = APIClient()
    
    if not force:
        try:
            # Get group info first
            group = client.get(f"/api/groups/{group_id}")
            
            # Warn if group has agents
            if group.get('agent_count', 0) > 0:
                console.print(f"[yellow]Warning: This group has {group['agent_count']} agents.[/yellow]")
                console.print("[yellow]Agents will be moved to no group.[/yellow]")
            
            confirmed = Confirm.ask(f"Are you sure you want to delete group '{group['name']}'?")
            if not confirmed:
                console.print("Cancelled.")
                return
        except Exception as e:
            if "404" in str(e):
                console.print(error_panel(
                    "❌ Agent Groups feature not available yet.\n"
                    "This requires the RBAC groups backend implementation."
                ))
                raise typer.Exit(1)
            raise
    
    try:
        client.delete(f"/api/groups/{group_id}")
    except Exception as e:
        if "404" in str(e):
            console.print(error_panel(
                "❌ Agent Groups feature not available yet.\n"
                "This requires the RBAC groups backend implementation."
            ))
            raise typer.Exit(1)
        raise
    
    console.print(success_panel("✅ Agent group deleted successfully!"))


@app.command("assign")
def assign_agent(
    group_id: str = typer.Argument(..., help="Group ID"),
    agent_id: str = typer.Argument(..., help="Agent ID to assign to group"),
):
    """Assign an agent to a group."""
    client = APIClient()
    
    try:
        # This would be a PUT or PATCH to the agent to update its group_id
        payload = {"group_id": group_id}
        client.put(f"/api/agents/{agent_id}", json=payload)
    except Exception as e:
        if "404" in str(e):
            console.print(error_panel(
                "❌ Agent Groups feature not available yet.\n"
                "This requires the RBAC groups backend implementation."
            ))
            raise typer.Exit(1)
        raise
    
    console.print(success_panel("✅ Agent assigned to group successfully!"))


@app.command("unassign")
def unassign_agent(
    agent_id: str = typer.Argument(..., help="Agent ID to remove from group"),
):
    """Remove an agent from its group."""
    client = APIClient()
    
    try:
        # This would set group_id to null
        payload = {"group_id": None}
        client.put(f"/api/agents/{agent_id}", json=payload)
    except Exception as e:
        if "404" in str(e):
            console.print(error_panel(
                "❌ Agent Groups feature not available yet.\n"
                "This requires the RBAC groups backend implementation."
            ))
            raise typer.Exit(1)
        raise
    
    console.print(success_panel("✅ Agent removed from group successfully!"))


if __name__ == "__main__":
    app()