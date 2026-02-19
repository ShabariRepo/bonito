"""Bonobot Agents CLI commands.

Manage AI agents: create, list, update, delete, execute, and manage sessions.
"""

import json
from typing import Optional, List

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
app = typer.Typer(help="🤖 Bonobot Agents — AI agent management")


@app.command("list")
def list_agents(
    project_id: Optional[str] = typer.Option(None, "--project", "-p", help="Project ID to filter agents"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """List agents in a project or all projects."""
    ensure_authenticated()
    fmt = get_output_format(json_output)
    
    if not project_id:
        # If no project specified, get user to choose from available projects
        try:
            projects_resp = api.get("/projects")
        except APIError as e:
            print_error(f"Failed to fetch projects: {e}")
            return
            
        if not projects_resp:
            print_error("No projects found. Create a project first with 'bonito projects create'.")
            return
        
        if len(projects_resp) == 1:
            project_id = projects_resp[0]["id"]
        else:
            console.print("\n[bold]Available Projects:[/bold]")
            for i, project in enumerate(projects_resp, 1):
                console.print(f"{i}. {project['name']} ({project['id']})")
            
            choice = Prompt.ask("\nSelect project", choices=[str(i) for i in range(1, len(projects_resp) + 1)])
            project_id = projects_resp[int(choice) - 1]["id"]
    
    try:
        with console.status("[cyan]Fetching agents…[/cyan]"):
            response = api.get(f"/projects/{project_id}/agents")
    except APIError as e:
        print_error(f"Failed to fetch agents: {e}")
        return
    
    if fmt == "json":
        console.print_json(json.dumps(response, default=str))
        return
    
    if not response:
        print_info("No agents found in this project.")
        return
    
    table = Table(title=f"Agents in Project")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Model", style="blue")
    table.add_column("Runs", justify="right")
    table.add_column("Cost", justify="right")
    table.add_column("Last Active", style="dim")
    
    for agent in response:
        table.add_row(
            agent["name"],
            format_status(agent["status"]),
            agent["model_id"],
            str(agent["total_runs"]),
            format_cost(agent["total_cost"]),
            format_timestamp(agent.get("last_active_at"))
        )
    
    console.print(table)


@app.command("create")
def create_agent(
    project_id: str = typer.Option(..., "--project", "-p", help="Project ID"),
    name: str = typer.Option(..., "--name", "-n", help="Agent name"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Agent description"),
    system_prompt: Optional[str] = typer.Option(None, "--prompt", help="System prompt (or use --prompt-file)"),
    prompt_file: Optional[str] = typer.Option(None, "--prompt-file", help="File containing system prompt"),
    model: str = typer.Option("auto", "--model", "-m", help="Model ID to use"),
    max_turns: int = typer.Option(25, "--max-turns", help="Maximum conversation turns"),
    timeout: int = typer.Option(300, "--timeout", help="Timeout in seconds"),
    rate_limit: int = typer.Option(30, "--rate-limit", help="Rate limit (requests per minute)"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """Create a new agent."""
    ensure_authenticated()
    fmt = get_output_format(json_output)
    
    # Get system prompt
    if prompt_file:
        try:
            with open(prompt_file, 'r') as f:
                system_prompt = f.read().strip()
        except FileNotFoundError:
            print_error(f"Prompt file not found: {prompt_file}")
            return
    elif not system_prompt:
        console.print("Enter the system prompt (end with Ctrl+D):")
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            system_prompt = '\n'.join(lines).strip()
    
    if not system_prompt:
        print_error("System prompt is required")
        return
    
    payload = {
        "name": name,
        "description": description,
        "system_prompt": system_prompt,
        "model_id": model,
        "max_turns": max_turns,
        "timeout_seconds": timeout,
        "rate_limit_rpm": rate_limit,
    }
    
    try:
        response = api.post(f"/projects/{project_id}/agents", data=payload)
    except APIError as e:
        print_error(f"Failed to create agent: {e}")
        return
    
    if fmt == "json":
        console.print_json(json.dumps(response, default=str))
        return
    
    print_success(f"Agent '{name}' created successfully!")
    console.print(f"Agent ID: [cyan]{response['id']}[/cyan]")


@app.command("info")
def agent_info(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    include_sessions: bool = typer.Option(False, "--sessions", help="Include recent sessions"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """Get detailed information about an agent."""
    ensure_authenticated()
    fmt = get_output_format(json_output)
    
    params = {"include_sessions": include_sessions}
    
    try:
        response = api.get(f"/agents/{agent_id}", params=params)
    except APIError as e:
        print_error(f"Failed to fetch agent info: {e}")
        return
    
    if fmt == "json":
        console.print_json(json.dumps(response, default=str))
        return
    
    # Agent details
    agent = response
    
    # Main info panel
    info_text = f"""[bold cyan]Name:[/bold cyan] {agent['name']}
[bold cyan]Status:[/bold cyan] {format_status(agent['status'])}
[bold cyan]Model:[/bold cyan] {agent['model_id']}
[bold cyan]Total Runs:[/bold cyan] {agent['total_runs']}
[bold cyan]Total Cost:[/bold cyan] {format_cost(agent['total_cost'])}
[bold cyan]Rate Limit:[/bold cyan] {agent['rate_limit_rpm']} RPM
[bold cyan]Max Turns:[/bold cyan] {agent['max_turns']}
[bold cyan]Timeout:[/bold cyan] {agent['timeout_seconds']}s"""
    
    if agent.get("description"):
        info_text = f"[bold cyan]Description:[/bold cyan] {agent['description']}\n" + info_text
    
    console.print(Panel(info_text, title="Agent Details"))
    
    # System prompt
    console.print(Panel(agent['system_prompt'], title="System Prompt", border_style="blue"))
    
    # Knowledge bases
    if agent.get('knowledge_bases'):
        kb_table = Table(title="Knowledge Bases")
        kb_table.add_column("Name")
        kb_table.add_column("ID", style="dim")
        for kb in agent['knowledge_bases']:
            kb_table.add_row(kb['name'], kb['id'])
        console.print(kb_table)
    
    # Recent sessions
    if include_sessions and agent.get('recent_sessions'):
        sessions_table = Table(title="Recent Sessions")
        sessions_table.add_column("Session ID", style="dim")
        sessions_table.add_column("Title")
        sessions_table.add_column("Messages", justify="right")
        sessions_table.add_column("Cost", justify="right")
        sessions_table.add_column("Last Message", style="dim")
        
        for session in agent['recent_sessions']:
            sessions_table.add_row(
                str(session['id'])[:8] + "...",
                session.get('title', 'Untitled'),
                str(session['message_count']),
                format_cost(session['total_cost']),
                format_timestamp(session.get('last_message_at'))
            )
        console.print(sessions_table)


@app.command("update")
def update_agent(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Update agent name"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Update description"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Update model ID"),
    max_turns: Optional[int] = typer.Option(None, "--max-turns", help="Update max turns"),
    timeout: Optional[int] = typer.Option(None, "--timeout", help="Update timeout seconds"),
    rate_limit: Optional[int] = typer.Option(None, "--rate-limit", help="Update rate limit RPM"),
    status: Optional[str] = typer.Option(None, "--status", help="Update status (active/paused/disabled)"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """Update agent configuration."""
    ensure_authenticated()
    fmt = get_output_format(json_output)
    
    payload = {}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if model is not None:
        payload["model_id"] = model
    if max_turns is not None:
        payload["max_turns"] = max_turns
    if timeout is not None:
        payload["timeout_seconds"] = timeout
    if rate_limit is not None:
        payload["rate_limit_rpm"] = rate_limit
    if status is not None:
        payload["status"] = status
    
    if not payload:
        print_error("No updates specified")
        return
    
    try:
        response = api.put(f"/agents/{agent_id}", data=payload)
    except APIError as e:
        print_error(f"Failed to update agent: {e}")
        return
    
    if fmt == "json":
        console.print_json(json.dumps(response, default=str))
        return
    
    print_success("Agent updated successfully!")


@app.command("delete")
def delete_agent(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete (disable) an agent."""
    ensure_authenticated()
    
    if not force:
        # Get agent info first
        try:
            agent = api.get(f"/agents/{agent_id}")
        except APIError as e:
            print_error(f"Failed to fetch agent info: {e}")
            return
        
        confirmed = Confirm.ask(f"Are you sure you want to delete agent '{agent['name']}'?")
        if not confirmed:
            console.print("Cancelled.")
            return
    
    try:
        api.delete(f"/agents/{agent_id}")
    except APIError as e:
        print_error(f"Failed to delete agent: {e}")
        return
    
    print_success("Agent deleted (disabled) successfully!")


@app.command("execute")
def execute_agent(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    message: Optional[str] = typer.Argument(None, help="Message to send"),
    session_id: Optional[str] = typer.Option(None, "--session", "-s", help="Session ID (creates new if not provided)"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """Execute an agent with a message."""
    ensure_authenticated()
    fmt = get_output_format(json_output)
    
    # Get message if not provided
    if not message:
        message = Prompt.ask("Enter your message")
    
    payload = {"message": message}
    if session_id:
        payload["session_id"] = session_id
    
    try:
        with console.status(f"[bold green]Executing agent...", spinner="dots"):
            response = api.post(f"/agents/{agent_id}/execute", data=payload)
    except APIError as e:
        print_error(f"Failed to execute agent: {e}")
        return
    
    if fmt == "json":
        console.print_json(json.dumps(response, default=str))
        return
    
    # Display response
    console.print(Panel(
        response.get('content', 'No content returned'),
        title=f"Agent Response",
        border_style="green"
    ))
    
    # Execution stats
    stats_text = f"""[bold]Run ID:[/bold] {response['run_id']}
[bold]Session ID:[/bold] {response['session_id']}
[bold]Model Used:[/bold] {response.get('model_used', 'Unknown')}
[bold]Tokens:[/bold] {response['tokens']}
[bold]Cost:[/bold] {format_cost(response['cost'])}
[bold]Turns:[/bold] {response['turns']}"""
    
    console.print(Panel(stats_text, title="Execution Stats", border_style="blue"))


@app.command("sessions")
def list_sessions(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum number of sessions to show"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """List sessions for an agent."""
    ensure_authenticated()
    fmt = get_output_format(json_output)
    
    params = {"limit": limit}
    
    try:
        response = api.get(f"/agents/{agent_id}/sessions", params=params)
    except APIError as e:
        print_error(f"Failed to fetch sessions: {e}")
        return
    
    if fmt == "json":
        console.print_json(json.dumps(response, default=str))
        return
    
    if not response:
        print_info("No sessions found for this agent.")
        return
    
    table = Table(title=f"Agent Sessions")
    table.add_column("Session ID", style="dim")
    table.add_column("Title")
    table.add_column("Status", style="green")
    table.add_column("Messages", justify="right")
    table.add_column("Tokens", justify="right")
    table.add_column("Cost", justify="right")
    table.add_column("Last Message", style="dim")
    
    for session in response:
        table.add_row(
            str(session['id'])[:8] + "...",
            session.get('title', 'Untitled'),
            format_status(session['status']),
            str(session['message_count']),
            str(session['total_tokens']),
            format_cost(session['total_cost']),
            format_timestamp(session.get('last_message_at'))
        )
    
    console.print(table)


@app.command("messages")
def session_messages(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    session_id: str = typer.Argument(..., help="Session ID"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """Show messages in a session."""
    ensure_authenticated()
    fmt = get_output_format(json_output)
    
    try:
        response = api.get(f"/agents/{agent_id}/sessions/{session_id}/messages")
    except APIError as e:
        print_error(f"Failed to fetch messages: {e}")
        return
    
    if fmt == "json":
        console.print_json(json.dumps(response, default=str))
        return
    
    if not response:
        print_info("No messages found in this session.")
        return
    
    for i, message in enumerate(response, 1):
        role_color = "blue" if message['role'] == 'user' else "green"
        role_icon = "👤" if message['role'] == 'user' else "🤖"
        
        header = f"{role_icon} {message['role'].title()}"
        if message.get('model_used'):
            header += f" ({message['model_used']})"
        
        content = message.get('content', '')
        if message.get('tool_calls'):
            content += f"\n\n[dim]Tool calls: {json.dumps(message['tool_calls'], indent=2)}[/dim]"
        
        panel = Panel(
            content,
            title=header,
            border_style=role_color,
            title_align="left"
        )
        
        console.print(panel)
        
        # Show token/cost info for assistant messages
        if message['role'] == 'assistant' and (message.get('input_tokens') or message.get('cost')):
            stats = []
            if message.get('input_tokens'):
                stats.append(f"In: {message['input_tokens']} tokens")
            if message.get('output_tokens'):
                stats.append(f"Out: {message['output_tokens']} tokens")
            if message.get('cost'):
                stats.append(f"Cost: {format_cost(message['cost'])}")
            if message.get('latency_ms'):
                stats.append(f"Latency: {message['latency_ms']}ms")
            
            if stats:
                console.print(f"  [dim]{' • '.join(stats)}[/dim]\n")


@app.command("connections")
def list_connections(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """List connections from this agent to other agents."""
    ensure_authenticated()
    fmt = get_output_format(json_output)
    
    try:
        response = api.get(f"/agents/{agent_id}/connections")
    except APIError as e:
        print_error(f"Failed to fetch connections: {e}")
        return
    
    if fmt == "json":
        console.print_json(json.dumps(response, default=str))
        return
    
    if not response:
        print_info("No connections found for this agent.")
        return
    
    table = Table(title="Agent Connections")
    table.add_column("Target Agent", style="cyan")
    table.add_column("Type", style="blue")
    table.add_column("Label")
    table.add_column("Enabled", style="green")
    
    for conn in response:
        table.add_row(
            conn.get('target_agent_name', 'Unknown'),
            conn['connection_type'],
            conn.get('label', ''),
            "✅" if conn['enabled'] else "❌"
        )
    
    console.print(table)


@app.command("triggers")
def list_triggers(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """List triggers for this agent."""
    ensure_authenticated()
    fmt = get_output_format(json_output)
    
    try:
        response = api.get(f"/agents/{agent_id}/triggers")
    except APIError as e:
        print_error(f"Failed to fetch triggers: {e}")
        return
    
    if fmt == "json":
        console.print_json(json.dumps(response, default=str))
        return
    
    if not response:
        print_info("No triggers found for this agent.")
        return
    
    table = Table(title="Agent Triggers")
    table.add_column("Type", style="blue")
    table.add_column("Config")
    table.add_column("Enabled", style="green")
    table.add_column("Last Fired", style="dim")
    
    for trigger in response:
        config_str = json.dumps(trigger.get('config', {}), separators=(',', ':'))[:50]
        if len(config_str) == 50:
            config_str += "..."
        
        table.add_row(
            trigger['trigger_type'],
            config_str,
            "✅" if trigger['enabled'] else "❌",
            format_timestamp(trigger.get('last_fired_at'))
        )
    
    console.print(table)


if __name__ == "__main__":
    app()