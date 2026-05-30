from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from pypdf import PdfReader

from omnikb.domain.models import SourceDocument

SUPPORTED_SUFFIXES = {".md", ".txt", ".pdf"}


def discover_files(root_path: str, recursive: bool = True) -> list[Path]:
    root = Path(root_path)
    if not root.exists():
        raise FileNotFoundError(f"Source path does not exist: {root_path}")
    if root.is_file():
        return [root] if root.suffix.lower() in SUPPORTED_SUFFIXES else []

    iterator = root.rglob("*") if recursive else root.glob("*")
    return [
        path for path in iterator if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    ]


def load_document(path: Path) -> SourceDocument:
    resolved = path.resolve()
    stat = resolved.stat()
    text = _read_text(path)
    digest = sha256(text.encode("utf-8")).hexdigest()
    mtime = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
    return SourceDocument(
        source_path=resolved.as_posix(),
        text=text,
        content_hash=digest,
        updated_at=mtime,
        source_size_bytes=int(stat.st_size),
    )


def _read_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".md":
        from omnikb.curation.frontmatter import frontmatter_body

        return frontmatter_body(path)
    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join([(page.extract_text() or "") for page in reader.pages])
    raise ValueError(f"Unsupported file type: {suffix}")
