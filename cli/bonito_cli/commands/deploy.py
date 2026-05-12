"""Deploy command - deploy a full Bonito stack from a bonito.yaml file.

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
app = typer.Typer(help="Deploy from bonito.yaml")

# -- env-var interpolation ---------------------------------------------------

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


# -- YAML validation ---------------------------------------------------------

_REQUIRED_TOP_KEYS = {"version", "name"}
_KNOWN_TOP_KEYS = {"version", "name", "description", "gateway", "mcp_servers",
                    "knowledge_bases", "agents", "observability", "secrets"}


def _validate(cfg: Dict[str, Any]) -> List[str]:
    """Return a list of validation error strings (empty = valid)."""
    errors: List[str] = []

    for key in _REQUIRED_TOP_KEYS:
        if key not in cfg:
            errors.append(f"Missing required top-level key: '{key}'")

    if "agents" in cfg and not isinstance(cfg["agents"], dict):
        errors.append("'agents' must be a mapping of agent-name -> config")

    if "gateway" in cfg:
        gw = cfg["gateway"]
        if "providers" in gw and not isinstance(gw["providers"], list):
            errors.append("'gateway.providers' must be a list")

    if "mcp_servers" in cfg and not isinstance(cfg["mcp_servers"], dict):
        errors.append("'mcp_servers' must be a mapping of server-name -> config")

    if "knowledge_bases" in cfg and not isinstance(cfg["knowledge_bases"], dict):
        errors.append("'knowledge_bases' must be a mapping of kb-name -> config")

    # Validate each agent
    for agent_name, agent_cfg in (cfg.get("agents") or {}).items():
        if not isinstance(agent_cfg, dict):
            errors.append(f"agents.{agent_name}: must be a mapping")
            continue
        if "system_prompt" not in agent_cfg:
            errors.append(f"agents.{agent_name}: missing 'system_prompt'")
        if "model" not in agent_cfg and "model_id" not in agent_cfg:
            errors.append(f"agents.{agent_name}: missing 'model' (or 'model_id')")

    return errors


# -- deploy helpers ----------------------------------------------------------


class DeployResult:
    """Tracks what was created/updated/errored during a deploy."""

    def __init__(self) -> None:
        self.providers: List[Dict[str, str]] = []
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
    def skipped(self) -> int:
        return sum(
            1 for items in (self.providers, self.mcp_servers, self.knowledge_bases, self.agents)
            for item in items if item["status"] == "skipped"
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


# -- step: providers ---------------------------------------------------------


def _deploy_providers(
    providers: List[Dict[str, Any]],
    result: DeployResult,
    dry_run: bool,
    verbose: bool,
) -> None:
    if not providers:
        return

    console.print("\n[bold cyan]Cloud Providers[/bold cyan]")

    for prov in providers:
        name = prov.get("name", "unnamed")
        try:
            if verbose:
                console.print(f"  [dim]-> {name} (priority={prov.get('priority', '-')})[/dim]")

            if dry_run:
                result.providers.append({"name": name, "status": "ok", "detail": "dry-run"})
                console.print(f"  [green]v[/green] {name} [dim](dry-run)[/dim]")
                continue

            # Build payload matching /api/providers/connect
            payload: Dict[str, Any] = {
                "provider_type": name,
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

            with console.status(f"  [cyan]Connecting {name}...[/cyan]"):
                api.post("/providers/connect", payload)

            result.providers.append({"name": name, "status": "ok", "detail": "connected"})
            console.print(f"  [green]v[/green] {name}")

        except APIError as exc:
            # Provider may already exist or keys not configured yet
            if exc.status_code == 409 or "already" in str(exc).lower():
                result.providers.append({"name": name, "status": "ok", "detail": "already connected"})
                console.print(f"  [green]v[/green] {name} [dim](already connected)[/dim]")
            else:
                result.providers.append({"name": name, "status": "skipped", "detail": str(exc)})
                console.print(f"  [yellow]-[/yellow] {name}: {exc} [dim](skipped)[/dim]")
        except Exception as exc:
            result.providers.append({"name": name, "status": "skipped", "detail": str(exc)})
            console.print(f"  [yellow]-[/yellow] {name}: {exc} [dim](skipped)[/dim]")


# -- step: find or create project --------------------------------------------


def _find_or_create_project(stack_name: str, verbose: bool) -> str:
    """Find an existing project or create one. Returns project_id."""
    if verbose:
        console.print("\n[dim]Looking for existing project...[/dim]")

    try:
        projects = api.get("/projects")
        # Response is a list
        if isinstance(projects, list) and len(projects) > 0:
            project_id = projects[0]["id"]
            if verbose:
                console.print(f"  [dim]Using project: {projects[0]['name']} ({project_id[:8]}...)[/dim]")
            return project_id
    except (APIError, Exception):
        pass

    # Create a new project
    if verbose:
        console.print(f"  [dim]Creating project: {stack_name}[/dim]")

    resp = api.post("/projects", {
        "name": stack_name,
        "description": f"Deployed from bonito.yaml",
    })
    project_id = resp["id"]
    console.print(f"  [green]v[/green] Project created: {stack_name} [dim]({project_id[:8]}...)[/dim]")
    return project_id


# -- step: knowledge bases ---------------------------------------------------


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

    console.print("\n[bold cyan]Knowledge Bases[/bold cyan]")

    for name, cfg in kbs.items():
        try:
            if verbose:
                sources = cfg.get("sources", [])
                console.print(f"  [dim]-> {name} ({len(sources)} source(s))[/dim]")

            if dry_run:
                result.knowledge_bases.append({"name": name, "status": "ok", "detail": "dry-run"})
                console.print(f"  [green]v[/green] {name} [dim](dry-run)[/dim]")
                continue

            # Create the knowledge base
            embedding = cfg.get("embedding", {})
            chunking = cfg.get("chunking", {})

            payload: Dict[str, Any] = {
                "name": name,
                "description": cfg.get("description"),
                "source_type": "upload",
                "embedding_model": embedding.get("model", "auto"),
                "chunk_size": chunking.get("max_chunk_size", 512),
                "chunk_overlap": chunking.get("overlap", 50),
            }

            with console.status(f"  [cyan]Creating {name}...[/cyan]"):
                try:
                    resp = api.post("/knowledge-bases", payload)
                except APIError as create_exc:
                    # If KB already exists, find it and reuse
                    if "already exists" in str(create_exc).lower():
                        existing = api.get("/knowledge-bases")
                        if isinstance(existing, list):
                            for kb in existing:
                                if kb.get("name") == name:
                                    kb_id_map[name] = kb["id"]
                                    result.knowledge_bases.append({"name": name, "status": "ok", "detail": f"reusing existing ({kb['id'][:8]}...)"})
                                    console.print(f"  [green]v[/green] {name} [dim](already exists, reusing)[/dim]")
                                    break
                            else:
                                raise create_exc
                        else:
                            raise create_exc
                        continue
                    raise

            kb_id = resp.get("id", "")
            kb_id_map[name] = kb_id

            # Configure compression if specified
            compression_cfg = cfg.get("compression")
            if compression_cfg:
                method = compression_cfg.get("method")
                if method:
                    try:
                        api.put(f"/knowledge-bases/{kb_id}/config", json={"compression": {"method": method}})
                        if verbose:
                            console.print(f"    [dim]-> Compression set to {method}[/dim]")
                    except APIError as compress_exc:
                        if verbose:
                            console.print(f"    [dim yellow]! Failed to set compression: {compress_exc}[/dim yellow]")

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
                                        console.print(f"    [dim red]! Upload failed: {file_path.name}: {upload_exc}[/dim red]")
                    else:
                        if verbose:
                            console.print(f"    [dim yellow]! Directory not found: {src_path}[/dim yellow]")

            detail = f"created ({kb_id[:8]}...)"
            if uploaded:
                detail += f", {uploaded} file(s) uploaded"

            result.knowledge_bases.append({"name": name, "status": "ok", "detail": detail})
            console.print(f"  [green]v[/green] {name} - {detail}")

        except (APIError, Exception) as exc:
            result.knowledge_bases.append({"name": name, "status": "error", "detail": str(exc)})
            console.print(f"  [red]x[/red] {name}: {exc}")

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


# -- step: agents ------------------------------------------------------------


def _find_existing_agents(project_id: str) -> Dict[str, Dict[str, Any]]:
    """Fetch existing agents in the project, keyed by name (lowercased)."""
    try:
        agents_list = api.get(f"/projects/{project_id}/agents")
        if isinstance(agents_list, list):
            return {a["name"].lower(): a for a in agents_list if a.get("name")}
    except (APIError, Exception):
        pass
    return {}


def _deploy_agents(
    agents: Dict[str, Dict[str, Any]],
    mcp_servers_cfg: Dict[str, Dict[str, Any]],
    result: DeployResult,
    dry_run: bool,
    verbose: bool,
    yaml_dir: Path,
    kb_id_map: Dict[str, str],
    project_id: str,
) -> Dict[str, str]:
    """Deploy agents to a project. Returns {agent_name: agent_id} map."""
    if not agents:
        return {}

    console.print("\n[bold cyan]Agents[/bold cyan]")

    agent_id_map: Dict[str, str] = {}

    # Pre-fetch existing agents so we can update instead of duplicate
    existing_agents: Dict[str, Dict[str, Any]] = {}
    if not dry_run:
        existing_agents = _find_existing_agents(project_id)
        if verbose and existing_agents:
            console.print(f"  [dim]Found {len(existing_agents)} existing agent(s) in project[/dim]")

    for name, cfg in agents.items():
        try:
            display_name = cfg.get("display_name", name)

            if verbose:
                model = cfg.get("model", {})
                primary = model.get("primary", "auto") if isinstance(model, dict) else str(model)
                console.print(f"  [dim]-> {display_name} (model={primary})[/dim]")

            if dry_run:
                # Validate system prompt file exists
                prompt_ref = cfg.get("system_prompt", "")
                if prompt_ref and not prompt_ref.startswith("You "):
                    prompt_path = (yaml_dir / prompt_ref).resolve()
                    if not prompt_path.exists():
                        result.agents.append({"name": name, "status": "error", "detail": f"system prompt not found: {prompt_ref}"})
                        console.print(f"  [red]x[/red] {display_name}: system prompt not found: {prompt_ref}")
                        continue
                result.agents.append({"name": name, "status": "ok", "detail": "dry-run"})
                console.print(f"  [green]v[/green] {display_name} [dim](dry-run)[/dim]")
                continue

            # Read system prompt (can be inline string or file reference)
            prompt_ref = cfg.get("system_prompt", "")
            if prompt_ref and not prompt_ref.startswith("You "):
                try:
                    system_prompt = _read_system_prompt(prompt_ref, yaml_dir)
                except FileNotFoundError:
                    # Treat as inline prompt
                    system_prompt = prompt_ref
            else:
                system_prompt = prompt_ref

            if not system_prompt:
                system_prompt = f"You are {display_name}."

            # Build model ID from model config
            model_cfg = cfg.get("model", {})
            if isinstance(model_cfg, dict):
                model_id = model_cfg.get("primary", "auto")
            else:
                model_id = str(model_cfg)

            # Build the payload matching AgentCreate/AgentUpdate schema
            params = cfg.get("parameters", {})
            payload: Dict[str, Any] = {
                "name": display_name,
                "description": cfg.get("description", ""),
                "system_prompt": system_prompt,
                "model_id": model_id,
            }

            # Model config (temperature, max_tokens, etc.)
            if params:
                payload["model_config"] = {}
                if params.get("temperature") is not None:
                    payload["model_config"]["temperature"] = params["temperature"]
                if params.get("max_tokens") is not None:
                    payload["model_config"]["max_tokens"] = params["max_tokens"]

            # Enable tools if agent has MCP servers or delegates
            agent_mcp_refs = cfg.get("mcp_servers", [])
            agent_delegates = cfg.get("delegates", [])
            if agent_mcp_refs or agent_delegates:
                payload["tool_policy"] = {"mode": "allowed", "allowed": [], "denied": [], "http_allowlist": []}
            elif cfg.get("rag"):
                # RAG agents get search_knowledge_base tool
                payload["tool_policy"] = {"mode": "allowed", "allowed": ["kb_search"], "denied": [], "http_allowlist": []}

            # Attach knowledge base if configured via RAG section
            rag = cfg.get("rag", {})
            if rag and rag.get("knowledge_base"):
                kb_name = rag["knowledge_base"]
                kb_id = kb_id_map.get(kb_name)
                if kb_id:
                    payload["knowledge_base_ids"] = [kb_id]
                elif verbose:
                    console.print(f"    [dim yellow]! KB '{kb_name}' not found - skipping[/dim yellow]")

            # Note: agent secrets are managed via /api/secrets, not in the agent payload

            # Check if agent already exists — update instead of creating a duplicate
            existing = existing_agents.get(display_name.lower())
            if existing:
                agent_id = existing["id"]
                with console.status(f"  [cyan]Updating {display_name}...[/cyan]"):
                    resp = api.put(f"/agents/{agent_id}", payload)
                agent_id_map[name] = agent_id
                action = "updated"
            else:
                with console.status(f"  [cyan]Creating {display_name}...[/cyan]"):
                    resp = api.post(f"/projects/{project_id}/agents", payload)
                agent_id = resp.get("id", "")
                agent_id_map[name] = agent_id
                action = "created"

            detail_parts = [f"{agent_id[:8]}...", f"model: {model_id}", action]

            # Register MCP servers for this agent
            agent_mcp_refs = cfg.get("mcp_servers", [])
            mcp_connected = 0
            for server_name in agent_mcp_refs:
                server_cfg = mcp_servers_cfg.get(server_name, {})
                if not server_cfg:
                    if verbose:
                        console.print(f"    [dim yellow]! MCP '{server_name}' not defined in mcp_servers section[/dim yellow]")
                    continue

                try:
                    mcp_payload: Dict[str, Any] = {
                        "name": server_name,
                        "transport_type": "http",
                        "endpoint_config": {
                            "url": server_cfg.get("url", ""),
                        },
                    }

                    # Auth config
                    auth = server_cfg.get("auth", {})
                    if auth:
                        if auth.get("token"):
                            mcp_payload["auth_config"] = {
                                "type": "bearer",
                                "token": auth["token"],
                            }
                        else:
                            mcp_payload["auth_config"] = {"type": "none"}
                    else:
                        mcp_payload["auth_config"] = {"type": "none"}

                    api.post(f"/agents/{agent_id}/mcp-servers", mcp_payload)
                    mcp_connected += 1
                except Exception as mcp_exc:
                    if verbose:
                        console.print(f"    [dim red]! MCP {server_name}: {mcp_exc}[/dim red]")

            if mcp_connected:
                detail_parts.append(f"{mcp_connected} MCP server(s)")

            # Attach KB if specified
            if rag and rag.get("knowledge_base") and rag["knowledge_base"] in kb_id_map:
                detail_parts.append("KB attached")

            detail = ", ".join(detail_parts)
            result.agents.append({"name": name, "status": "ok", "detail": detail})
            status_icon = "[yellow]~[/yellow]" if action == "updated" else "[green]v[/green]"
            console.print(f"  {status_icon} {display_name} [dim]({detail})[/dim]")

        except FileNotFoundError as exc:
            result.agents.append({"name": name, "status": "error", "detail": str(exc)})
            console.print(f"  [red]x[/red] {cfg.get('display_name', name)}: {exc}")
        except (APIError, Exception) as exc:
            result.agents.append({"name": name, "status": "error", "detail": str(exc)})
            console.print(f"  [red]x[/red] {cfg.get('display_name', name)}: {exc}")

    return agent_id_map


# -- step: agent connections (delegation) ------------------------------------


def _create_agent_connections(
    agents: Dict[str, Dict[str, Any]],
    agent_id_map: Dict[str, str],
    result: DeployResult,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Create connections from Bonobot orchestrators to their delegate agents."""
    connections_made = 0

    for name, cfg in agents.items():
        delegates = cfg.get("delegates", [])
        if not delegates:
            continue

        source_id = agent_id_map.get(name)
        if not source_id:
            continue

        display_name = cfg.get("display_name", name)

        if verbose:
            console.print(f"\n  [dim]Wiring {display_name} delegation...[/dim]")

        for delegate_cfg in delegates:
            # Delegates can be strings (agent names) or dicts with agent + domains
            if isinstance(delegate_cfg, str):
                target_name = delegate_cfg
            elif isinstance(delegate_cfg, dict):
                target_name = delegate_cfg.get("agent", "")
            else:
                continue

            target_id = agent_id_map.get(target_name)
            if not target_id:
                if verbose:
                    console.print(f"    [dim yellow]! delegate '{target_name}' not found in deployed agents[/dim yellow]")
                continue

            if dry_run:
                if verbose:
                    console.print(f"    [dim]{display_name} -> {target_name} (dry-run)[/dim]")
                continue

            try:
                api.post(f"/agents/{source_id}/connections", {
                    "target_agent_id": target_id,
                    "connection_type": "handoff",
                    "label": target_name,
                    "enabled": True,
                })
                connections_made += 1
                if verbose:
                    console.print(f"    [green]v[/green] {display_name} -> {target_name}")
            except Exception as exc:
                if "already exists" in str(exc).lower():
                    if verbose:
                        console.print(f"    [dim]{display_name} -> {target_name} (exists)[/dim]")
                else:
                    if verbose:
                        console.print(f"    [dim red]! {display_name} -> {target_name}: {exc}[/dim red]")

    if connections_made and not dry_run:
        console.print(f"\n  [green]{connections_made} agent connection(s) created[/green]")


