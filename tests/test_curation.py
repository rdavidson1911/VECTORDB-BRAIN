from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from omnikb.adapters.document_loader import load_document
from omnikb.curation.manifest import build_manifest_entries
from omnikb.curation.validate import CurationPolicy, validate_corpus, validate_frontmatter
from omnikb.services.ingestion_service import IngestionService

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_SOURCES = ROOT / "data" / "sources"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "curation"

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
    """Only hash tracked sample files (avoid scanning large local PDFs under data/sources)."""
    for rel, digest in EXPECTED_HASHES.items():
        path = ROOT / Path(*rel.split("/"))
        doc = load_document(path)
        assert doc.content_hash.lower() == digest.lower()


def test_manifest_entries_relative_paths_use_posix_slashes() -> None:
    for rel in EXPECTED_HASHES:
        path = ROOT / Path(*rel.split("/"))
        entries = build_manifest_entries(path, relative_to=ROOT, recursive=False)
        assert len(entries) == 1
        assert "\\" not in entries[0]["source_path"]
        assert entries[0]["source_path"] == rel


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
        data_sources_path=str(tmp_path),
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
        data_sources_path=str(tmp_path),
    )
    svc.ingest_path(str(doc_path), recursive=False)
    payload = store.upserts[0][0].payload
    assert payload["embedding_model"] == "test-model"
    assert payload["pipeline_version"] == "9.9.9"
    assert payload["normalization_profile"] == "test_profile"
    assert payload["chunk_size"] == 32
    assert payload["chunk_overlap"] == 4
    assert payload["source_size_bytes"] == doc_path.stat().st_size


# ---------------------------------------------------------------------------
# Frontmatter validation tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename,expected_code",
    [
        ("missing_frontmatter.md", "missing_frontmatter"),
        ("not_finalized.md", "note_not_finalized"),
        ("ai_unverified.md", "ai_unverified"),
        ("secret_in_note.md", "secret_pattern"),
    ],
)
def test_validate_frontmatter_error_code(filename: str, expected_code: str) -> None:
    path = FIXTURES / filename
    issues = validate_frontmatter(path, CurationPolicy())
    codes = [i.code for i in issues]
    assert expected_code in codes, f"Expected {expected_code!r} in {codes}"


def test_valid_curated_note_zero_errors() -> None:
    path = FIXTURES / "valid_curated_note.md"
    issues = validate_frontmatter(path, CurationPolicy())
    errors = [i for i in issues if i.severity == "error"]
    assert errors == [], f"Unexpected errors on valid note: {errors}"


def test_exempt_file_skips_frontmatter_checks(tmp_path: Path) -> None:
    curated = tmp_path / "curated"
    curated.mkdir()
    shutil.copy(FIXTURES / "sample-exempt.md", curated / "sample-exempt.md")
    report = validate_corpus(tmp_path, policy=CurationPolicy())
    fm_errors = [i for i in report.issues if i.code == "missing_frontmatter"]
    assert not fm_errors, f"Exempt file should not raise missing_frontmatter: {fm_errors}"


def test_validate_corpus_structured_issues(tmp_path: Path) -> None:
    curated = tmp_path / "curated"
    curated.mkdir()
    shutil.copy(FIXTURES / "missing_frontmatter.md", curated / "missing_frontmatter.md")
    report = validate_corpus(tmp_path, policy=CurationPolicy())
    issue = next((i for i in report.issues if i.code == "missing_frontmatter"), None)
    assert issue is not None, "Expected missing_frontmatter issue in report"
    assert issue.path is not None
    assert issue.severity == "error"
    assert issue.code == "missing_frontmatter"


def test_no_gate_disables_frontmatter_checking(tmp_path: Path) -> None:
    curated = tmp_path / "curated"
    curated.mkdir()
    shutil.copy(FIXTURES / "missing_frontmatter.md", curated / "missing_frontmatter.md")
    report = validate_corpus(tmp_path, policy=CurationPolicy(gate_enabled=False))
    assert not any(i.code == "missing_frontmatter" for i in report.issues)


def test_warning_codes_fire_on_incomplete_frontmatter(tmp_path: Path) -> None:
    note = tmp_path / "note.md"
    note.write_text(
        "---\nkb_ingest: true\nnote_finalized: true\nkb_status: curated\n---\n\nbody\n",
        encoding="utf-8",
    )
    issues = validate_frontmatter(note, CurationPolicy())
    codes = {i.code for i in issues}
    assert "missing_summary" in codes
    assert "missing_kb_reviewed_at" in codes


def test_kb_ingest_not_true_fires(tmp_path: Path) -> None:
    note = tmp_path / "note.md"
    note.write_text(
        "---\nkb_ingest: false\nnote_finalized: true\nkb_status: curated\n---\n\nbody\n",
        encoding="utf-8",
    )
    issues = validate_frontmatter(note, CurationPolicy())
    assert any(i.code == "kb_ingest_not_true" for i in issues)


def test_kb_status_not_curated_fires(tmp_path: Path) -> None:
    note = tmp_path / "note.md"
    note.write_text(
        "---\nkb_ingest: true\nnote_finalized: true\nkb_status: staging\n---\n\nbody\n",
        encoding="utf-8",
    )
    issues = validate_frontmatter(note, CurationPolicy())
    assert any(i.code == "kb_status_not_curated" for i in issues)


def test_strict_frontmatter_false_skips_all_checks(tmp_path: Path) -> None:
    note = tmp_path / "note.md"
    note.write_text("no frontmatter at all", encoding="utf-8")
    issues = validate_frontmatter(note, CurationPolicy(strict_frontmatter=False))
    assert issues == []


def test_quoted_kb_ingest_passes_frontmatter(tmp_path: Path) -> None:
    note = tmp_path / "note.md"
    note.write_text(
        '---\nkb_ingest: "true"\nnote_finalized: true\nkb_status: curated\n'
        "summary: ok\nkb_reviewed_at: 2026-05-29\n---\n\nbody\n",
        encoding="utf-8",
    )
    issues = validate_frontmatter(note, CurationPolicy())
    errors = [i for i in issues if i.severity == "error"]
    assert errors == []


def test_root_level_md_skips_frontmatter_gate(tmp_path: Path) -> None:
    (tmp_path / "orphan.md").write_text("# no yaml\n", encoding="utf-8")
    report = validate_corpus(tmp_path, policy=CurationPolicy())
    assert not any(i.code == "missing_frontmatter" for i in report.issues)
