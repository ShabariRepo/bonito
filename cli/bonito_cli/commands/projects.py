"""Bonobot Projects CLI commands.

Manage AI agent projects: create, list, update, delete, and visualize project graphs.
"""

import json
from typing import Optional
from decimal import Decimal

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from ..api import api, APIError
from ..utils.auth import ensure_authenticated
from ..utils.display import (
    print_success, print_error, print_info,
    format_cost, format_timestamp, get_output_format,
    print_json_or_table, format_status
)

console = Console()
app = typer.Typer(help="📁 Projects — AI agent project management")


@app.command("list")
def list_projects(
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """List all projects in your organization."""
    ensure_authenticated()
    fmt = get_output_format(json_output)
    
    try:
        with console.status("[cyan]Fetching projects…[/cyan]"):
            response = api.get("/projects")
    except APIError as e:
        print_error(f"Failed to fetch projects: {e}")
        return
    
    if fmt == "json":
        console.print_json(json.dumps(response, default=str))
        return
    
    if not response:
        print_info("No projects found. Create one with 'bonito projects create'.")
        return
    
    table = Table(title="Projects")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Agents", justify="right")
    table.add_column("Budget", justify="right")
    table.add_column("Spent", justify="right")
    table.add_column("Created", style="dim")
    
    for project in response:
        budget_str = format_cost(project.get('budget_monthly')) if project.get('budget_monthly') else "No limit"
        spent_str = format_cost(project.get('budget_spent', 0))
        
        # Color code spent vs budget
        if project.get('budget_monthly') and project.get('budget_spent'):
            spent_pct = float(project['budget_spent']) / float(project['budget_monthly'])
            if spent_pct > 0.8:
                spent_str = f"[red]{spent_str}[/red]"
            elif spent_pct > 0.6:
                spent_str = f"[yellow]{spent_str}[/yellow]"
        
        table.add_row(
            project["name"],
            format_status(project["status"]),
            str(project.get("agent_count", 0)),
            budget_str,
            spent_str,
            format_timestamp(project["created_at"])
        )
    
    console.print(table)


@app.command("create")
def create_project(
    name: str = typer.Option(..., "--name", "-n", help="Project name"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Project description"),
    budget: Optional[str] = typer.Option(None, "--budget", "-b", help="Monthly budget (e.g., '100.00')"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """Create a new project."""
    ensure_authenticated()
    fmt = get_output_format(json_output)
    
    payload = {
        "name": name,
        "description": description,
    }
    
    # Parse budget
    if budget:
        try:
            payload["budget_monthly"] = str(Decimal(budget))
        except ValueError:
            print_error(f"Invalid budget format: {budget}. Use decimal format like '100.00'")
            return
    
    try:
        response = api.post("/projects", data=payload)
    except APIError as e:
        print_error(f"Failed to create project: {e}")
        return
    
    if fmt == "json":
        console.print_json(json.dumps(response, default=str))
        return
    
    print_success(f"Project '{name}' created successfully!")
    console.print(f"Project ID: [cyan]{response['id']}[/cyan]")


@app.command("info")
def project_info(
    project_id: str = typer.Argument(..., help="Project ID or name"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """Get detailed information about a project."""
    ensure_authenticated()
    fmt = get_output_format(json_output)
    
    # Try to get project by ID first, fallback to searching by name
    try:
        response = api.get(f"/projects/{project_id}")
    except APIError:
        # If not found by ID, search by name
        try:
            projects = api.get("/projects")
            matching = [p for p in projects if p['name'].lower() == project_id.lower()]
            if not matching:
                print_error(f"Project not found: {project_id}")
                return
            response = matching[0]
        except APIError as e:
            print_error(f"Failed to fetch project info: {e}")
            return
    
    if fmt == "json":
        console.print_json(json.dumps(response, default=str))
        return
    
    # Project details
    project = response
    
    info_text = f"""[bold cyan]Name:[/bold cyan] {project['name']}
[bold cyan]Status:[/bold cyan] {format_status(project['status'])}
[bold cyan]Agent Count:[/bold cyan] {project.get('agent_count', 0)}
[bold cyan]Created:[/bold cyan] {format_timestamp(project['created_at'])}"""
    
    if project.get("description"):
        info_text = f"[bold cyan]Description:[/bold cyan] {project['description']}\n" + info_text
    
    # Budget info
    budget_info = []
    if project.get('budget_monthly'):
        budget_spent = project.get('budget_spent', 0)
        budget_pct = (float(budget_spent) / float(project['budget_monthly'])) * 100
        
        budget_info.append(f"[bold cyan]Monthly Budget:[/bold cyan] {format_cost(project['budget_monthly'])}")
        budget_info.append(f"[bold cyan]Spent This Month:[/bold cyan] {format_cost(budget_spent)}")
        budget_info.append(f"[bold cyan]Budget Used:[/bold cyan] {budget_pct:.1f}%")
    else:
        budget_info.append("[bold cyan]Budget:[/bold cyan] No limit set")
    
    if budget_info:
        info_text += "\n" + "\n".join(budget_info)
    
    console.print(Panel(info_text, title="Project Details"))
    
    # Settings
    if project.get('settings'):
        settings_text = json.dumps(project['settings'], indent=2)
        console.print(Panel(settings_text, title="Settings", border_style="blue"))


@app.command("update")
def update_project(
    project_id: str = typer.Argument(..., help="Project ID"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Update project name"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Update description"),
    budget: Optional[str] = typer.Option(None, "--budget", "-b", help="Update monthly budget"),
    status: Optional[str] = typer.Option(None, "--status", help="Update status (active/paused/archived)"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """Update project configuration."""
    ensure_authenticated()
    fmt = get_output_format(json_output)
    
    payload = {}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if status is not None:
        if status not in ["active", "paused", "archived"]:
            print_error("Status must be one of: active, paused, archived")
            return
        payload["status"] = status
    if budget is not None:
        try:
            payload["budget_monthly"] = str(Decimal(budget))
        except ValueError:
            print_error(f"Invalid budget format: {budget}. Use decimal format like '100.00'")
            return
    
    if not payload:
        print_error("No updates specified")
        return
    
    try:
        response = api.put(f"/projects/{project_id}", data=payload)
    except APIError as e:
        print_error(f"Failed to update project: {e}")
        return
    
    if fmt == "json":
        console.print_json(json.dumps(response, default=str))
        return
    
    print_success("Project updated successfully!")


@app.command("delete")
def delete_project(
    project_id: str = typer.Argument(..., help="Project ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete (archive) a project."""
    ensure_authenticated()
    
    if not force:
        # Get project info first
        try:
            project = api.get(f"/projects/{project_id}")
        except APIError as e:
            print_error(f"Failed to fetch project info: {e}")
            return
        
        # Warn if project has agents
        if project.get('agent_count', 0) > 0:
            console.print(f"[yellow]Warning: This project has {project['agent_count']} agents.[/yellow]")
        
        confirmed = Confirm.ask(f"Are you sure you want to archive project '{project['name']}'?")
        if not confirmed:
            console.print("Cancelled.")
            return
    
    try:
        api.delete(f"/projects/{project_id}")
    except APIError as e:
        print_error(f"Failed to delete project: {e}")
        return
    
    print_success("Project archived successfully!")


@app.command("graph")
def project_graph(
    project_id: str = typer.Argument(..., help="Project ID"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Save graph data to JSON file"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """Get project graph data for visualization."""
    ensure_authenticated()
    fmt = get_output_format(json_output)
    
    try:
        response = api.get(f"/projects/{project_id}/graph")
    except APIError as e:
        print_error(f"Failed to fetch project graph: {e}")
        return
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(response, f, indent=2, default=str)
        print_success(f"Graph data saved to {output_file}")
        return
    
    if fmt == "json":
        console.print_json(json.dumps(response, default=str))
        return
    
    # Display summary
    nodes = response.get('nodes', [])
    edges = response.get('edges', [])
    
    agent_nodes = [n for n in nodes if n['type'] == 'agent']
    trigger_nodes = [n for n in nodes if n['type'] == 'trigger']
    
    summary_text = f"""[bold cyan]Nodes:[/bold cyan] {len(nodes)} total
  • {len(agent_nodes)} agents
  • {len(trigger_nodes)} triggers

[bold cyan]Edges:[/bold cyan] {len(edges)} total"""
    
    console.print(Panel(summary_text, title="Project Graph Summary"))
    
    # Show agents
    if agent_nodes:
        agent_table = Table(title="Agents")
        agent_table.add_column("Name", style="cyan")
        agent_table.add_column("Status", style="green")
        agent_table.add_column("Model", style="blue")
        agent_table.add_column("Runs", justify="right")
        agent_table.add_column("Cost", justify="right")
        
        for node in agent_nodes:
            data = node['data']
            agent_table.add_row(
                data['name'],
                format_status(data['status']),
                data['model_id'],
                str(data['total_runs']),
                format_cost(data['total_cost'])
            )
        
        console.print(agent_table)
    
    # Show connections
    connection_edges = [e for e in edges if e['type'] == 'connection']
    if connection_edges:
        conn_table = Table(title="Agent Connections")
        conn_table.add_column("From", style="cyan")
        conn_table.add_column("To", style="cyan")
        conn_table.add_column("Type", style="blue")
        conn_table.add_column("Label")
        
        for edge in connection_edges:
            data = edge['data']
            conn_table.add_row(
                data.get('source_name', 'Unknown'),
                data.get('target_name', 'Unknown'),
                data['connection_type'],
                data.get('label', '')
            )
        
        console.print(conn_table)
    
    console.print(f"\n[dim]💡 Use --json to get full graph data for React Flow or other visualization tools.[/dim]")


if __name__ == "__main__":
    app()