# -- summary -----------------------------------------------------------------


def _print_summary(result: DeployResult, stack_name: str, dry_run: bool) -> None:
    """Print a final deployment summary table."""
    console.print()

    table = Table(
        title=f"{'Dry-run' if dry_run else 'Deploy'} Summary - {stack_name}",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
    )
    table.add_column("Resource", style="bold")
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("Detail", style="dim")

    _icon = {"providers": "Cloud", "mcp_servers": "MCP", "knowledge_bases": "KB", "agents": "Agent"}

    for category, items in [
        ("providers", result.providers),
        ("mcp_servers", result.mcp_servers),
        ("knowledge_bases", result.knowledge_bases),
        ("agents", result.agents),
    ]:
        label = _icon[category]
        for item in items:
            status_map = {"ok": ("green", "ok"), "error": ("red", "FAIL"), "skipped": ("yellow", "SKIP")}
            status_color, status_text = status_map.get(item["status"], ("red", "FAIL"))
            table.add_row(
                label,
                item["name"],
                f"[{status_color}]{status_text}[/{status_color}]",
                item.get("detail", ""),
            )

    console.print(table)

    if result.errors:
        console.print(f"\n[red bold]{result.errors} error(s) during deploy[/red bold]")
    else:
        verb = "validated" if dry_run else "deployed"
        msg = f"{result.ok} resource(s) {verb} successfully"
        if result.skipped:
            msg += f", {result.skipped} skipped"
        console.print(f"\n[green bold]{msg}[/green bold]")


