from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class SourceDocument:
    """Loaded document; ``updated_at`` is the source file mtime (UTC)."""

    source_path: str
    text: str
    content_hash: str
    updated_at: datetime
    source_size_bytes: int = 0


@dataclass(slots=True)
class Chunk:
    document_id: str
    chunk_index: int
    text: str
    source_path: str
    content_hash: str
