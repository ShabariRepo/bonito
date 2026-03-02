"""Deploy command — deploy a full Bonito stack from a bonito.yaml file.

Usage:
    bonito deploy -f bonito.yaml
    bonito deploy -f bonito.yaml --dry-run
    bonito deploy -f bonito.yaml --verbose
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..api import api, APIError
from ..utils.auth import ensure_authenticated
from ..utils.display import print_error, print_info, print_success, print_warning

console = Console()
app = typer.Typer(help="📦 Deploy from bonito.yaml")

# ── env-var interpolation ───────────────────────────────────────

_ENV_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _resolve_env(value: Any) -> Any:
    """Recursively resolve ``${ENV_VAR}`` placeholders in strings/dicts/lists."""
    if isinstance(value, str):
        def _sub(m: re.Match) -> str:
            name = m.group(1)
            env_val = os.environ.get(name)
            if env_val is None:
                return m.group(0)  # leave unresolved
            return env_val
        return _ENV_RE.sub(_sub, value)
    if isinstance(value, dict):
        return {k: _resolve_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env(v) for v in value]
    return value


def _find_unresolved(value: Any, path: str = "") -> List[str]:
    """Return a list of ``${VAR}`` references that could not be resolved."""
    unresolved: List[str] = []
    if isinstance(value, str):
        for m in _ENV_RE.finditer(value):
            if os.environ.get(m.group(1)) is None:
                unresolved.append(f"{path}: ${{{m.group(1)}}}")
    elif isinstance(value, dict):
        for k, v in value.items():
            unresolved.extend(_find_unresolved(v, f"{path}.{k}" if path else k))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            unresolved.extend(_find_unresolved(v, f"{path}[{i}]"))
    return unresolved


# ── YAML validation ─────────────────────────────────────────────

_REQUIRED_TOP_KEYS = {"version", "name"}
_KNOWN_TOP_KEYS = {"version", "name", "description", "gateway", "mcp_servers",
                    "knowledge_bases", "agents", "observability"}


def _validate(cfg: Dict[str, Any]) -> List[str]:
    """Return a list of validation error strings (empty = valid)."""
    errors: List[str] = []

    for key in _REQUIRED_TOP_KEYS:
        if key not in cfg:
            errors.append(f"Missing required top-level key: '{key}'")

    if "agents" in cfg and not isinstance(cfg["agents"], dict):
        errors.append("'agents' must be a mapping of agent-name → config")

    if "gateway" in cfg:
        gw = cfg["gateway"]
        if "providers" in gw and not isinstance(gw["providers"], list):
            errors.append("'gateway.providers' must be a list")

    if "mcp_servers" in cfg and not isinstance(cfg["mcp_servers"], dict):
        errors.append("'mcp_servers' must be a mapping of server-name → config")

    if "knowledge_bases" in cfg and not isinstance(cfg["knowledge_bases"], dict):
        errors.append("'knowledge_bases' must be a mapping of kb-name → config")

    # Validate each agent
    for agent_name, agent_cfg in (cfg.get("agents") or {}).items():
        if not isinstance(agent_cfg, dict):
            errors.append(f"agents.{agent_name}: must be a mapping")
            continue
        if "system_prompt" not in agent_cfg:
            errors.append(f"agents.{agent_name}: missing 'system_prompt'")
        if "model" not in agent_cfg:
            errors.append(f"agents.{agent_name}: missing 'model'")

    return errors


# ── deploy helpers ──────────────────────────────────────────────


class DeployResult:
    """Tracks what was created/updated/errored during a deploy."""

    def __init__(self) -> None:
        self.providers: List[Dict[str, str]] = []   # {"name": ..., "status": ok|error, "detail": ...}
        self.mcp_servers: List[Dict[str, str]] = []
        self.knowledge_bases: List[Dict[str, str]] = []
        self.agents: List[Dict[str, str]] = []

    @property
    def total(self) -> int:
        return len(self.providers) + len(self.mcp_servers) + len(self.knowledge_bases) + len(self.agents)

    @property
    def errors(self) -> int:
        return sum(
            1 for items in (self.providers, self.mcp_servers, self.knowledge_bases, self.agents)
            for item in items if item["status"] == "error"
        )

    @property
    def ok(self) -> int:
        return self.total - self.errors


def _read_system_prompt(prompt_ref: str, yaml_dir: Path) -> str:
    """Read a system prompt from a file path relative to the YAML file."""
    prompt_path = (yaml_dir / prompt_ref).resolve()
    if not prompt_path.exists():
        raise FileNotFoundError(f"System prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8").strip()


# ── step: providers ─────────────────────────────────────────────


def _deploy_providers(
    providers: List[Dict[str, Any]],
    result: DeployResult,
    dry_run: bool,
    verbose: bool,
) -> None:
    if not providers:
        return

    console.print("\n[bold cyan]☁️  Deploying providers…[/bold cyan]")

    for prov in providers:
        name = prov.get("name", "unnamed")
        try:
            if verbose:
                console.print(f"  [dim]→ {name} (priority={prov.get('priority', '—')})[/dim]")

            if dry_run:
                result.providers.append({"name": name, "status": "ok", "detail": "dry-run"})
                console.print(f"  [green]✓[/green] {name} [dim](dry-run)[/dim]")
                continue

            # Build payload matching the provider connect API
            payload: Dict[str, Any] = {
                "provider_type": name,
                "name": prov.get("display_name", name),
                "credentials": {},
            }

            # Map known credential fields
            if prov.get("api_key"):
                payload["credentials"]["api_key"] = prov["api_key"]
            if prov.get("region"):
                payload["credentials"]["region"] = prov["region"]
            if prov.get("access_key"):
                payload["credentials"]["access_key_id"] = prov["access_key"]
            if prov.get("secret_key"):
                payload["credentials"]["secret_access_key"] = prov["secret_key"]

            # Include models and priority as metadata
            if prov.get("models"):
                payload["models"] = prov["models"]
            if prov.get("priority") is not None:
                payload["priority"] = prov["priority"]

            with console.status(f"  [cyan]Connecting {name}…[/cyan]"):
                api.post("/providers/connect", payload)

            result.providers.append({"name": name, "status": "ok", "detail": "created"})
            console.print(f"  [green]✓[/green] {name}")

        except (APIError, Exception) as exc:
            result.providers.append({"name": name, "status": "error", "detail": str(exc)})
            console.print(f"  [red]✗[/red] {name}: {exc}")


# ── step: MCP servers ───────────────────────────────────────────


def _deploy_mcp_servers(
    servers: Dict[str, Dict[str, Any]],
    result: DeployResult,
    dry_run: bool,
    verbose: bool,
) -> None:
    if not servers:
        return

    console.print("\n[bold cyan]🔌 Deploying MCP servers…[/bold cyan]")

    for name, cfg in servers.items():
        try:
            if verbose:
                console.print(f"  [dim]→ {name} ({cfg.get('transport', '—')} @ {cfg.get('url', '—')})[/dim]")

            if dry_run:
                result.mcp_servers.append({"name": name, "status": "ok", "detail": "dry-run"})
                console.print(f"  [green]✓[/green] {name} [dim](dry-run)[/dim]")
                continue

            payload: Dict[str, Any] = {
                "name": name,
                "transport": cfg.get("transport", "sse"),
                "url": cfg.get("url"),
            }
            if cfg.get("auth"):
                payload["auth"] = cfg["auth"]
            if cfg.get("capabilities"):
                payload["capabilities"] = cfg["capabilities"]

            with console.status(f"  [cyan]Registering {name}…[/cyan]"):
                api.post("/mcp-servers", payload)

            result.mcp_servers.append({"name": name, "status": "ok", "detail": "created"})
            console.print(f"  [green]✓[/green] {name}")

        except (APIError, Exception) as exc:
            result.mcp_servers.append({"name": name, "status": "error", "detail": str(exc)})
            console.print(f"  [red]✗[/red] {name}: {exc}")


# ── step: knowledge bases ───────────────────────────────────────


def _deploy_knowledge_bases(
    kbs: Dict[str, Dict[str, Any]],
    result: DeployResult,
    dry_run: bool,
    verbose: bool,
    yaml_dir: Path,
) -> Dict[str, str]:
    """Deploy knowledge bases. Returns ``{kb_name: kb_id}`` map for agent linking."""
    kb_id_map: Dict[str, str] = {}
    if not kbs:
        return kb_id_map

    console.print("\n[bold cyan]📚 Deploying knowledge bases…[/bold cyan]")

    for name, cfg in kbs.items():
        try:
            if verbose:
                sources = cfg.get("sources", [])
                console.print(f"  [dim]→ {name} ({len(sources)} source(s))[/dim]")

            if dry_run:
                result.knowledge_bases.append({"name": name, "status": "ok", "detail": "dry-run"})
                console.print(f"  [green]✓[/green] {name} [dim](dry-run)[/dim]")
                continue

            # Create the knowledge base
            embedding = cfg.get("embedding", {})
            chunking = cfg.get("chunking", {})

            payload: Dict[str, Any] = {
                "name": name,
                "description": cfg.get("description"),
                "source_type": "upload",  # default — directory sources use upload
                "embedding_model": embedding.get("model", "auto"),
                "chunk_size": chunking.get("max_chunk_size", 512),
                "chunk_overlap": chunking.get("overlap", 50),
            }

            with console.status(f"  [cyan]Creating {name}…[/cyan]"):
                resp = api.post("/knowledge-bases", payload)

            kb_id = resp.get("id", "")
            kb_id_map[name] = kb_id

            # Upload directory sources
            sources = cfg.get("sources", [])
            uploaded = 0
            for source in sources:
                if source.get("type") == "directory":
                    src_path = (yaml_dir / source["path"]).resolve()
                    glob_pattern = source.get("glob", "**/*")
                    if src_path.is_dir():
                        for file_path in src_path.glob(glob_pattern):
                            if file_path.is_file():
                                try:
                                    _upload_file_to_kb(kb_id, file_path)
                                    uploaded += 1
                                except Exception as upload_exc:
                                    if verbose:
                                        console.print(f"    [dim red]⚠ Upload failed: {file_path.name}: {upload_exc}[/dim red]")
                    else:
                        if verbose:
                            console.print(f"    [dim yellow]⚠ Directory not found: {src_path}[/dim yellow]")

            detail = f"created (id={kb_id[:8]}…)"
            if uploaded:
                detail += f", {uploaded} file(s) uploaded"

            result.knowledge_bases.append({"name": name, "status": "ok", "detail": detail})
            console.print(f"  [green]✓[/green] {name} — {detail}")

        except (APIError, Exception) as exc:
            result.knowledge_bases.append({"name": name, "status": "error", "detail": str(exc)})
            console.print(f"  [red]✗[/red] {name}: {exc}")

    return kb_id_map


def _upload_file_to_kb(kb_id: str, file_path: Path) -> None:
    """Upload a single file to a knowledge base via multipart form."""
    import httpx
    from ..config import get_api_key
    from .. import __version__

    headers: Dict[str, str] = {"User-Agent": f"bonito-cli/{__version__}"}
    token = get_api_key()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    ext = file_path.suffix.lower().lstrip(".")
    mime_map = {
        "pdf": "application/pdf",
        "md": "text/markdown",
        "txt": "text/plain",
        "html": "text/html",
        "csv": "text/csv",
        "json": "application/json",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    mime = mime_map.get(ext, "application/octet-stream")

    with open(file_path, "rb") as fh:
        resp = httpx.post(
            f"{api.base_url}/api/knowledge-bases/{kb_id}/documents",
            files={"file": (file_path.name, fh, mime)},
            headers=headers,
            timeout=120.0,
        )
    if resp.status_code >= 400:
        raise APIError(f"HTTP {resp.status_code}: {resp.text[:200]}", resp.status_code)


# ── step: agents ────────────────────────────────────────────────


def _deploy_agents(
    agents: Dict[str, Dict[str, Any]],
    result: DeployResult,
    dry_run: bool,
    verbose: bool,
    yaml_dir: Path,
    kb_id_map: Dict[str, str],
) -> None:
    if not agents:
        return

    console.print("\n[bold cyan]🤖 Deploying agents…[/bold cyan]")

    # First pass: create all agents and collect IDs for delegation linking
    agent_id_map: Dict[str, str] = {}

    for name, cfg in agents.items():
        try:
            agent_type = cfg.get("type", "bonbon")
            display_name = cfg.get("display_name", name)

            if verbose:
                model = cfg.get("model", {})
                primary = model.get("primary", "auto") if isinstance(model, dict) else str(model)
                console.print(f"  [dim]→ {display_name} (type={agent_type}, model={primary})[/dim]")

            if dry_run:
                # Validate system prompt file exists
                prompt_ref = cfg.get("system_prompt", "")
                if prompt_ref:
                    prompt_path = (yaml_dir / prompt_ref).resolve()
                    if not prompt_path.exists():
                        result.agents.append({"name": name, "status": "error", "detail": f"system prompt not found: {prompt_ref}"})
                        console.print(f"  [red]✗[/red] {display_name}: system prompt not found: {prompt_ref}")
                        continue
                result.agents.append({"name": name, "status": "ok", "detail": "dry-run"})
                console.print(f"  [green]✓[/green] {display_name} [dim](dry-run)[/dim]")
                continue

            # Read system prompt
            prompt_ref = cfg.get("system_prompt", "")
            system_prompt = ""
            if prompt_ref:
                system_prompt = _read_system_prompt(prompt_ref, yaml_dir)

            # Build model ID
            model_cfg = cfg.get("model", {})
            if isinstance(model_cfg, dict):
                model_id = model_cfg.get("primary", "auto")
            else:
                model_id = str(model_cfg)

            params = cfg.get("parameters", {})

            # Build the create payload
            payload: Dict[str, Any] = {
                "name": name,
                "display_name": display_name,
                "description": cfg.get("description", ""),
                "agent_type": agent_type,
                "system_prompt": system_prompt,
                "model_id": model_id,
            }

            # Optional fields
            if model_cfg and isinstance(model_cfg, dict) and model_cfg.get("fallback"):
                payload["fallback_model_id"] = model_cfg["fallback"]
            if params.get("temperature") is not None:
                payload["temperature"] = params["temperature"]
            if params.get("max_tokens") is not None:
                payload["max_tokens"] = params["max_tokens"]
            if cfg.get("mode"):
                payload["mode"] = cfg["mode"]

            # MCP server references
            if cfg.get("mcp_servers"):
                payload["mcp_servers"] = cfg["mcp_servers"]

            # RAG / knowledge base linking
            rag = cfg.get("rag", {})
            if rag and rag.get("knowledge_base"):
                kb_name = rag["knowledge_base"]
                kb_id = kb_id_map.get(kb_name)
                if kb_id:
                    payload["knowledge_base_id"] = kb_id
                    if rag.get("top_k"):
                        payload["rag_top_k"] = rag["top_k"]
                    if rag.get("similarity_threshold"):
                        payload["rag_similarity_threshold"] = rag["similarity_threshold"]
                else:
                    if verbose:
                        console.print(f"    [dim yellow]⚠ KB '{kb_name}' not found in deploy — skipping RAG link[/dim yellow]")

            # Triggers
            if cfg.get("triggers"):
                payload["triggers"] = cfg["triggers"]

            # Delegates (for orchestrators)
            if cfg.get("delegates"):
                payload["delegates"] = cfg["delegates"]

            # Widget config
            if cfg.get("widget"):
                payload["widget"] = cfg["widget"]

            # Channels
            if cfg.get("channels"):
                payload["channels"] = cfg["channels"]

            with console.status(f"  [cyan]Creating {display_name}…[/cyan]"):
                resp = api.post("/agents", payload)

            agent_id = resp.get("id", "")
            agent_id_map[name] = agent_id

            result.agents.append({"name": name, "status": "ok", "detail": f"created (id={agent_id[:8]}…)"})
            console.print(f"  [green]✓[/green] {display_name} [dim](id={agent_id[:8]}…)[/dim]")

        except FileNotFoundError as exc:
            result.agents.append({"name": name, "status": "error", "detail": str(exc)})
            console.print(f"  [red]✗[/red] {cfg.get('display_name', name)}: {exc}")
        except (APIError, Exception) as exc:
            result.agents.append({"name": name, "status": "error", "detail": str(exc)})
            console.print(f"  [red]✗[/red] {cfg.get('display_name', name)}: {exc}")


# ── summary ─────────────────────────────────────────────────────


def _print_summary(result: DeployResult, stack_name: str, dry_run: bool) -> None:
    """Print a final deployment summary table."""
    console.print()

    table = Table(
        title=f"{'📋 Dry-run' if dry_run else '📦 Deploy'} Summary — {stack_name}",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
    )
    table.add_column("Resource", style="bold")
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("Detail", style="dim")

    _icon = {"providers": "☁️ ", "mcp_servers": "🔌", "knowledge_bases": "📚", "agents": "🤖"}

    for category, items in [
        ("providers", result.providers),
        ("mcp_servers", result.mcp_servers),
        ("knowledge_bases", result.knowledge_bases),
        ("agents", result.agents),
    ]:
        icon = _icon[category]
        for item in items:
            status_color = "green" if item["status"] == "ok" else "red"
            status_text = "✓" if item["status"] == "ok" else "✗"
            table.add_row(
                f"{icon} {category.replace('_', ' ').title()}",
                item["name"],
                f"[{status_color}]{status_text}[/{status_color}]",
                item.get("detail", ""),
            )

    console.print(table)

    if result.errors:
        console.print(f"\n[red bold]⚠  {result.errors} error(s) during deploy[/red bold]")
    else:
        emoji = "🎯" if dry_run else "🚀"
        verb = "validated" if dry_run else "deployed"
        console.print(f"\n[green bold]{emoji} {result.ok} resource(s) {verb} successfully[/green bold]")


# ── main command ────────────────────────────────────────────────


@app.callback(invoke_without_command=True)
def deploy(
    ctx: typer.Context,
    file: Path = typer.Option(
        ...,
        "--file", "-f",
        help="Path to bonito.yaml deployment file",
        exists=True,
        readable=True,
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate only — don't deploy"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
):
    """
    Deploy a full Bonito stack from a declarative YAML file.

    Reads bonito.yaml and creates/updates providers, MCP servers,
    knowledge bases, and agents in the correct order.

    \b
    Examples:
        bonito deploy -f bonito.yaml
        bonito deploy -f bonito.yaml --dry-run
        bonito deploy -f bonito.yaml --verbose
    """
    ensure_authenticated()

    yaml_path = file.resolve()
    yaml_dir = yaml_path.parent

    # ── 1. Parse YAML ──────────────────────────────────────────
    console.print(Panel(
        f"[bold]{yaml_path.name}[/bold]\n[dim]{yaml_path}[/dim]",
        title="📦 Bonito Deploy" + (" [yellow](dry-run)[/yellow]" if dry_run else ""),
        border_style="cyan",
    ))

    try:
        raw = yaml_path.read_text(encoding="utf-8")
        cfg = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        print_error(f"Invalid YAML: {exc}")
        return
    except Exception as exc:
        print_error(f"Failed to read {yaml_path}: {exc}")
        return

    if not isinstance(cfg, dict):
        print_error("YAML file must contain a mapping at the top level")
        return

    # ── 2. Resolve env vars ────────────────────────────────────
    cfg = _resolve_env(cfg)

    unresolved = _find_unresolved(cfg)
    if unresolved:
        console.print(f"\n[yellow]⚠  {len(unresolved)} unresolved environment variable(s):[/yellow]")
        for u in unresolved[:10]:
            console.print(f"  [dim]• {u}[/dim]")
        if len(unresolved) > 10:
            console.print(f"  [dim]… and {len(unresolved) - 10} more[/dim]")
        if not dry_run:
            print_warning("Deploying with unresolved variables may cause errors")

    # ── 3. Validate ────────────────────────────────────────────
    errors = _validate(cfg)
    if errors:
        console.print("\n[red bold]Validation errors:[/red bold]")
        for err in errors:
            console.print(f"  [red]• {err}[/red]")
        print_error(f"{len(errors)} validation error(s) — fix your YAML and retry")
        return

    stack_name = cfg.get("name", "unnamed")
    if verbose:
        console.print(f"\n[dim]Stack: {stack_name} (version {cfg.get('version', '?')})[/dim]")
        desc = cfg.get("description")
        if desc:
            console.print(f"[dim]{desc}[/dim]")

    result = DeployResult()

    # ── 4. Providers ───────────────────────────────────────────
    gateway = cfg.get("gateway", {})
    providers = gateway.get("providers", [])
    _deploy_providers(providers, result, dry_run, verbose)

    # ── 5. MCP Servers ─────────────────────────────────────────
    mcp_servers = cfg.get("mcp_servers", {})
    _deploy_mcp_servers(mcp_servers, result, dry_run, verbose)

    # ── 6. Knowledge Bases ─────────────────────────────────────
    kbs = cfg.get("knowledge_bases", {})
    kb_id_map = _deploy_knowledge_bases(kbs, result, dry_run, verbose, yaml_dir)

    # ── 7. Agents ──────────────────────────────────────────────
    agents = cfg.get("agents", {})
    _deploy_agents(agents, result, dry_run, verbose, yaml_dir, kb_id_map)

    # ── 8. Summary ─────────────────────────────────────────────
    _print_summary(result, stack_name, dry_run)

    if result.errors:
        raise typer.Exit(1)
