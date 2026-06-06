"""
Walks the Typer CLI tree and emits one `IngestionRecord` per leaf command.

Uses **direct Typer introspection** (preferred — fast, deterministic, parsed
metadata). If the import fails (e.g. CLI dependencies missing in the
ingestion environment), falls back to running `bonito --help` via subprocess
and parsing the rendered output — coarser, but still works.

Each record looks like:

    title:        "agents create — Create a new Bonobot agent"
    source_path:  "agents.create"
    content:      help text + argument list + options list
    metadata:     {cli_group, cli_command, args: [...], options: [...]}
"""

from __future__ import annotations

import inspect
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

from .models import IngestionRecord, SourceType

logger = logging.getLogger(__name__)

# Path injection: the CLI lives at `<repo_root>/cli/bonito_cli` but isn't on
# sys.path by default when this module runs from `backend/`. Resolve dynamically.
_REPO_ROOT = Path(__file__).resolve().parents[5]
_CLI_SRC = _REPO_ROOT / "cli"


def _ensure_cli_on_path() -> None:
    """Make `bonito_cli` importable from this process."""
    if str(_CLI_SRC) not in sys.path:
        sys.path.insert(0, str(_CLI_SRC))


def _import_cli_app() -> Any | None:
    """
    Best-effort import of the Typer `app`. Returns None on failure so
    callers can fall back to the subprocess path.
    """
    _ensure_cli_on_path()
    try:
        from bonito_cli.app import app  # type: ignore[import-not-found]

        return app
    except Exception as exc:
        logger.warning("Could not import bonito_cli.app: %s", exc)
        return None


def _describe_param(param: inspect.Parameter) -> dict[str, Any]:
    """
    Turn an `inspect.Parameter` into a structured dict.

    Typer wraps arg/option metadata in default values of type
    `typer.models.OptionInfo` / `ArgumentInfo`. We pull help / default / type
    off those when present, and fall back to the bare default otherwise.
    """
    info: dict[str, Any] = {
        "name": param.name,
        "kind": "argument",
        "help": None,
        "default": None,
        "required": param.default is inspect.Parameter.empty,
        "type": str(param.annotation) if param.annotation is not inspect.Parameter.empty else None,
    }

    default = param.default
    if default is inspect.Parameter.empty:
        return info

    # Lazy import — typer should always be available if we got here, but be
    # defensive in case this runs in a stripped env.
    try:
        from typer.models import ArgumentInfo, OptionInfo  # type: ignore[import-not-found]
    except Exception:  # pragma: no cover
        info["default"] = repr(default)
        return info

    if isinstance(default, OptionInfo):
        info["kind"] = "option"
        info["help"] = default.help
        info["default"] = default.default if default.default is not ... else None
        info["required"] = default.default is ...
    elif isinstance(default, ArgumentInfo):
        info["kind"] = "argument"
        info["help"] = default.help
        info["default"] = default.default if default.default is not ... else None
        info["required"] = default.default is ...
    else:
        info["default"] = repr(default)
        info["required"] = False

    return info


def _record_for_command(
    group_path: tuple[str, ...],
    command_name: str,
    callback: Any,
    help_text: str | None,
) -> IngestionRecord:
    """Build the IngestionRecord for one leaf command."""
    dotted = ".".join((*group_path, command_name))
    parts: list[str] = []

    full_cmd = " ".join(("bonito", *group_path, command_name))
    parts.append(f"Command: {full_cmd}")

    docstring = (callback.__doc__ or "").strip() if callback else ""
    description = (help_text or docstring or "").strip()
    if description:
        parts.append(description)

    args_info: list[dict[str, Any]] = []
    options_info: list[dict[str, Any]] = []

    if callback is not None:
        try:
            sig = inspect.signature(callback)
        except (TypeError, ValueError):
            sig = None
        if sig is not None:
            for p in sig.parameters.values():
                desc = _describe_param(p)
                if desc["kind"] == "argument":
                    args_info.append(desc)
                else:
                    options_info.append(desc)

    if args_info:
        parts.append("Arguments:")
        for a in args_info:
            req = "*" if a["required"] else ""
            help_str = f" — {a['help']}" if a["help"] else ""
            parts.append(f"  - {a['name']}{req}{help_str}")

    if options_info:
        parts.append("Options:")
        for o in options_info:
            req = "*" if o["required"] else ""
            default = f" (default: {o['default']})" if o["default"] is not None else ""
            help_str = f" — {o['help']}" if o["help"] else ""
            parts.append(f"  - --{o['name'].replace('_', '-')}{req}{default}{help_str}")

    content = "\n\n".join(parts)
    title = f"{full_cmd}"
    if description:
        first_line = description.splitlines()[0].strip()
        title = f"{full_cmd} — {first_line[:120]}"

    return IngestionRecord(
        source_type=SourceType.CLI,
        source_path=dotted,
        title=title,
        content=content,
        metadata={
            "cli_group": ".".join(group_path) or None,
            "cli_command": command_name,
            "full_command": full_cmd,
            "args": args_info,
            "options": options_info,
            "extraction_method": "typer_introspection",
            "token_estimate": int(len(content.split()) * 1.3),
        },
    )


