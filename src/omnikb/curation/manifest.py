from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from omnikb.adapters.document_loader import discover_files, load_document

MANIFEST_VERSION = "1"


def build_manifest_entries(
    root: Path,
    *,
    relative_to: Path | None = None,
    recursive: bool = True,
) -> list[dict[str, Any]]:
    """Scan supported files and return manifest entry dicts (sorted by source_path)."""
    files = sorted(discover_files(str(root), recursive=recursive))
    base = relative_to or root.resolve()
    entries: list[dict[str, Any]] = []
    for path in files:
        resolved = path.resolve()
        doc = load_document(path)
        rel = str(resolved.relative_to(base)) if base else str(path)
        text_stripped = doc.text.strip()
        entries.append(
            {
                "source_path": rel.replace("\\", "/"),
                "absolute_path": str(resolved).replace("\\", "/"),
                "file_type": path.suffix.lower().lstrip("."),
                "size_bytes": doc.source_size_bytes,
                "source_mtime_iso": doc.updated_at.isoformat(),
                "content_hash": doc.content_hash,
                "char_count": len(doc.text),
                "ingest_eligible": bool(text_stripped),
            }
        )
    entries.sort(key=lambda e: e["source_path"])
    return entries


def build_manifest_document(
    root: Path,
    *,
    relative_to: Path | None = None,
    recursive: bool = True,
) -> dict[str, Any]:
    """Full manifest JSON document including metadata wrapper."""
    root_resolved = root.resolve()
    base = relative_to.resolve() if relative_to else root_resolved
    entries = build_manifest_entries(root, relative_to=base, recursive=recursive)
    return {
        "manifest_version": MANIFEST_VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "root": str(root_resolved).replace("\\", "/"),
        "entries": entries,
    }