# -- next steps --------------------------------------------------------------


def _print_next_steps(
    result: DeployResult,
    stack_name: str,
    project_id: str,
    agent_id_map: Dict[str, str],
    cfg: Dict[str, Any],
) -> None:
    """Print context-aware next steps after a successful deploy."""
    lines: List[str] = []

    # --- Always show ---
    lines.append("[bold cyan]Dashboard:[/bold cyan]  https://getbonito.com/dashboard")
    lines.append("[bold cyan]View logs:[/bold cyan]  bonito gateway logs")

    # --- Providers ---
    has_providers = any(p["status"] == "ok" for p in result.providers)
    if has_providers:
        lines.append("")
        lines.append("[bold green]Providers[/bold green]")
        lines.append("  List models:    [cyan]bonito models list[/cyan]")
        lines.append(
            "  Test gateway:   [white]curl -X POST https://api.getbonito.com/v1/chat/completions \\\n"
            "                    -H 'Authorization: Bearer $BONITO_API_KEY' \\\n"
            "                    -H 'Content-Type: application/json' \\\n"
            '                    -d \'{"model":"gpt-4","messages":[{"role":"user","content":"Hello!"}]}\'[/white]'
        )

    # --- Agents ---
    deployed_agents = [a for a in result.agents if a["status"] == "ok"]
    agents_cfg = cfg.get("agents", {})
    if deployed_agents and agent_id_map:
        lines.append("")
        lines.append("[bold green]Agents[/bold green]")
        lines.append(f"  Project:        https://getbonito.com/agents/{project_id}")

        first_agent_name = next(iter(agent_id_map), None)
        if first_agent_name:
            lines.append(f"  Test chat:      [cyan]bonito chat --agent {first_agent_name}[/cyan]")

        # Widget embed and API endpoint for each deployed agent
        for agent_name, agent_id in agent_id_map.items():
            agent_cfg = agents_cfg.get(agent_name, {})
            display = agent_cfg.get("display_name", agent_name)

            lines.append(f"  API endpoint:   [white]POST https://api.getbonito.com/api/agents/{agent_id}/execute[/white]")

            if agent_cfg.get("widget_enabled"):
                lines.append(f"  BonBon widget ({display}):")
                lines.append(
                    f'    [white]<script src="https://getbonito.com/widget/chat/{agent_id}"></script>[/white]'
                )

    # --- Knowledge Bases ---
    deployed_kbs = [kb for kb in result.knowledge_bases if kb["status"] == "ok"]
    if deployed_kbs:
        lines.append("")
        lines.append("[bold green]Knowledge Bases[/bold green]")
        lines.append("  Manage:         https://getbonito.com/admin/kb")
        lines.append("  Documents are being processed. Check status with: [cyan]bonito kb list[/cyan]")

    # --- MCP Servers ---
    deployed_mcp = [m for m in result.mcp_servers if m["status"] == "ok"]
    if deployed_mcp:
        lines.append("")
        lines.append("[bold green]MCP Servers[/bold green]")
        # Find the first agent that has MCP servers attached
        mcp_agent_name: Optional[str] = None
        for agent_name, agent_cfg in agents_cfg.items():
            if agent_cfg.get("mcp_servers") and agent_name in agent_id_map:
                mcp_agent_name = agent_name
                break
        if mcp_agent_name:
            lines.append(
                f"  MCP servers are registered per-agent. Test with: [cyan]bonito chat --agent {mcp_agent_name}[/cyan]"
            )
        else:
            lines.append("  MCP servers are registered per-agent. Test with: [cyan]bonito chat --agent <name>[/cyan]")

    # --- Connect your own infrastructure ---
    lines.append("")
    lines.append("[bold green]Connecting to your own infrastructure[/bold green]")
    lines.append("  Self-hosted:      Set [cyan]BONITO_API_URL[/cyan] to point to your backend")
    lines.append("  VPC deployment:   See https://getbonito.com/docs#vpc-deployment")
    lines.append("  Custom providers: [cyan]bonito providers connect --help[/cyan]")

    # --- Footer ---
    lines.append("")
    lines.append("[dim]Docs: https://getbonito.com/docs[/dim]")
    lines.append("[dim]CLI help: bonito --help[/dim]")

    panel_content = "\n".join(lines)
    console.print()
    console.print(Panel(
        panel_content,
        title="[bold green]Next Steps[/bold green]",
        border_style="green",
        padding=(1, 2),
    ))


