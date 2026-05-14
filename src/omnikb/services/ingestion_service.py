from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

from qdrant_client.models import FieldCondition, MatchValue

from omnikb.adapters.document_loader import discover_files, load_document
from omnikb.adapters.embedder import SentenceTransformerEmbedder
from omnikb.adapters.qdrant_store import QdrantStore, VectorRecord
from omnikb.domain.chunking import ChunkingConfig, chunk_text


@dataclass(slots=True)
class IngestionResult:
    files_seen: int
    files_indexed: int
    chunks_indexed: int
    files_skipped: int = 0


class IngestionService:
    def __init__(
        self,
        store: QdrantStore,
        embedder: SentenceTransformerEmbedder,
        chunk_size: int,
        chunk_overlap: int,
        chunk_strategy: str = "recursive_char_v1",
        *,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        pipeline_version: str = "0.1.0",
        normalization_profile: str = "utf8_ignore_pypdf_v1",
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunk_strategy = chunk_strategy
        self.embedding_model = embedding_model
        self.pipeline_version = pipeline_version
        self.normalization_profile = normalization_profile
        self.chunking_config = ChunkingConfig(
            strategy=chunk_strategy, chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

    def ingest_path(
        self, path: str, recursive: bool = True, *, skip_unchanged: bool = False
    ) -> IngestionResult:
        files = discover_files(path, recursive=recursive)
        total_chunks = 0
        indexed_files = 0
        skipped_files = 0
        self.store.ensure_collection(self.embedder.dimensions)

        for file_path in files:
            outcome = self._ingest_single(file_path, skip_unchanged=skip_unchanged)
            if outcome == "skipped":
                skipped_files += 1
            elif isinstance(outcome, int) and outcome > 0:
                indexed_files += 1
                total_chunks += outcome

        return IngestionResult(
            files_seen=len(files),
            files_indexed=indexed_files,
            chunks_indexed=total_chunks,
            files_skipped=skipped_files,
        )

    def _ingest_single(self, path: Path, *, skip_unchanged: bool) -> int | Literal["skipped"]:
        doc = load_document(path)
        chunks = chunk_text(doc.text, self.chunking_config)
        if not chunks:
            return 0

        if skip_unchanged and self._is_unchanged_in_store(
            doc.source_path, doc.content_hash, len(chunks)
        ):
            return "skipped"

        vectors = self.embedder.embed(chunks)
        records: list[VectorRecord] = []
        document_id = sha256(doc.source_path.encode("utf-8")).hexdigest()
        indexed_at = datetime.now(UTC)

        for idx, (chunk_value, vector) in enumerate(zip(chunks, vectors, strict=True)):
            point_id = str(uuid5(NAMESPACE_URL, f"{doc.source_path}:{doc.content_hash}:{idx}"))
            payload = {
                "document_id": document_id,
                "chunk_index": idx,
                "source_path": doc.source_path,
                "file_type": path.suffix.lower().lstrip("."),
                "content_hash": doc.content_hash,
                "source_size_bytes": doc.source_size_bytes,
                "content_preview": chunk_value[:240],
                "text": chunk_value,
                "updated_at": doc.updated_at.isoformat(),
                "updated_at_ts": doc.updated_at.timestamp(),
                "indexed_at": indexed_at.isoformat(),
                "indexed_at_ts": indexed_at.timestamp(),
                "chunk_strategy": self.chunk_strategy,
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "embedding_model": self.embedding_model,
                "pipeline_version": self.pipeline_version,
                "normalization_profile": self.normalization_profile,
            }
            records.append(VectorRecord(point_id=point_id, vector=vector, payload=payload))

        # Clear existing chunks for this document path to keep ingestion idempotent.
        self.store.delete_by_source_path(doc.source_path)
        self.store.upsert(records)
        return len(records)

    def _is_unchanged_in_store(
        self, source_path: str, content_hash: str, expected_chunks: int
    ) -> bool:
        must = [
            FieldCondition(key="source_path", match=MatchValue(value=source_path)),
            FieldCondition(key="content_hash", match=MatchValue(value=content_hash)),
            FieldCondition(key="chunk_strategy", match=MatchValue(value=self.chunk_strategy)),
            FieldCondition(key="embedding_model", match=MatchValue(value=self.embedding_model)),
            FieldCondition(key="chunk_size", match=MatchValue(value=self.chunk_size)),
            FieldCondition(key="chunk_overlap", match=MatchValue(value=self.chunk_overlap)),
            FieldCondition(key="pipeline_version", match=MatchValue(value=self.pipeline_version)),
            FieldCondition(
                key="normalization_profile",
                match=MatchValue(value=self.normalization_profile),
            ),
        ]
        return self.store.count_points(must) == expected_chunks

    def build_previews_for_files(self, files: list[Path]) -> list[dict]:
        previews: list[dict] = []
        for file_path in files:
            doc = load_document(file_path)
            chunks = chunk_text(doc.text, self.chunking_config)
            previews.append(
                {
                    "source_path": str(file_path),
                    "strategy": self.chunk_strategy,
                    "chunk_size": self.chunk_size,
                    "chunk_overlap": self.chunk_overlap,
                    "chunks": chunks[:20],
                }
            )
        return previews

    def preview_path(self, path: str, recursive: bool = True, limit_files: int = 10) -> list[dict]:
        files = discover_files(path, recursive=recursive)
        return self.build_previews_for_files(files[:limit_files])
