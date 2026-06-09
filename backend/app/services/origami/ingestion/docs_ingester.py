"""
Ingests internal markdown docs that describe the Bonito platform.

Splits each doc on top-level `## ` headings, then further splits any chunk
that exceeds the soft token target. Returns one `IngestionRecord` per chunk.

Working end-to-end against the actual repo state. The token-count proxy is
intentionally cheap (`words * 1.3`) — Phase 1 can swap in a real tokenizer
once we know which embedding model we're standardizing on.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Iterable

from .models import IngestionRecord, SourceType

logger = logging.getLogger(__name__)

# Repo root, resolved from this file's location. This module lives at
# backend/app/services/origami/ingestion/docs_ingester.py — so 5 parents up.
_REPO_ROOT = Path(__file__).resolve().parents[5]

# Files we always pull in (relative to repo root). Missing files are skipped
# with a warning rather than blowing up the whole pipeline.
PRIMARY_DOCS: tuple[str, ...] = (
    "CLAUDE.md",
    "ARCHITECTURAL_PATTERNS.md",
    "docs/BONOBOT-ARCHITECTURE.md",
    "docs/ORIGAMI-MVP-PLAN.md",
)

# All docs/*.md beyond the curated primaries also get ingested. We exclude
# anything that looks like a one-off scratch / report so the KB stays focused.
_EXCLUDED_DOC_PATTERNS: tuple[str, ...] = (
    "playwright-report",
)

# Soft target — chunks larger than this get split further. ~1500 tokens leaves
# headroom inside an 8k embedding window even for the title + prefix.
SOFT_TOKEN_TARGET = 1500


def _estimate_tokens(text: str) -> int:
    """
    Cheap token-count proxy.

    1 word ~= 1.3 tokens is reasonable for English prose. Phase 1 should
    replace this with the embedding model's actual tokenizer.
    """
    # TODO: swap for tiktoken / the gateway's chosen embedding tokenizer once
    # the embedding model for `bonito-knowledge` is locked in.
    return int(len(text.split()) * 1.3)


def _split_on_h2(markdown: str) -> list[tuple[str, str]]:
    """
    Split markdown on top-level `## ` headings.

    Returns a list of `(heading, body)` tuples. The body INCLUDES any nested
    h3/h4/etc. Content before the first `##` is returned with heading `""`.
    """
    # Split on lines that begin with exactly `## ` (not `###`, etc.)
    parts = re.split(r"(?m)^##[ \t]+(.+)$", markdown)
    if len(parts) == 1:
        # No h2 headings — single chunk
        return [("", markdown.strip())]

    out: list[tuple[str, str]] = []
    preamble = parts[0].strip()
    if preamble:
        out.append(("", preamble))

    # parts after split: [preamble, h1, body1, h2, body2, ...]
    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        body = parts[i + 1].strip() if (i + 1) < len(parts) else ""
        if body or heading:
            out.append((heading, body))
    return out


def _split_oversized_chunk(
    heading: str, body: str, target: int = SOFT_TOKEN_TARGET
) -> list[tuple[str, str]]:
    """
    If a single h2 section is too big, split it further on paragraph breaks.

    Each sub-chunk carries the same heading so context is preserved. Returns
    `[(heading, sub_body), ...]`.
    """
    if _estimate_tokens(body) <= target:
        return [(heading, body)]

    paragraphs = re.split(r"\n\s*\n", body)
    chunks: list[tuple[str, str]] = []
    current: list[str] = []
    current_tokens = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        para_tokens = _estimate_tokens(para)
        if current and current_tokens + para_tokens > target:
            chunks.append((heading, "\n\n".join(current)))
            current = [para]
            current_tokens = para_tokens
        else:
            current.append(para)
            current_tokens += para_tokens

    if current:
        chunks.append((heading, "\n\n".join(current)))
    return chunks


def _doc_title(rel_path: str, markdown: str) -> str:
    """Use the first h1 if present, else the filename."""
    m = re.search(r"(?m)^#[ \t]+(.+)$", markdown)
    if m:
        return m.group(1).strip()
    return Path(rel_path).stem


def _discover_doc_paths(
    repo_root: Path,
    primary: Iterable[str] = PRIMARY_DOCS,
) -> list[Path]:
    """
    Resolve PRIMARY_DOCS + every `docs/*.md` (deduped, ordered).

    Missing primary docs are skipped with a warning — not fatal.
    """
    seen: set[Path] = set()
    ordered: list[Path] = []

    for rel in primary:
        path = (repo_root / rel).resolve()
        if not path.exists():
            logger.warning("Primary doc not found, skipping: %s", rel)
            continue
        if path not in seen:
            seen.add(path)
            ordered.append(path)

    docs_dir = repo_root / "docs"
    if docs_dir.is_dir():
        for path in sorted(docs_dir.glob("*.md")):
            if any(pat in str(path) for pat in _EXCLUDED_DOC_PATTERNS):
                continue
            if path not in seen:
                seen.add(path)
                ordered.append(path)

    return ordered


def ingest_docs(
    repo_root: Path | str | None = None,
    primary_docs: Iterable[str] = PRIMARY_DOCS,
) -> list[IngestionRecord]:
    """
    Read all known internal docs, chunk on h2 headings, return records.

    Args:
        repo_root: Override the auto-detected repo root (useful for tests).
        primary_docs: Iterable of repo-relative doc paths to force-include.

    Returns:
        List of `IngestionRecord` ready for embedding + KB insert.
    """
    root = Path(repo_root).resolve() if repo_root else _REPO_ROOT
    paths = _discover_doc_paths(root, primary_docs)
    records: list[IngestionRecord] = []

    for path in paths:
        try:
            markdown = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("Failed reading %s: %s", path, exc)
            continue

        rel_path = path.relative_to(root).as_posix()
        doc_title = _doc_title(rel_path, markdown)
        sections = _split_on_h2(markdown)

        # Flatten: split any oversized section, then enumerate globally so
        # chunk_index is unique within the doc.
        flattened: list[tuple[str, str]] = []
        for heading, body in sections:
            flattened.extend(_split_oversized_chunk(heading, body))

        total = len(flattened)
        for idx, (heading, body) in enumerate(flattened):
            if not body.strip():
                continue
            title = f"{doc_title} — {heading}" if heading else doc_title
            records.append(
                IngestionRecord(
                    source_type=SourceType.DOC,
                    source_path=rel_path,
                    title=title,
                    content=body,
                    metadata={
                        "heading": heading or None,
                        "chunk_index": idx,
                        "total_chunks": total,
                        "token_estimate": _estimate_tokens(body),
                        "doc_title": doc_title,
                    },
                )
            )

    logger.info(
        "Doc ingest produced %d records from %d files", len(records), len(paths)
    )
    return records


__all__ = ["ingest_docs", "PRIMARY_DOCS", "SOFT_TOKEN_TARGET"]