# -- main command ------------------------------------------------------------


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
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate only - don't deploy"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
):
    """
    Deploy a full Bonito stack from a declarative YAML file.

    Reads bonito.yaml and creates/updates providers, knowledge bases,
    and agents in the correct order.

    \b
    Examples:
        bonito deploy -f bonito.yaml
        bonito deploy -f bonito.yaml --dry-run
        bonito deploy -f bonito.yaml --verbose
    """
    ensure_authenticated()

    yaml_path = file.resolve()
    yaml_dir = yaml_path.parent

    # -- 1. Parse YAML -------------------------------------------------------
    console.print(Panel(
        f"[bold]{yaml_path.name}[/bold]\n[dim]{yaml_path}[/dim]",
        title="Bonito Deploy" + (" [yellow](dry-run)[/yellow]" if dry_run else ""),
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

    # -- 2. Resolve env vars -------------------------------------------------
    cfg = _resolve_env(cfg)

    unresolved = _find_unresolved(cfg)
    if unresolved:
        console.print(f"\n[yellow]{len(unresolved)} unresolved environment variable(s):[/yellow]")
        for u in unresolved[:10]:
            console.print(f"  [dim]* {u}[/dim]")
        if len(unresolved) > 10:
            console.print(f"  [dim]... and {len(unresolved) - 10} more[/dim]")
        if not dry_run:
            print_warning("Deploying with unresolved variables may cause errors")

    # -- 3. Validate ---------------------------------------------------------
    errors = _validate(cfg)
    if errors:
        console.print("\n[red bold]Validation errors:[/red bold]")
        for err in errors:
            console.print(f"  [red]* {err}[/red]")
        print_error(f"{len(errors)} validation error(s) - fix your YAML and retry")
        return

    stack_name = cfg.get("name", "unnamed")
    if verbose:
        console.print(f"\n[dim]Stack: {stack_name} (version {cfg.get('version', '?')})[/dim]")
        desc = cfg.get("description")
        if desc:
            console.print(f"[dim]{desc}[/dim]")

    result = DeployResult()

    # -- 4. Providers --------------------------------------------------------
    gateway = cfg.get("gateway", {})
    providers = gateway.get("providers", [])
    _deploy_providers(providers, result, dry_run, verbose)

    # -- 5. Knowledge Bases --------------------------------------------------
    kbs = cfg.get("knowledge_bases", {})
    kb_id_map = _deploy_knowledge_bases(kbs, result, dry_run, verbose, yaml_dir)

    # -- 5.5. Validate secrets (warn if missing, don't fail) ----------------
    secrets_list = cfg.get("secrets", [])
    if secrets_list and not dry_run:
        try:
            existing_secrets = api.get("/secrets")
            existing_names = {s.get("name") for s in existing_secrets}
            missing = [s for s in secrets_list if s not in existing_names]
            if missing:
                print_warning(f"Missing secrets (create with 'bonito secrets set'): {', '.join(missing)}")
        except APIError:
            if verbose:
                console.print("[dim yellow]Could not validate secrets[/dim yellow]")

    # -- 6. Find or create project -------------------------------------------
    project_id = ""
    if not dry_run:
        try:
            project_id = _find_or_create_project(stack_name, verbose)
        except (APIError, Exception) as exc:
            print_error(f"Failed to create project: {exc}")
            raise typer.Exit(1)

    # -- 7. Agents (with per-agent MCP servers) ------------------------------
    agents = cfg.get("agents", {})
    mcp_servers_cfg = cfg.get("mcp_servers", {})
    agent_id_map = _deploy_agents(
        agents, mcp_servers_cfg, result, dry_run, verbose,
        yaml_dir, kb_id_map, project_id,
    )

    # Track MCP servers in result for summary
    for server_name in mcp_servers_cfg:
        # Check if any agent referenced this server
        referenced = any(
            server_name in (cfg.get("agents", {}).get(a, {}).get("mcp_servers", []))
            for a in agents
        )
        if referenced:
            result.mcp_servers.append({"name": server_name, "status": "ok", "detail": "registered per-agent"})
        else:
            result.mcp_servers.append({"name": server_name, "status": "ok", "detail": "defined (no agent reference)"})

    # -- 8. Agent connections (delegation) -----------------------------------
    _create_agent_connections(agents, agent_id_map, result, dry_run, verbose)

    # -- 9. Summary ----------------------------------------------------------
    _print_summary(result, stack_name, dry_run)

    # -- 10. Next steps (only on successful, real deploys) -------------------
    if result.errors == 0 and not dry_run:
        _print_next_steps(result, stack_name, project_id, agent_id_map, cfg)

    if result.errors:
        raise typer.Exit(1)
