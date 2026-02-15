"""Interactive AI chat commands - THE KILLER FEATURE."""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
import typer
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt

from ..api import api, APIError
from ..config import get_config_value, set_config_value
from ..utils.display import (
    print_error, print_success, print_info, print_warning,
    get_output_format, format_cost, format_tokens, format_latency,
    ChatDisplay
)
from ..utils.auth import ensure_authenticated

console = Console()

app = typer.Typer(help="💬 Interactive AI chat", invoke_without_command=True)


@app.callback()
def main(
    ctx: typer.Context,
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model to use for chat"),
    temperature: Optional[float] = typer.Option(None, "--temperature", help="Temperature (0-2)", min=0, max=2),
    max_tokens: Optional[int] = typer.Option(None, "--max-tokens", help="Maximum tokens to generate"),
    compare: List[str] = typer.Option(None, "--compare", help="Compare multiple models"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    prompt: Optional[str] = typer.Argument(None, help="One-shot prompt (non-interactive)")
):
    """
    Interactive AI chat with streaming responses.
    
    Examples:
        bonito chat                              # Interactive mode
        bonito chat -m claude-3-sonnet           # With specific model
        bonito chat -m gpt-4o "What is AI?"     # One-shot mode
        bonito chat --compare model1 model2     # Compare mode
        echo "Summarize this" | bonito chat     # Pipe input
    """
    ensure_authenticated()
    
    # Handle compare mode
    if compare:
        if len(compare) < 2:
            print_error("Compare mode requires at least 2 models")
            return
        
        # If prompt is provided, do one-shot compare
        if prompt:
            run_compare_mode(compare, prompt, json_output)
        else:
            # Interactive compare mode
            run_interactive_compare(compare, json_output)
        return
    
    # Handle piped input
    if not sys.stdin.isatty():
        piped_input = sys.stdin.read().strip()
        if piped_input and prompt:
            prompt = f"{piped_input}\n\n{prompt}"
        elif piped_input:
            prompt = piped_input
    
    # Determine model
    if not model:
        model = get_config_value("default_model")
        if not model:
            # Try to get first available model
            try:
                models = api.list_models(enabled_only=True)
                if models:
                    model = models[0]["id"]
                else:
                    print_error("No enabled models found. Enable a model first with: bonito models enable MODEL_ID")
                    return
            except APIError:
                print_error("Could not fetch models. Please specify a model with -m")
                return
    
    # Build chat settings
    settings = {}
    if temperature is not None:
        settings["temperature"] = temperature
    if max_tokens is not None:
        settings["max_tokens"] = max_tokens
    
    # One-shot mode
    if prompt:
        run_oneshot_chat(model, prompt, settings, json_output)
    else:
        # Interactive mode
        run_interactive_chat(model, settings, json_output)


def run_oneshot_chat(model: str, prompt: str, settings: Dict, json_output: bool):
    """Run one-shot chat completion."""
    output_format = get_output_format(json_output)
    
    try:
        messages = [{"role": "user", "content": prompt}]
        
        start_time = time.time()
        
        if output_format == "json":
            response = api.chat_completion(model, messages, **settings)
            console.print_json(response)
        else:
            with console.status(f"[bold green]Thinking..."):
                response = api.chat_completion(model, messages, **settings)
            
            # Extract response content
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = response.get("usage", {})
            
            # Calculate metrics
            latency = time.time() - start_time
            tokens = usage.get("total_tokens", 0)
            cost = calculate_cost(usage, model)
            
            # Display response
            console.print(f"\n[bold green]{model}:[/bold green] {content}")
            
            # Show stats
            ChatDisplay.print_stats(tokens, cost, latency)
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Chat failed: {e}")


def run_interactive_chat(model: str, settings: Dict, json_output: bool):
    """Run interactive chat session."""
    if json_output:
        print_error("Interactive mode not supported with --json flag")
        return
    
    # Initialize chat session
    messages = []
    total_cost = 0.0
    total_tokens = 0
    session_start = time.time()
    
    # Show header
    ChatDisplay.print_header(model, settings)
    ChatDisplay.print_help()
    
    console.print(f"\n[dim]Type your message or use /commands. Type /quit to exit.[/dim]")
    
    try:
        while True:
            # Get user input
            try:
                user_input = console.input("\n[bold blue]You:[/bold blue] ").strip()
            except (KeyboardInterrupt, EOFError):
                break
            
            if not user_input:
                continue
            
            # Handle chat commands
            if user_input.startswith('/'):
                command_result = handle_chat_command(
                    user_input, model, settings, messages, 
                    total_cost, total_tokens, session_start
                )
                
                if command_result == "quit":
                    break
                elif command_result == "clear":
                    messages = []
                    total_cost = 0.0
                    total_tokens = 0
                    session_start = time.time()
                    console.clear()
                    ChatDisplay.print_header(model, settings)
                    console.print("[green]Conversation cleared[/green]")
                elif isinstance(command_result, dict):
                    # Model or settings changed
                    model = command_result.get("model", model)
                    settings.update(command_result.get("settings", {}))
                    ChatDisplay.print_header(model, settings)
                
                continue
            
            # Add user message
            messages.append({"role": "user", "content": user_input})
            
            # Get AI response
            try:
                start_time = time.time()
                
                # Try to stream if possible
                response_content = ""
                try:
                    response_content = stream_response(model, messages, settings)
                except:
                    # Fallback to non-streaming
                    with console.status("[bold green]Thinking..."):
                        response = api.chat_completion(model, messages, **settings)
                    
                    response_content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
                    console.print(f"\n[bold green]{model}:[/bold green] {response_content}")
                
                # Calculate metrics (estimated for streaming)
                latency = time.time() - start_time
                tokens = len(response_content.split()) * 1.3  # Rough estimate
                cost = calculate_cost({"total_tokens": int(tokens)}, model)
                
                # Update totals
                total_tokens += int(tokens)
                total_cost += cost
                
                # Show stats
                ChatDisplay.print_stats(int(tokens), cost, latency)
                
                # Add assistant message to conversation
                messages.append({"role": "assistant", "content": response_content})
            
            except APIError as e:
                print_error(f"Error: {e}")
                # Remove the user message that caused the error
                if messages and messages[-1]["role"] == "user":
                    messages.pop()
    
    except KeyboardInterrupt:
        pass
    
    # Show session summary
    session_duration = time.time() - session_start
    console.print(f"\n[dim]Session ended. Duration: {session_duration:.1f}s | Messages: {len(messages)} | Total cost: {format_cost(total_cost)} | Total tokens: {format_tokens(total_tokens)}[/dim]")


def stream_response(model: str, messages: List[Dict], settings: Dict) -> str:
    """Stream response from model (if supported)."""
    response_content = ""
    
    try:
        # This would use the async streaming API
        async def stream_chat():
            content = ""
            console.print(f"\n[bold green]{model}:[/bold green] ", end="")
            
            async for chunk in api.stream_chat_completion(model, messages, **settings):
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                if "content" in delta:
                    content += delta["content"]
                    console.print(delta["content"], end="")
            
            console.print()  # New line
            return content
        
        # Run async streaming
        response_content = asyncio.run(stream_chat())
        
    except Exception:
        # Fallback to regular response if streaming fails
        raise
    
    return response_content


def handle_chat_command(
    command: str, current_model: str, current_settings: Dict,
    messages: List[Dict], total_cost: float, total_tokens: int, session_start: float
) -> Any:
    """Handle in-chat commands."""
    parts = command.split()
    cmd = parts[0].lower()
    
    if cmd == "/quit" or cmd == "/q":
        return "quit"
    
    elif cmd == "/clear":
        return "clear"
    
    elif cmd == "/help" or cmd == "/h":
        ChatDisplay.print_help()
        return None
    
    elif cmd == "/model":
        if len(parts) < 2:
            console.print("[yellow]Usage: /model MODEL_ID[/yellow]")
            return None
        
        new_model = parts[1]
        console.print(f"[green]Switched to model: {new_model}[/green]")
        return {"model": new_model}
    
    elif cmd == "/temp" or cmd == "/temperature":
        if len(parts) < 2:
            console.print("[yellow]Usage: /temp VALUE (0-2)[/yellow]")
            return None
        
        try:
            temp = float(parts[1])
            if 0 <= temp <= 2:
                console.print(f"[green]Temperature set to: {temp}[/green]")
                return {"settings": {"temperature": temp}}
            else:
                console.print("[red]Temperature must be between 0 and 2[/red]")
        except ValueError:
            console.print("[red]Invalid temperature value[/red]")
        
        return None
    
    elif cmd == "/tokens" or cmd == "/maxtokens":
        if len(parts) < 2:
            console.print("[yellow]Usage: /tokens VALUE[/yellow]")
            return None
        
        try:
            max_tokens = int(parts[1])
            if max_tokens > 0:
                console.print(f"[green]Max tokens set to: {max_tokens}[/green]")
                return {"settings": {"max_tokens": max_tokens}}
            else:
                console.print("[red]Max tokens must be positive[/red]")
        except ValueError:
            console.print("[red]Invalid max tokens value[/red]")
        
        return None
    
    elif cmd == "/export":
        return export_conversation(messages, total_cost, total_tokens, session_start)
    
    elif cmd == "/stats":
        # Show session stats
        session_duration = time.time() - session_start
        console.print(f"\n[bold]Session Statistics:[/bold]")
        console.print(f"Duration: {session_duration:.1f}s")
        console.print(f"Messages: {len(messages)}")
        console.print(f"Total cost: {format_cost(total_cost)}")
        console.print(f"Total tokens: {format_tokens(total_tokens)}")
        return None
    
    else:
        console.print(f"[red]Unknown command: {cmd}[/red]")
        console.print("[yellow]Type /help for available commands[/yellow]")
        return None


def export_conversation(
    messages: List[Dict], total_cost: float, 
    total_tokens: int, session_start: float
) -> None:
    """Export conversation to file."""
    if not messages:
        console.print("[yellow]No conversation to export[/yellow]")
        return
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"bonito_chat_{timestamp}.json"
    
    export_data = {
        "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "session_duration": time.time() - session_start,
        "total_cost": total_cost,
        "total_tokens": total_tokens,
        "message_count": len(messages),
        "messages": messages
    }
    
    try:
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        console.print(f"[green]Conversation exported to: {filename}[/green]")
    except Exception as e:
        console.print(f"[red]Export failed: {e}[/red]")
    
    return None


def run_compare_mode(models: List[str], prompt: str, json_output: bool):
    """Run comparison mode with multiple models."""
    output_format = get_output_format(json_output)
    
    try:
        if output_format == "json":
            result = api.compare_models(models, prompt)
            console.print_json(result)
        else:
            console.print(f"\n[bold cyan]🔄 Comparing {len(models)} models[/bold cyan]")
            console.print(f"[dim]Prompt: {prompt}[/dim]\n")
            
            # Get responses from each model
            responses = []
            for model in models:
                try:
                    with console.status(f"[bold green]Getting response from {model}..."):
                        start_time = time.time()
                        response = api.chat_completion(model, [{"role": "user", "content": prompt}])
                        latency = time.time() - start_time
                    
                    content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
                    usage = response.get("usage", {})
                    tokens = usage.get("total_tokens", 0)
                    cost = calculate_cost(usage, model)
                    
                    responses.append({
                        "model": model,
                        "content": content,
                        "tokens": tokens,
                        "cost": cost,
                        "latency": latency
                    })
                
                except APIError as e:
                    responses.append({
                        "model": model,
                        "content": f"Error: {e}",
                        "tokens": 0,
                        "cost": 0,
                        "latency": 0,
                        "error": True
                    })
            
            # Display responses
            for i, resp in enumerate(responses, 1):
                if resp.get("error"):
                    console.print(Panel(
                        resp["content"],
                        title=f"{i}. [red]{resp['model']} (Error)[/red]",
                        border_style="red"
                    ))
                else:
                    stats = f"tokens: {format_tokens(resp['tokens'])} | cost: {format_cost(resp['cost'])} | latency: {format_latency(resp['latency'])}"
                    console.print(Panel(
                        resp["content"] + f"\n\n[dim]{stats}[/dim]",
                        title=f"{i}. [green]{resp['model']}[/green]",
                        border_style="green"
                    ))
                console.print()
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Comparison failed: {e}")


def run_interactive_compare(models: List[str], json_output: bool):
    """Run interactive comparison mode."""
    if json_output:
        print_error("Interactive compare mode not supported with --json flag")
        return
    
    console.print(f"\n[bold cyan]🔄 Interactive Compare Mode[/bold cyan]")
    console.print(f"[dim]Comparing: {', '.join(models)}[/dim]")
    console.print(f"[dim]Type your prompts or /quit to exit[/dim]\n")
    
    try:
        while True:
            try:
                prompt = console.input("[bold blue]Compare prompt:[/bold blue] ").strip()
            except (KeyboardInterrupt, EOFError):
                break
            
            if not prompt:
                continue
            
            if prompt.lower() in ["/quit", "/q", "/exit"]:
                break
            
            # Run comparison
            run_compare_mode(models, prompt, False)
            console.print("\n" + "="*60 + "\n")
    
    except KeyboardInterrupt:
        pass
    
    console.print("\n[dim]Compare session ended[/dim]")


def calculate_cost(usage: Dict, model: str) -> float:
    """Calculate approximate cost based on usage."""
    # This is a rough estimation - real costs would come from the API
    total_tokens = usage.get("total_tokens", 0)
    
    # Rough cost estimates (per 1K tokens)
    cost_per_1k = {
        "gpt-4": 0.03,
        "gpt-4-turbo": 0.01,
        "gpt-3.5-turbo": 0.002,
        "claude-3-opus": 0.015,
        "claude-3-sonnet": 0.003,
        "claude-3-haiku": 0.00025,
    }
    
    # Find matching cost
    rate = 0.001  # Default fallback
    for model_prefix, cost in cost_per_1k.items():
        if model_prefix in model.lower():
            rate = cost
            break
    
    return (total_tokens / 1000) * rate


if __name__ == "__main__":
    app()