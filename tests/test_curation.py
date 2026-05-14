from __future__ import annotations

from pathlib import Path

from omnikb.adapters.document_loader import load_document
from omnikb.curation.manifest import build_manifest_document, build_manifest_entries
from omnikb.curation.validate import validate_corpus
from omnikb.services.ingestion_service import IngestionService

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_SOURCES = ROOT / "data" / "sources"

EXPECTED_HASHES = {
    "data/sources/sample-note.md": (
        "a62f083de0e1edaa8c33887c4c5bc17bca698485a68c3d15230b6d1684ad2fe4"
    ),
    "data/sources/sample-ops.txt": (
        "721b64c31834c0d9b71949a70018b44e3c6366afa61382c8b313706e6fbe2b84"
    ),
    "data/sources/sample-rag.md": (
        "390f79b112842f10eb4ab9edd56ad4031ea4541317d16803f5566c5462403179"
    ),
}


def test_manifest_sample_hashes_match_evidence() -> None:
    doc = build_manifest_document(SAMPLE_SOURCES, relative_to=ROOT, recursive=True)
    by_path = {e["source_path"]: e for e in doc["entries"]}
    for rel, digest in EXPECTED_HASHES.items():
        assert rel in by_path, f"missing tracked sample {rel}"
        assert by_path[rel]["content_hash"].lower() == digest.lower()
        assert by_path[rel]["ingest_eligible"] is True


def test_manifest_entries_relative_paths_use_posix_slashes() -> None:
    entries = build_manifest_entries(SAMPLE_SOURCES, relative_to=ROOT, recursive=True)
    for e in entries:
        assert "\\" not in e["source_path"]


def test_load_document_uses_filesystem_mtime_and_size(tmp_path: Path) -> None:
    path = tmp_path / "note.md"
    path.write_text("hello curation", encoding="utf-8")
    doc = load_document(path)
    stat = path.stat()
    assert doc.source_size_bytes == stat.st_size
    assert abs(doc.updated_at.timestamp() - stat.st_mtime) < 0.01


def test_validate_corpus_detects_duplicate_content(tmp_path: Path) -> None:
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    body = "# Title\n\nSame unique body xyz123.\n"
    a.write_text(body, encoding="utf-8")
    b.write_text(body, encoding="utf-8")
    report = validate_corpus(tmp_path, recursive=False)
    assert report.duplicate_content_hashes
    assert any(i.code == "duplicate_content_hash" for i in report.issues)


class _SkipFakeStore:
    def __init__(self) -> None:
        self.collection_ensured = False
        self.deleted_sources: list[str] = []
        self.upserts: list[list] = []

    def ensure_collection(self, vector_size: int) -> None:
        self.collection_ensured = vector_size > 0

    def delete_by_source_path(self, source_path: str) -> None:
        self.deleted_sources.append(source_path)

    def count_points(self, must: list) -> int:  # noqa: ANN001
        if not self.upserts:
            return 0
        return len(self.upserts[-1])

    def upsert(self, records: list) -> None:
        self.upserts.append(records)


class _FakeEmbedder:
    dimensions = 4

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]


def test_ingest_skip_unchanged_skips_second_pass(tmp_path: Path) -> None:
    doc_path = tmp_path / "note.md"
    doc_path.write_text("# Hello\n\n" + ("word " * 80), encoding="utf-8")
    store = _SkipFakeStore()
    svc = IngestionService(
        store=store,  # type: ignore[arg-type]
        embedder=_FakeEmbedder(),  # type: ignore[arg-type]
        chunk_size=120,
        chunk_overlap=10,
        chunk_strategy="recursive_char_v1",
    )
    first = svc.ingest_path(str(doc_path), recursive=False, skip_unchanged=False)
    second = svc.ingest_path(str(doc_path), recursive=False, skip_unchanged=True)
    assert first.files_skipped == 0
    assert second.files_skipped == 1
    assert second.chunks_indexed == 0
    assert len(store.upserts) == 1


def test_ingestion_payload_includes_pipeline_fields(tmp_path: Path) -> None:
    doc_path = tmp_path / "x.txt"
    doc_path.write_text("one two three four five six seven eight", encoding="utf-8")
    store = _SkipFakeStore()
    svc = IngestionService(
        store=store,  # type: ignore[arg-type]
        embedder=_FakeEmbedder(),  # type: ignore[arg-type]
        chunk_size=32,
        chunk_overlap=4,
        embedding_model="test-model",
        pipeline_version="9.9.9",
        normalization_profile="test_profile",
    )
    svc.ingest_path(str(doc_path), recursive=False)
    payload = store.upserts[0][0].payload
    assert payload["embedding_model"] == "test-model"
    assert payload["pipeline_version"] == "9.9.9"
    assert payload["normalization_profile"] == "test_profile"
    assert payload["chunk_size"] == 32
    assert payload["chunk_overlap"] == 4
    assert payload["source_size_bytes"] == doc_path.stat().st_size
