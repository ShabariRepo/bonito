"""Knowledge Base (AI Context / RAG) management commands."""

from __future__ import annotations

import json as _json
import os
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from ..api import api, APIError
from ..utils.auth import ensure_authenticated
from ..utils.display import (
    format_status,
    format_tokens,
    format_timestamp,
    get_output_format,
    print_dict_as_table,
    print_error,
    print_info,
    print_success,
    print_table,
    print_warning,
)

console = Console()
app = typer.Typer(help="📚 Knowledge base (AI Context / RAG) management")

_KB = "/knowledge-bases"


# ── list ────────────────────────────────────────────────────────


@app.command("list")
def list_knowledge_bases(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all knowledge bases."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching knowledge bases…[/cyan]"):
            kbs = api.get(f"{_KB}")

        if fmt == "json":
            console.print_json(_json.dumps(kbs, default=str))
            return

        if not kbs:
            console.print(
                Panel(
                    "[dim]No knowledge bases yet.[/dim]\n\n"
                    "Create one: [cyan]bonito kb create --name 'My KB'[/cyan]",
                    title="📚 Knowledge Bases",
                    border_style="dim",
                )
            )
            return

        rows = []
        for kb in kbs:
            rows.append({
                "ID": str(kb.get("id", ""))[:8] + "…",
                "Name": kb.get("name", "—"),
                "Source": kb.get("source_type", "—"),
                "Status": format_status(kb.get("status", "unknown")),
                "Docs": str(kb.get("document_count", 0)),
                "Chunks": str(kb.get("chunk_count", 0)),
            })
        print_table(rows, title="📚 Knowledge Bases")
        print_info(f"{len(kbs)} knowledge base(s)")

    except APIError as exc:
        print_error(f"Failed to list knowledge bases: {exc}")


# ── create ──────────────────────────────────────────────────────

_SOURCE_TYPES = ["upload", "s3", "azure_blob", "gcs"]


@app.command("create")
def create_knowledge_base(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Knowledge base name"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Description"),
    source_type: Optional[str] = typer.Option(
        "upload", "--source", "-s", help="Source type: upload, s3, azure_blob, gcs"
    ),
    embedding_model: str = typer.Option("auto", "--embedding-model", help="Embedding model"),
    chunk_size: int = typer.Option(512, "--chunk-size", help="Chunk size (100-2048)"),
    chunk_overlap: int = typer.Option(50, "--chunk-overlap", help="Chunk overlap (0-200)"),
    json_output: bool = typer.Option(False, "--json"),
):
    """
    Create a new knowledge base.

    Examples:
        bonito kb create --name "Product Docs" --description "All product documentation"
        bonito kb create --name "S3 Docs" --source s3
        bonito kb create   # interactive
    """
    fmt = get_output_format(json_output)
    ensure_authenticated()

    if not name:
        name = Prompt.ask("[cyan]Knowledge base name[/cyan]")
    if not description:
        description = Prompt.ask("[cyan]Description (optional)[/cyan]", default="")
    if source_type not in _SOURCE_TYPES:
        print_error(f"Invalid source type. Choose from: {', '.join(_SOURCE_TYPES)}")
        return

    payload = {
        "name": name,
        "description": description or None,
        "source_type": source_type,
        "embedding_model": embedding_model,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
    }

    try:
        with console.status("[cyan]Creating knowledge base…[/cyan]"):
            result = api.post(f"{_KB}", payload)

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            info = {
                "ID": str(result.get("id", "—")),
                "Name": result.get("name", name),
                "Source": result.get("source_type", source_type),
                "Status": result.get("status", "pending"),
                "Embedding Model": result.get("embedding_model", embedding_model),
                "Chunk Size": str(result.get("chunk_size", chunk_size)),
            }
            print_success(f"Knowledge base '{name}' created")
            print_dict_as_table(info, title="📚 Knowledge Base")
            if source_type == "upload":
                console.print(
                    "\n[dim]Upload documents: "
                    f"[cyan]bonito kb upload {str(result.get('id', 'KB_ID'))} file.pdf[/cyan][/dim]"
                )
    except APIError as exc:
        print_error(f"Failed to create knowledge base: {exc}")


# ── info ────────────────────────────────────────────────────────


