"""Interactive AI chat — the killer feature."""

from __future__ import annotations

import json as _json
import sys
import time
from typing import Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from ..api import api, APIError
from ..config import get_config_value, set_config_value
from ..utils.auth import ensure_authenticated
from ..utils.display import (
    ChatDisplay,
    format_cost,
    format_latency,
    format_tokens,
    get_output_format,
    print_error,
    print_info,
    print_success,
)

console = Console()
app = typer.Typer(help="💬 Interactive AI chat", invoke_without_command=True)


# ── cost helper ─────────────────────────────────────────────────

_COST_1K: Dict[str, float] = {
    "gpt-4": 0.03,
    "gpt-4o": 0.005,
    "gpt-4-turbo": 0.01,
    "gpt-3.5": 0.002,
    "claude-3-opus": 0.015,
    "claude-3-sonnet": 0.003,
    "claude-3-haiku": 0.00025,
    "claude-3.5": 0.003,
    "nova": 0.0008,
    "llama": 0.0007,
    "mistral": 0.0007,
}


def _estimate_cost(usage: Dict, model: str) -> float:
    tokens = usage.get("total_tokens", 0)
    rate = 0.001
    for prefix, cost in _COST_1K.items():
        if prefix in model.lower():
            rate = cost
            break
    return (tokens / 1000) * rate


# ── main callback (acts as the command itself) ──────────────────


@app.callback(invoke_without_command=True)
def chat(
    ctx: typer.Context,
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model UUID or name"),
    temperature: Optional[float] = typer.Option(None, "--temperature", "-t", help="Temperature (0-2)"),
    max_tokens: Optional[int] = typer.Option(None, "--max-tokens", help="Max output tokens"),
    compare: Optional[List[str]] = typer.Option(None, "--compare", help="Compare multiple models"),
    json_output: bool = typer.Option(False, "--json", help="JSON output (one-shot only)"),
    prompt: Optional[str] = typer.Argument(None, help="One-shot prompt (non-interactive)"),
):
    """
    Start an interactive AI chat or send a one-shot prompt.

    [bold]Examples:[/bold]

        bonito chat                           # interactive
        bonito chat -m gpt-4o "What is AI?"   # one-shot
        bonito chat --compare m1 --compare m2 "Compare these"
        echo "Summarize" | bonito chat        # pipe input
    """
    if ctx.invoked_subcommand is not None:
        return

    ensure_authenticated()

    # ── compare mode ────────────────────────────────────────────
    if compare:
        if len(compare) < 2:
            print_error("--compare needs at least 2 models")
            return
        if prompt:
            _compare_oneshot(compare, prompt, json_output)
        else:
            _compare_interactive(compare)
        return

    # ── piped stdin ─────────────────────────────────────────────
    if not sys.stdin.isatty():
        piped = sys.stdin.read().strip()
        if piped:
            prompt = f"{piped}\n\n{prompt}" if prompt else piped

    # ── resolve model ───────────────────────────────────────────
    if not model:
        model = get_config_value("default_model")
    if not model:
        try:
            models = api.get("/models/")
            if models:
                model = models[0]["id"]
            else:
                print_error("No models available. Enable one: [cyan]bonito models enable <id>[/cyan]")
                return
        except APIError:
            print_error("Could not fetch models. Specify one with -m")
            return

    settings: Dict[str, Any] = {}
    if temperature is not None:
        settings["temperature"] = temperature
    if max_tokens is not None:
        settings["max_tokens"] = max_tokens

    if prompt:
        _oneshot(model, prompt, settings, json_output)
    else:
        _interactive(model, settings)


# ── one-shot ────────────────────────────────────────────────────


