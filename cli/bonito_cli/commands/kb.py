"""Knowledge Base management commands."""

from __future__ import annotations

import json as _json
from typing import Optional
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm

from ..api import api, APIError
from ..utils.auth import ensure_authenticated
from ..utils.display import (
    get_output_format,
    print_dict_as_table,
    print_error,
    print_info,
    print_success,
    print_table,
    print_warning,
)

console = Console()
app = typer.Typer(help="📚 Knowledge Base management")

# Knowledge Base API endpoints are at /api/knowledge-bases
_KB = "/knowledge-bases"


# ── list ──────────────────────────────────────────────────────

@app.command("list")
def list_knowledge_bases(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all knowledge bases for your organization."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching knowledge bases…[/cyan]"):
            kb_list = api.get(_KB)

        if not kb_list:
            print_info("No knowledge bases found. Create one with 'bonito kb create'.")
            return

        if fmt == "json":
            console.print_json(_json.dumps(kb_list, default=str))
        else:
            # Format as table
            rows = []
            for kb in kb_list:
                status_color = {
                    "ready": "green",
                    "syncing": "yellow", 
                    "pending": "blue",
                    "error": "red"
                }.get(kb.get("status", "unknown"), "white")
                
                rows.append({
                    "ID": kb["id"][:8] + "...",
                    "Name": kb["name"],
                    "Source": kb["source_type"],
                    "Status": f"[{status_color}]{kb['status']}[/{status_color}]",
                    "Documents": str(kb["document_count"]),
                    "Chunks": str(kb["chunk_count"]),
                    "Last Sync": kb["last_synced_at"][:10] if kb["last_synced_at"] else "Never"
                })

            print_table(rows, title="📚 Knowledge Bases")

    except APIError as e:
        print_error(f"Failed to list knowledge bases: {e}")
        raise typer.Exit(1)


# ── create ────────────────────────────────────────────────────