@app.command("info")
def kb_info(
    kb_id: str = typer.Argument(..., help="Knowledge base UUID"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Show detailed information and stats for a knowledge base."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching knowledge base…[/cyan]"):
            kb = api.get(f"{_KB}/{kb_id}")
            # Also fetch stats
            stats = {}
            try:
                stats = api.get(f"{_KB}/{kb_id}/stats")
            except APIError:
                pass

        if fmt == "json":
            console.print_json(_json.dumps({**kb, "stats": stats}, default=str))
            return

        info = {
            "ID": str(kb.get("id", "—")),
            "Name": kb.get("name", "—"),
            "Description": kb.get("description", "—") or "—",
            "Source Type": kb.get("source_type", "—"),
            "Status": format_status(kb.get("status", "unknown")),
            "Embedding Model": kb.get("embedding_model", "—"),
            "Chunk Size": str(kb.get("chunk_size", "—")),
            "Chunk Overlap": str(kb.get("chunk_overlap", "—")),
            "Created": format_timestamp(kb.get("created_at", "—")),
            "Updated": format_timestamp(kb.get("updated_at", "—")),
        }
        print_dict_as_table(info, title=f"📚 {kb.get('name', 'Knowledge Base')}")

        if stats:
            stat_info = {
                "Documents": str(stats.get("total_documents", 0)),
                "Chunks": str(stats.get("total_chunks", 0)),
                "Total Tokens": format_tokens(stats.get("total_tokens", 0)),
                "Avg Chunk Size": f"{stats.get('avg_chunk_size', 0):.0f} tokens",
                "Last Sync": format_timestamp(stats.get("last_sync", "—")) if stats.get("last_sync") else "Never",
            }
            print_dict_as_table(stat_info, title="📊 Statistics")

            doc_types = stats.get("document_types", {})
            if doc_types:
                rows = [{"Type": t, "Count": str(c)} for t, c in doc_types.items()]
                print_table(rows, title="📄 Document Types")

            status_counts = stats.get("status_counts", {})
            if status_counts:
                rows = [{"Status": format_status(s), "Count": str(c)} for s, c in status_counts.items()]
                print_table(rows, title="📋 Status Breakdown")

    except APIError as exc:
        print_error(f"Failed to get knowledge base: {exc}")


# ── upload ──────────────────────────────────────────────────────


@app.command("upload")
def upload_document(
    kb_id: str = typer.Argument(..., help="Knowledge base UUID"),
    files: List[Path] = typer.Argument(..., help="File(s) to upload"),
    json_output: bool = typer.Option(False, "--json"),
):
    """
    Upload one or more documents to a knowledge base.

    Supported formats: PDF, DOCX, TXT, MD, HTML, CSV, JSON

    Examples:
        bonito kb upload <kb-id> report.pdf
        bonito kb upload <kb-id> doc1.pdf doc2.md notes.txt
    """
    fmt = get_output_format(json_output)
    ensure_authenticated()

    results = []
    for file_path in files:
        if not file_path.exists():
            print_error(f"File not found: {file_path}", exit_code=0)
            results.append({"file": str(file_path), "error": "File not found"})
            continue

        file_size = file_path.stat().st_size
        if file_size > 50 * 1024 * 1024:
            print_error(f"File too large (>50MB): {file_path}", exit_code=0)
            results.append({"file": str(file_path), "error": "File too large (>50MB)"})
            continue

        try:
            with console.status(f"[cyan]Uploading {file_path.name}…[/cyan]"):
                # Upload uses multipart form data, not JSON
                import httpx

                with open(file_path, "rb") as fh:
                    headers = {}
                    from ..config import get_api_key
                    token = get_api_key()
                    if token:
                        headers["Authorization"] = f"Bearer {token}"
                    headers["User-Agent"] = "bonito-cli/0.2.0"

                    resp = httpx.post(
                        f"{api.base_url}/api{_KB}/{kb_id}/documents",
                        files={"file": (file_path.name, fh, _guess_mime(file_path.name))},
                        headers=headers,
                        timeout=120.0,
                    )

                if resp.status_code >= 400:
                    try:
                        detail = resp.json().get("detail", f"HTTP {resp.status_code}")
                    except Exception:
                        detail = f"HTTP {resp.status_code}"
                    raise APIError(str(detail), resp.status_code)

                data = resp.json()
                results.append(data)

                if fmt != "json":
                    status_str = data.get("status", "pending")
                    print_success(
                        f"{file_path.name} — {data.get('message', status_str)}"
                    )

        except APIError as exc:
            if fmt != "json":
                console.print(f"[red]✗ {file_path.name}: {exc}[/red]")
            results.append({"file": str(file_path), "error": str(exc)})

    if fmt == "json":
        console.print_json(_json.dumps(results, default=str))
    elif results:
        ok = sum(1 for r in results if "error" not in r)
        print_info(f"{ok}/{len(files)} file(s) uploaded successfully")


def _guess_mime(filename: str) -> str:
    """Guess MIME type from extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    _mime = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain",
        "md": "text/markdown",
        "html": "text/html",
        "csv": "text/csv",
        "json": "application/json",
    }
    return _mime.get(ext, "application/octet-stream")


# ── search ──────────────────────────────────────────────────────


@app.command("search")
def search_kb(
    kb_id: str = typer.Argument(..., help="Knowledge base UUID"),
    query: str = typer.Argument(..., help="Search query"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of results (1-50)"),
    json_output: bool = typer.Option(False, "--json"),
):
    """
    Search a knowledge base with a natural language query.

    Uses vector similarity search to find the most relevant chunks.

    Examples:
        bonito kb search <kb-id> "How do I configure authentication?"
        bonito kb search <kb-id> "pricing details" --top-k 10
    """
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status(f"[cyan]Searching '{query[:40]}{'…' if len(query)>40 else ''}'…[/cyan]"):
            result = api.post(f"{_KB}/{kb_id}/search", {
                "query": query,
                "top_k": top_k,
            })

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
            return

        results = result.get("results", [])
        search_time = result.get("search_time_ms", 0)

        if not results:
            print_info(f"No results for '{query}'")
            return

        console.print(
            f"\n[bold cyan]🔍 Search Results[/bold cyan] "
            f"[dim]({len(results)} results in {search_time}ms)[/dim]\n"
        )

        for i, r in enumerate(results, 1):
            score = r.get("score", 0)
            score_color = "green" if score >= 0.8 else "yellow" if score >= 0.5 else "red"
            source = r.get("source_file") or r.get("document_name", "unknown")
            page = r.get("source_page")
            section = r.get("source_section")

            location_parts = [source]
            if page:
                location_parts.append(f"p.{page}")
            if section:
                location_parts.append(section)
            location = " › ".join(location_parts)

            content = r.get("content", "")
            # Truncate long content for display
            if len(content) > 300:
                content = content[:297] + "…"

            console.print(
                Panel(
                    f"{content}\n\n"
                    f"[dim]📄 {location}[/dim]",
                    title=f"[{score_color}]#{i} Score: {score:.4f}[/{score_color}]",
                    border_style=score_color,
                    padding=(0, 1),
                )
            )

    except APIError as exc:
        print_error(f"Search failed: {exc}")


# ── delete ──────────────────────────────────────────────────────


@app.command("delete")
def delete_kb(
    kb_id: str = typer.Argument(..., help="Knowledge base UUID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Delete a knowledge base and all its documents."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    if not force and fmt != "json":
        if not Confirm.ask(
            f"[red]Delete knowledge base {kb_id[:8]}… and all its documents?[/red]"
        ):
            print_info("Cancelled")
            return

    try:
        with console.status("[cyan]Deleting knowledge base…[/cyan]"):
            api.delete(f"{_KB}/{kb_id}")

        if fmt == "json":
            console.print_json(f'{{"status":"deleted","id":"{kb_id}"}}')
        else:
            print_success(f"Knowledge base {kb_id[:8]}… deleted")
    except APIError as exc:
        print_error(f"Delete failed: {exc}")


# ── sync ────────────────────────────────────────────────────────


@app.command("sync")
def sync_kb(
    kb_id: str = typer.Argument(..., help="Knowledge base UUID"),
    force: bool = typer.Option(False, "--force", "-f", help="Force sync even if already running"),
    json_output: bool = typer.Option(False, "--json"),
):
    """
    Trigger a sync for a cloud-storage-backed knowledge base.

    This will pull new/updated documents from the configured cloud storage
    (S3, Azure Blob, or GCS) and process them.

    Examples:
        bonito kb sync <kb-id>
        bonito kb sync <kb-id> --force
    """
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Starting sync…[/cyan]"):
            result = api.post(f"{_KB}/{kb_id}/sync", {"force": force})

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            status_val = result.get("status", "unknown")
            print_success(f"Sync started — status: {status_val}")

            info = {
                "KB ID": str(result.get("knowledge_base_id", kb_id))[:8] + "…",
                "Status": format_status(status_val),
                "Progress": f"{result.get('progress_percentage', 0)}%",
                "Files Processed": str(result.get("files_processed", 0)),
                "Files Total": str(result.get("files_total", 0)),
            }
            print_dict_as_table(info, title="🔄 Sync Status")
            console.print(
                "\n[dim]Check progress: "
                f"[cyan]bonito kb sync-status {kb_id}[/cyan][/dim]"
            )
    except APIError as exc:
        print_error(f"Sync failed: {exc}")


# ── sync-status ─────────────────────────────────────────────────


@app.command("sync-status")
def sync_status(
    kb_id: str = typer.Argument(..., help="Knowledge base UUID"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Check the current sync status for a knowledge base."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Checking sync status…[/cyan]"):
            result = api.get(f"{_KB}/{kb_id}/sync-status")

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            status_val = result.get("status", "unknown")
            info = {
                "Status": format_status(status_val),
                "Progress": f"{result.get('progress_percentage', 0) or 0}%",
                "Files Processed": str(result.get("files_processed", 0)),
                "Files Total": str(result.get("files_total", 0)),
                "Current File": result.get("current_file") or "—",
            }
            if result.get("started_at"):
                info["Started"] = format_timestamp(result["started_at"])
            if result.get("error_message"):
                info["Error"] = result["error_message"]

            print_dict_as_table(info, title="🔄 Sync Status")
    except APIError as exc:
        print_error(f"Failed to get sync status: {exc}")


# ── documents ───────────────────────────────────────────────────


@app.command("documents")
def list_documents(
    kb_id: str = typer.Argument(..., help="Knowledge base UUID"),
    json_output: bool = typer.Option(False, "--json"),
):
    """List all documents in a knowledge base."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching documents…[/cyan]"):
            docs = api.get(f"{_KB}/{kb_id}/documents")

        if fmt == "json":
            console.print_json(_json.dumps(docs, default=str))
            return

        if not docs:
            print_info("No documents in this knowledge base")
            return

        rows = []
        for d in docs:
            size = d.get("file_size", 0)
            size_str = f"{size / 1024:.1f}KB" if size and size < 1_000_000 else f"{(size or 0) / 1_048_576:.1f}MB"
            rows.append({
                "ID": str(d.get("id", ""))[:8] + "…",
                "File": d.get("file_name", "—"),
                "Type": d.get("file_type", "—"),
                "Size": size_str,
                "Status": format_status(d.get("status", "unknown")),
                "Chunks": str(d.get("chunk_count", 0)),
            })
        print_table(rows, title="📄 Documents")
        print_info(f"{len(docs)} document(s)")

    except APIError as exc:
        print_error(f"Failed to list documents: {exc}")