def _oneshot(model: str, prompt: str, settings: Dict, json_flag: bool):
    fmt = get_output_format(json_flag)
    messages = [{"role": "user", "content": prompt}]
    t0 = time.time()

    try:
        with console.status("[cyan]Thinking…[/cyan]"):
            resp = api.post(f"/models/{model}/playground", {"messages": messages, **settings})

        # Support both Bonito playground format {"response": "..."} and
        # OpenAI format {"choices": [{"message": {"content": "..."}}]}
        content = resp.get("response") or (
            resp.get("choices", [{}])[0].get("message", {}).get("content", "")
        )
        usage = resp.get("usage", {})
        latency = resp.get("latency_ms", (time.time() - t0) * 1000) / 1000
        tokens = usage.get("total_tokens", len(content.split()))
        cost = resp.get("cost") or _estimate_cost(usage, model)

        if fmt == "json":
            console.print_json(_json.dumps(resp, default=str))
        else:
            console.print(f"\n[bold green]{model}:[/bold green]\n{content}")
            ChatDisplay.print_stats(tokens, cost, latency)

    except APIError as exc:
        print_error(f"Chat failed: {exc}")


# ── interactive ─────────────────────────────────────────────────


def _interactive(model: str, settings: Dict):
    messages: List[Dict[str, str]] = []
    total_cost = 0.0
    total_tokens = 0
    t_start = time.time()

    ChatDisplay.print_header(model, settings)
    ChatDisplay.print_help()
    console.print("[dim]Type a message or /quit to exit.[/dim]\n")

    try:
        while True:
            try:
                user_input = console.input("[bold blue]You:[/bold blue] ").strip()
            except (KeyboardInterrupt, EOFError):
                break

            if not user_input:
                continue

            # ── slash commands ───────────────────────────────────
            if user_input.startswith("/"):
                result = _handle_command(user_input, model, settings, messages, total_cost, total_tokens, t_start)
                if result == "quit":
                    break
                if result == "clear":
                    messages.clear()
                    total_cost = total_tokens = 0
                    t_start = time.time()
                    console.clear()
                    ChatDisplay.print_header(model, settings)
                    print_success("Conversation cleared")
                    continue
                if isinstance(result, dict):
                    model = result.get("model", model)
                    settings.update(result.get("settings", {}))
                    ChatDisplay.print_header(model, settings)
                continue

            # ── send message ────────────────────────────────────
            messages.append({"role": "user", "content": user_input})

            try:
                t0 = time.time()
                with console.status("[dim]Thinking…[/dim]"):
                    resp = api.post(f"/models/{model}/playground", {"messages": messages, **settings})

                content = resp.get("response") or (
                    resp.get("choices", [{}])[0].get("message", {}).get("content", "")
                )
                usage = resp.get("usage", {})
                latency = resp.get("latency_ms", (time.time() - t0) * 1000) / 1000
                tokens = usage.get("total_tokens", len(content.split()))
                cost = resp.get("cost") or _estimate_cost(usage, model)

                console.print(f"\n[bold green]{model}:[/bold green]\n{content}")
                ChatDisplay.print_stats(tokens, cost, latency)

                total_tokens += tokens
                total_cost += cost
                messages.append({"role": "assistant", "content": content})

            except APIError as exc:
                console.print(f"[red]✗ {exc}[/red]")
                if messages and messages[-1]["role"] == "user":
                    messages.pop()

    except KeyboardInterrupt:
        pass

    duration = time.time() - t_start
    console.print(
        f"\n[dim]Session: {duration:.0f}s · {len(messages)} messages · "
        f"{format_tokens(total_tokens)} tokens · {format_cost(total_cost)}[/dim]"
    )


# ── slash command handler ───────────────────────────────────────