@app.command("create")
def create_knowledge_base(
    name: str = typer.Argument(..., help="Knowledge base name"),
    source: str = typer.Option("upload", "--source", help="Source type: upload, s3, azure_blob, gcs"),
    bucket: Optional[str] = typer.Option(None, "--bucket", help="S3 bucket or Azure container or GCS bucket name"),
    prefix: Optional[str] = typer.Option(None, "--prefix", help="Path prefix within the bucket/container"),
    region: Optional[str] = typer.Option(None, "--region", help="Cloud region (for S3)"),
    account: Optional[str] = typer.Option(None, "--account", help="Storage account name (for Azure Blob)"),
    description: Optional[str] = typer.Option(None, "--description", help="Knowledge base description"),
    chunk_size: int = typer.Option(512, "--chunk-size", help="Chunk size in tokens"),
    chunk_overlap: int = typer.Option(50, "--chunk-overlap", help="Chunk overlap in tokens"),
    embedding_model: str = typer.Option("auto", "--embedding-model", help="Embedding model (auto = cheapest)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Create a new knowledge base."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    # Build source config based on source type
    source_config = {}
    if source == "s3":
        if not bucket:
            print_error("--bucket is required for S3 source")
            raise typer.Exit(1)
        source_config = {"bucket": bucket}
        if prefix:
            source_config["prefix"] = prefix
        if region:
            source_config["region"] = region

    elif source == "azure_blob":
        if not bucket:
            print_error("--bucket (container name) is required for Azure Blob source")
            raise typer.Exit(1)
        source_config = {"container": bucket}
        if prefix:
            source_config["prefix"] = prefix
        if account:
            source_config["account"] = account

    elif source == "gcs":
        if not bucket:
            print_error("--bucket is required for GCS source")
            raise typer.Exit(1)
        source_config = {"bucket": bucket}
        if prefix:
            source_config["prefix"] = prefix

    elif source == "upload":
        source_config = {}  # No config needed for direct upload

    else:
        print_error(f"Unsupported source type: {source}. Use: upload, s3, azure_blob, gcs")
        raise typer.Exit(1)

    # Prepare request body
    kb_data = {
        "name": name,
        "source_type": source,
        "source_config": source_config,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "embedding_model": embedding_model,
    }
    if description:
        kb_data["description"] = description

    try:
        with console.status(f"[cyan]Creating knowledge base '{name}'…[/cyan]"):
            kb = api.post(_KB, json=kb_data)

        if fmt == "json":
            console.print_json(_json.dumps(kb, default=str))
        else:
            print_success(f"✓ Created knowledge base '{kb['name']}' (ID: {kb['id'][:8]}...)")
            print_info(f"  Source: {kb['source_type']}")
            print_info(f"  Status: {kb['status']}")
            
            if source != "upload":
                print_info("\nNext steps:")
                print_info("  1. Ensure your cloud credentials allow Bonito to read from the source")
                print_info("  2. Run 'bonito kb sync <kb-id>' to index documents")
            else:
                print_info("\nNext steps:")
                print_info("  1. Upload documents with 'bonito kb upload <kb-id> <file>'")

    except APIError as e:
        print_error(f"Failed to create knowledge base: {e}")
        raise typer.Exit(1)


# ── info ──────────────────────────────────────────────────────

@app.command("info")
def get_knowledge_base_info(
    kb_id: str = typer.Argument(..., help="Knowledge base ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Get detailed information about a knowledge base."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status(f"[cyan]Fetching knowledge base info…[/cyan]"):
            kb = api.get(f"{_KB}/{kb_id}")

        if fmt == "json":
            console.print_json(_json.dumps(kb, default=str))
        else:
            print_dict_as_table({
                "ID": kb["id"],
                "Name": kb["name"],
                "Description": kb.get("description") or "None",
                "Source Type": kb["source_type"],
                "Source Config": _json.dumps(kb["source_config"], indent=2),
                "Status": kb["status"],
                "Documents": kb["document_count"],
                "Chunks": kb["chunk_count"],
                "Total Tokens": f"{kb['total_tokens']:,}",
                "Embedding Model": kb["embedding_model"],
                "Embedding Dimensions": kb["embedding_dimensions"],
                "Chunk Size": f"{kb['chunk_size']} tokens",
                "Chunk Overlap": f"{kb['chunk_overlap']} tokens",
                "Last Synced": kb["last_synced_at"] or "Never",
                "Created": kb["created_at"][:19].replace("T", " "),
                "Updated": kb["updated_at"][:19].replace("T", " "),
            }, title=f"📚 Knowledge Base: {kb['name']}")

    except APIError as e:
        print_error(f"Failed to get knowledge base info: {e}")
        raise typer.Exit(1)


# ── delete ────────────────────────────────────────────────────

@app.command("delete")
def delete_knowledge_base(
    kb_id: str = typer.Argument(..., help="Knowledge base ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete a knowledge base and all its documents."""
    ensure_authenticated()

    try:
        # Get KB info first
        kb = api.get(f"{_KB}/{kb_id}")
        kb_name = kb["name"]
        
        if not yes:
            console.print(f"\n[red]⚠️  This will permanently delete knowledge base '{kb_name}' and all its documents![/red]")
            if not Confirm.ask("Are you sure?"):
                print_info("Cancelled.")
                return

        with console.status(f"[red]Deleting knowledge base '{kb_name}'…[/red]"):
            api.delete(f"{_KB}/{kb_id}")

        print_success(f"✓ Deleted knowledge base '{kb_name}'")

    except APIError as e:
        print_error(f"Failed to delete knowledge base: {e}")
        raise typer.Exit(1)


# ── docs ──────────────────────────────────────────────────────

@app.command("docs")
def list_documents(
    kb_id: str = typer.Argument(..., help="Knowledge base ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List documents in a knowledge base."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status(f"[cyan]Fetching documents…[/cyan]"):
            docs = api.get(f"{_KB}/{kb_id}/documents")

        if not docs:
            print_info("No documents found in this knowledge base.")
            return

        if fmt == "json":
            console.print_json(_json.dumps(docs, default=str))
        else:
            rows = []
            for doc in docs:
                status_color = {
                    "ready": "green",
                    "processing": "yellow",
                    "pending": "blue",
                    "error": "red"
                }.get(doc.get("status", "unknown"), "white")
                
                file_size = ""
                if doc.get("file_size"):
                    size = doc["file_size"]
                    if size < 1024:
                        file_size = f"{size} B"
                    elif size < 1024 * 1024:
                        file_size = f"{size // 1024} KB"
                    else:
                        file_size = f"{size // (1024 * 1024)} MB"

                rows.append({
                    "ID": doc["id"][:8] + "...",
                    "Name": doc["file_name"],
                    "Type": doc.get("file_type", "").upper() or "Unknown",
                    "Size": file_size,
                    "Status": f"[{status_color}]{doc['status']}[/{status_color}]",
                    "Chunks": str(doc["chunk_count"]),
                    "Created": doc["created_at"][:10]
                })

            print_table(rows, title="📄 Documents")

    except APIError as e:
        print_error(f"Failed to list documents: {e}")
        raise typer.Exit(1)


# ── upload ────────────────────────────────────────────────────

@app.command("upload")
def upload_document(
    kb_id: str = typer.Argument(..., help="Knowledge base ID"),
    file_path: str = typer.Argument(..., help="File or directory path to upload"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Upload a document to a knowledge base."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    path = Path(file_path)
    
    if not path.exists():
        print_error(f"File or directory not found: {file_path}")
        raise typer.Exit(1)

    # Collect files to upload
    files_to_upload = []
    if path.is_file():
        files_to_upload.append(path)
    elif path.is_dir():
        # Find supported file types in directory
        supported_extensions = {".pdf", ".docx", ".txt", ".md", ".html", ".csv", ".json"}
        for file in path.rglob("*"):
            if file.is_file() and file.suffix.lower() in supported_extensions:
                files_to_upload.append(file)
    
    if not files_to_upload:
        print_error("No supported files found to upload.")
        print_info("Supported formats: PDF, DOCX, TXT, MD, HTML, CSV, JSON")
        raise typer.Exit(1)

    print_info(f"Found {len(files_to_upload)} file(s) to upload.")
    
    # Upload each file
    results = []
    for file_path in files_to_upload:
        try:
            with console.status(f"[cyan]Uploading {file_path.name}…[/cyan]"):
                with open(file_path, "rb") as f:
                    files = {"file": (file_path.name, f, "application/octet-stream")}
                    result = api.post(f"{_KB}/{kb_id}/documents", files=files)
                    results.append(result)
            
            if fmt != "json":
                status_color = "green" if result["status"] == "ready" else "yellow"
                print_success(f"✓ Uploaded {file_path.name} ([{status_color}]{result['status']}[/{status_color}])")

        except APIError as e:
            print_error(f"Failed to upload {file_path.name}: {e}")
            results.append({"error": str(e), "file": file_path.name})

    if fmt == "json":
        console.print_json(_json.dumps(results, default=str))
    else:
        successful = len([r for r in results if "error" not in r])
        print_info(f"\nUploaded {successful}/{len(files_to_upload)} files successfully.")


# ── sync ──────────────────────────────────────────────────────

@app.command("sync")
def sync_knowledge_base(
    kb_id: str = typer.Argument(..., help="Knowledge base ID"),
    force: bool = typer.Option(False, "--force", help="Force sync even if already in progress"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Trigger sync from cloud storage."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        sync_data = {"force": force}
        
        with console.status(f"[cyan]Starting sync…[/cyan]"):
            result = api.post(f"{_KB}/{kb_id}/sync", json=sync_data)

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            print_success("✓ Sync started successfully")
            print_info(f"Status: {result['status']}")
            print_info("Check sync progress with 'bonito kb info <kb-id>'")

    except APIError as e:
        print_error(f"Failed to start sync: {e}")
        raise typer.Exit(1)


# ── search ────────────────────────────────────────────────────

@app.command("search")
def search_knowledge_base(
    kb_id: str = typer.Argument(..., help="Knowledge base ID"),
    query: str = typer.Argument(..., help="Search query"),
    top_k: int = typer.Option(5, "--top-k", help="Number of results to return"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Search for relevant chunks in a knowledge base."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        search_data = {
            "query": query,
            "top_k": top_k
        }
        
        with console.status(f"[cyan]Searching knowledge base…[/cyan]"):
            result = api.post(f"{_KB}/{kb_id}/search", json=search_data)

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            print_info(f"Query: {result['query']}")
            print_info(f"Search time: {result['search_time_ms']}ms")
            print_info(f"Results: {result['total_results']}")
            
            if result["results"]:
                console.print()
                for i, chunk in enumerate(result["results"], 1):
                    score_color = "green" if chunk["score"] > 0.8 else "yellow" if chunk["score"] > 0.6 else "red"
                    console.print(f"[bold]Result {i}[/bold] (score: [{score_color}]{chunk['score']:.3f}[/{score_color}])")
                    
                    source_info = chunk.get("source_file", "Unknown file")
                    if chunk.get("source_page"):
                        source_info += f", page {chunk['source_page']}"
                    console.print(f"[dim]Source: {source_info}[/dim]")
                    
                    # Show first 200 characters of content
                    content = chunk["content"]
                    if len(content) > 200:
                        content = content[:200] + "..."
                    console.print(f"[italic]{content}[/italic]")
                    console.print()
            else:
                print_info("No results found.")

    except APIError as e:
        print_error(f"Failed to search knowledge base: {e}")
        raise typer.Exit(1)