# ── delete-doc ──────────────────────────────────────────────────


@app.command("delete-doc")
def delete_document(
    kb_id: str = typer.Argument(..., help="Knowledge base UUID"),
    doc_id: str = typer.Argument(..., help="Document UUID"),
    force: bool = typer.Option(False, "--force", "-f"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Delete a document from a knowledge base."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    if not force and fmt != "json":
        if not Confirm.ask(f"[red]Delete document {doc_id[:8]}…?[/red]"):
            print_info("Cancelled")
            return

    try:
        with console.status("[cyan]Deleting document…[/cyan]"):
            api.delete(f"{_KB}/{kb_id}/documents/{doc_id}")

        if fmt == "json":
            console.print_json(f'{{"status":"deleted","id":"{doc_id}"}}')
        else:
            print_success(f"Document {doc_id[:8]}… deleted")
    except APIError as exc:
        print_error(f"Delete failed: {exc}")


# ── stats ───────────────────────────────────────────────────────


@app.command("stats")
def kb_stats(
    kb_id: str = typer.Argument(..., help="Knowledge base UUID"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Show statistics for a knowledge base."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching stats…[/cyan]"):
            stats = api.get(f"{_KB}/{kb_id}/stats")

        if fmt == "json":
            console.print_json(_json.dumps(stats, default=str))
            return

        info = {
            "Total Documents": str(stats.get("total_documents", 0)),
            "Total Chunks": str(stats.get("total_chunks", 0)),
            "Total Tokens": format_tokens(stats.get("total_tokens", 0)),
            "Avg Chunk Size": f"{stats.get('avg_chunk_size', 0):.0f} tokens",
            "Last Sync": format_timestamp(stats.get("last_sync", "—")) if stats.get("last_sync") else "Never",
        }
        print_dict_as_table(info, title="📊 Knowledge Base Statistics")

        doc_types = stats.get("document_types", {})
        if doc_types:
            rows = [{"Type": t, "Count": str(c)} for t, c in doc_types.items()]
            print_table(rows, title="📄 Document Types")

        status_counts = stats.get("status_counts", {})
        if status_counts:
            rows = [{"Status": s.title(), "Count": str(c)} for s, c in status_counts.items()]
            print_table(rows, title="📋 Status Breakdown")

    except APIError as exc:
        print_error(f"Failed to get stats: {exc}")