def _walk_typer(app: Any, prefix: tuple[str, ...] = ()) -> Iterable[IngestionRecord]:
    """Recursively walk Typer groups + commands, yielding records."""
    for cmd in getattr(app, "registered_commands", []) or []:
        callback = cmd.callback
        # Typer derives the displayed command name from callback name with
        # underscores → hyphens if `name` wasn't given explicitly.
        name = cmd.name or (callback.__name__.replace("_", "-") if callback else "?")
        help_text = getattr(cmd, "help", None) or getattr(cmd, "short_help", None)
        yield _record_for_command(prefix, name, callback, help_text)

    for group in getattr(app, "registered_groups", []) or []:
        sub = group.typer_instance
        if sub is None:
            continue
        group_name = group.name or ""
        new_prefix = (*prefix, group_name) if group_name else prefix
        yield from _walk_typer(sub, new_prefix)


def extract_from_typer() -> list[IngestionRecord]:
    """
    Preferred path: introspect the live Typer app.

    Returns `[]` if the import fails; callers can then try
    `extract_from_subprocess()`.
    """
    app = _import_cli_app()
    if app is None:
        return []
    records = list(_walk_typer(app))
    logger.info("Typer introspection produced %d CLI records", len(records))
    return records


# ─── Subprocess fallback ───────────────────────────────────────────────────


def _bonito_executable() -> str | None:
    """Find a usable `bonito` binary on PATH (or local venv)."""
    found = shutil.which("bonito")
    if found:
        return found
    # TODO: if `bonito-cli` isn't installed, consider invoking
    # `python -m bonito_cli` after pip-install-ing in dev. For now we
    # require the entry point.
    return None


def _run_help(args: list[str]) -> str:
    """Run `bonito <args> --help` and return stdout (best-effort)."""
    binary = _bonito_executable()
    if binary is None:
        return ""
    try:
        proc = subprocess.run(
            [binary, *args, "--help"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("`bonito %s --help` failed: %s", " ".join(args), exc)
        return ""
    return proc.stdout or ""


def extract_from_subprocess() -> list[IngestionRecord]:
    """
    Fallback path: shell out to `bonito --help` and walk subcommands.

    Coarser than Typer introspection — we end up with help text per node
    but not structured arg/option metadata. Good enough for KB retrieval
    when introspection isn't available.
    """
    # TODO: this is a minimal first cut. Full impl should:
    #   - parse the rich-formatted "Commands:" section to discover subgroups
    #   - recurse, building dotted paths
    #   - parse the "Arguments" / "Options" tables of each leaf command
    # For now we emit a single root record so the pipeline still works.
    root_help = _run_help([])
    if not root_help:
        return []
    return [
        IngestionRecord(
            source_type=SourceType.CLI,
            source_path="__root__",
            title="bonito — CLI root help",
            content=root_help,
            metadata={
                "extraction_method": "subprocess_fallback",
                "token_estimate": int(len(root_help.split()) * 1.3),
            },
        )
    ]


def extract_cli() -> list[IngestionRecord]:
    """
    Public entry point. Tries introspection first, falls back to subprocess.

    Records carry a `metadata.extraction_method` field so downstream
    consumers can tell which path produced them.
    """
    records = extract_from_typer()
    if records:
        return records
    logger.warning("Typer introspection returned no records — using subprocess fallback")
    return extract_from_subprocess()


__all__ = ["extract_cli", "extract_from_typer", "extract_from_subprocess"]