def _handle_command(
    raw: str, model: str, settings: Dict, messages: List, cost: float, tokens: int, t0: float
) -> Any:
    parts = raw.split()
    cmd = parts[0].lower()

    if cmd in ("/quit", "/q", "/exit"):
        return "quit"

    if cmd == "/clear":
        return "clear"

    if cmd in ("/help", "/h"):
        ChatDisplay.print_help()
        return None

    if cmd == "/model":
        if len(parts) < 2:
            console.print("[yellow]Usage: /model <id>[/yellow]")
            return None
        console.print(f"[green]Switched → {parts[1]}[/green]")
        return {"model": parts[1]}

    if cmd in ("/temp", "/temperature"):
        if len(parts) < 2:
            console.print("[yellow]Usage: /temp <0–2>[/yellow]")
            return None
        try:
            t = float(parts[1])
            if 0 <= t <= 2:
                console.print(f"[green]Temperature → {t}[/green]")
                return {"settings": {"temperature": t}}
            console.print("[red]Must be 0–2[/red]")
        except ValueError:
            console.print("[red]Invalid number[/red]")
        return None

    if cmd in ("/tokens", "/maxtokens"):
        if len(parts) < 2:
            console.print("[yellow]Usage: /tokens <n>[/yellow]")
            return None
        try:
            n = int(parts[1])
            if n > 0:
                console.print(f"[green]Max tokens → {n}[/green]")
                return {"settings": {"max_tokens": n}}
        except ValueError:
            pass
        console.print("[red]Must be a positive integer[/red]")
        return None

    if cmd == "/stats":
        dur = time.time() - t0
        console.print(
            f"\n[bold]Session stats:[/bold]  {dur:.0f}s · {len(messages)} msgs · "
            f"{format_tokens(tokens)} tokens · {format_cost(cost)}"
        )
        return None

    if cmd == "/export":
        _export(messages, cost, tokens, t0)
        return None

    console.print(f"[red]Unknown: {cmd}[/red] — type [cyan]/help[/cyan]")
    return None


# ── export ──────────────────────────────────────────────────────


def _export(messages: List, cost: float, tokens: int, t0: float):
    if not messages:
        console.print("[yellow]Nothing to export[/yellow]")
        return
    ts = time.strftime("%Y%m%d_%H%M%S")
    fname = f"bonito_chat_{ts}.json"
    data = {
        "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_s": time.time() - t0,
        "total_cost": cost,
        "total_tokens": tokens,
        "messages": messages,
    }
    try:
        with open(fname, "w") as fh:
            _json.dump(data, fh, indent=2)
        print_success(f"Exported → {fname}")
    except Exception as exc:
        console.print(f"[red]Export failed: {exc}[/red]")


# ── compare mode ────────────────────────────────────────────────


def _compare_oneshot(models: List[str], prompt: str, json_flag: bool):
    fmt = get_output_format(json_flag)

    console.print(f"\n[bold cyan]🔄 Comparing {len(models)} models[/bold cyan]")
    console.print(f"[dim]{prompt[:80]}{'…' if len(prompt)>80 else ''}[/dim]\n")

    results = []
    for m in models:
        try:
            t0 = time.time()
            with console.status(f"[cyan]{m}…[/cyan]"):
                resp = api.post(f"/models/{m}/playground", {"messages": [{"role": "user", "content": prompt}]})
            latency = time.time() - t0
            content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = resp.get("usage", {})
            results.append({"model": m, "content": content, "tokens": usage.get("total_tokens", 0), "latency": latency})
        except APIError as exc:
            results.append({"model": m, "content": f"Error: {exc}", "error": True})

    if fmt == "json":
        console.print_json(_json.dumps(results, default=str))
    else:
        for i, r in enumerate(results, 1):
            border = "red" if r.get("error") else "green"
            stats = ""
            if not r.get("error"):
                stats = f"\n\n[dim]{format_tokens(r.get('tokens',0))} tokens · {format_latency(r.get('latency',0))}[/dim]"
            console.print(Panel(r["content"] + stats, title=f"{i}. {r['model']}", border_style=border))


def _compare_interactive(models: List[str]):
    console.print(f"\n[bold cyan]🔄 Compare: {', '.join(models)}[/bold cyan]")
    console.print("[dim]/quit to exit[/dim]\n")
    try:
        while True:
            try:
                prompt = console.input("[bold blue]Prompt:[/bold blue] ").strip()
            except (KeyboardInterrupt, EOFError):
                break
            if not prompt or prompt.lower() in ("/quit", "/q"):
                break
            _compare_oneshot(models, prompt, False)
            console.print()
    except KeyboardInterrupt:
        pass
    console.print("[dim]Compare session ended[/dim]")
