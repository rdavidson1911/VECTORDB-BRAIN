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
from omnikb.curation.validate import (
    CurationPolicy,
    assert_curation_gate,
    validate_corpus,
    validate_ingest_files,
)
from omnikb.domain.chunking import ChunkingConfig, chunk_text
from omnikb.domain.path_safety import assert_ingest_file_target, resolve_ingest_path


@dataclass(slots=True)
class IngestionResult:
    files_seen: int
    files_indexed: int
    chunks_indexed: int
    files_skipped: int = 0
    resolved_path: str | None = None


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
        data_sources_path: str = "/data/sources",
        host_data_sources_path: str | None = None,
        curation_policy: CurationPolicy | None = None,
        curation_allow_override: bool = False,
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunk_strategy = chunk_strategy
        self.embedding_model = embedding_model
        self.pipeline_version = pipeline_version
        self.normalization_profile = normalization_profile
        self.data_sources_path = data_sources_path
        self.host_data_sources_path = host_data_sources_path or None
        self.curation_policy = curation_policy if curation_policy is not None else CurationPolicy()
        self.curation_allow_override = curation_allow_override
        self.chunking_config = ChunkingConfig(
            strategy=chunk_strategy, chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

    def _resolve_user_path(self, path: str) -> Path:
        return resolve_ingest_path(
            path,
            allowed_root=Path(self.data_sources_path),
            host_sources_root=self.host_data_sources_path,
        )

    def ingest_file(
        self, path: str, *, skip_unchanged: bool = False, allow_quality_override: bool = False
    ) -> IngestionResult:
        """Index a single file under the configured sources root."""
        resolved = self._resolve_user_path(path)
        assert_ingest_file_target(resolved)
        self._run_curation_gate([resolved], allow_quality_override=allow_quality_override)
        self.store.ensure_collection(self.embedder.dimensions)
        outcome = self._ingest_single(resolved, skip_unchanged=skip_unchanged)
        resolved_posix = resolved.as_posix()
        if outcome == "skipped":
            return IngestionResult(
                files_seen=1,
                files_indexed=0,
                chunks_indexed=0,
                files_skipped=1,
                resolved_path=resolved_posix,
            )
        chunks = int(outcome) if isinstance(outcome, int) else 0
        return IngestionResult(
            files_seen=1,
            files_indexed=1 if chunks > 0 else 0,
            chunks_indexed=chunks,
            files_skipped=0,
            resolved_path=resolved_posix,
        )

    def ingest_path(
        self,
        path: str,
        recursive: bool = True,
        *,
        skip_unchanged: bool = False,
        allow_quality_override: bool = False,
    ) -> IngestionResult:
        resolved = self._resolve_user_path(path)
        self._run_curation_gate_for_tree(resolved, recursive, allow_quality_override)
        files = discover_files(str(resolved), recursive=recursive)
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
        resolved = self._resolve_user_path(path)
        files = discover_files(str(resolved), recursive=recursive)
        return self.build_previews_for_files(files[:limit_files])

    def _corpus_root(self) -> Path:
        return Path(self.data_sources_path)

    def _run_curation_gate_for_tree(
        self, scan_root: Path, recursive: bool, allow_quality_override: bool
    ) -> None:
        if not self.curation_policy.gate_enabled:
            return
        if scan_root.is_file():
            report = validate_ingest_files(
                [scan_root],
                corpus_root=self._corpus_root(),
                policy=self.curation_policy,
            )
        else:
            report = validate_corpus(
                scan_root,
                recursive=recursive,
                policy=self.curation_policy,
            )
        assert_curation_gate(
            report,
            allow_override=allow_quality_override,
            override_enabled=self.curation_allow_override,
        )

    def _run_curation_gate(self, files: list[Path], *, allow_quality_override: bool) -> None:
        if not self.curation_policy.gate_enabled:
            return
        report = validate_ingest_files(
            files,
            corpus_root=self._corpus_root(),
            policy=self.curation_policy,
        )
        assert_curation_gate(
            report,
            allow_override=allow_quality_override,
            override_enabled=self.curation_allow_override,
        )
