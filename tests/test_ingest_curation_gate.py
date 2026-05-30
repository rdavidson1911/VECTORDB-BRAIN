from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from omnikb.adapters.document_loader import load_document
from omnikb.curation.exceptions import CurationGateError
from omnikb.curation.validate import CurationPolicy, validate_corpus
from omnikb.services.ingestion_service import IngestionService

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "curation"


class _SkipFakeStore:
    def __init__(self) -> None:
        self.upserts: list[list] = []

    def ensure_collection(self, vector_size: int) -> None:
        _ = vector_size

    def delete_by_source_path(self, source_path: str) -> None:
        _ = source_path

    def count_points(self, must: list) -> int:  # noqa: ANN001
        return 0

    def upsert(self, records: list) -> None:
        self.upserts.append(records)


class _FakeEmbedder:
    dimensions = 4

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]


def _service(
    tmp_path: Path, *, gate: bool = True, allow_override: bool = False
) -> IngestionService:
    return IngestionService(
        store=_SkipFakeStore(),  # type: ignore[arg-type]
        embedder=_FakeEmbedder(),  # type: ignore[arg-type]
        chunk_size=120,
        chunk_overlap=10,
        data_sources_path=str(tmp_path),
        curation_policy=CurationPolicy(gate_enabled=gate),
        curation_allow_override=allow_override,
    )


def test_ingest_blocks_curated_file_missing_frontmatter(tmp_path: Path) -> None:
    curated = tmp_path / "curated"
    curated.mkdir()
    shutil.copy(FIXTURES / "missing_frontmatter.md", curated / "missing_frontmatter.md")
    svc = _service(tmp_path)
    with pytest.raises(CurationGateError) as exc_info:
        svc.ingest_path(str(curated), recursive=False)
    assert any(i.code == "missing_frontmatter" for i in exc_info.value.issues)


def test_ingest_allows_curated_valid_note(tmp_path: Path) -> None:
    curated = tmp_path / "curated"
    curated.mkdir()
    shutil.copy(FIXTURES / "valid_curated_note.md", curated / "valid_curated_note.md")
    svc = _service(tmp_path)
    result = svc.ingest_path(str(curated), recursive=False)
    assert result.chunks_indexed > 0


def test_ingest_override_bypasses_gate_when_enabled(tmp_path: Path) -> None:
    curated = tmp_path / "curated"
    curated.mkdir()
    shutil.copy(FIXTURES / "missing_frontmatter.md", curated / "missing_frontmatter.md")
    svc = _service(tmp_path, allow_override=True)
    result = svc.ingest_path(str(curated), recursive=False, allow_quality_override=True)
    assert result.files_seen == 1


def test_ingest_root_md_not_subject_to_frontmatter_gate(tmp_path: Path) -> None:
    note = tmp_path / "plain.md"
    note.write_text("# hello\n\nno frontmatter required at corpus root.\n", encoding="utf-8")
    svc = _service(tmp_path)
    result = svc.ingest_path(str(tmp_path), recursive=False)
    assert result.chunks_indexed > 0


def test_load_document_strips_yaml_from_indexed_text(tmp_path: Path) -> None:
    path = tmp_path / "curated.md"
    path.write_text(
        "---\nkb_ingest: true\nsummary: meta\n---\n\nIndexed body only.\n",
        encoding="utf-8",
    )
    doc = load_document(path)
    assert "kb_ingest" not in doc.text
    assert "Indexed body only." in doc.text


def test_gate_scoping_staging_md_skips_frontmatter(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "draft.md").write_text("no frontmatter\n", encoding="utf-8")
    report = validate_corpus(tmp_path, policy=CurationPolicy())
    assert not any(i.code == "missing_frontmatter" for i in report.issues)


def test_valid_curated_note_passes_full_corpus_validate(tmp_path: Path) -> None:
    curated = tmp_path / "curated"
    curated.mkdir()
    shutil.copy(FIXTURES / "valid_curated_note.md", curated / "valid_curated_note.md")
    report = validate_corpus(tmp_path, policy=CurationPolicy())
    errors = [i for i in report.issues if i.severity == "error"]
    assert errors == []


def test_empty_body_curated_note_errors(tmp_path: Path) -> None:
    curated = tmp_path / "curated"
    curated.mkdir()
    (curated / "empty.md").write_text(
        "---\nkb_ingest: true\nnote_finalized: true\nkb_status: curated\n"
        "summary: x\nkb_reviewed_at: 2026-05-29\n---\n\n   \n",
        encoding="utf-8",
    )
    report = validate_corpus(tmp_path, policy=CurationPolicy())
    assert any(i.code == "empty_content" for i in report.issues)


@pytest.mark.parametrize(
    "secret_line",
    [
        "AKIAIOSFODNN7EXAMPLE",
        "ghp_123456789012345678901234567890123456",
        "password=hunter2",
    ],
)
def test_secret_patterns_in_body(tmp_path: Path, secret_line: str) -> None:
    curated = tmp_path / "curated"
    curated.mkdir()
    (curated / "bad.md").write_text(
        "---\nkb_ingest: true\nnote_finalized: true\nkb_status: curated\n"
        "summary: s\nkb_reviewed_at: 2026-05-29\n---\n\n"
        f"leak: {secret_line}\n",
        encoding="utf-8",
    )
    report = validate_corpus(tmp_path, policy=CurationPolicy())
    assert any(i.code == "secret_pattern" for i in report.issues)


def test_secret_in_frontmatter_detected(tmp_path: Path) -> None:
    curated = tmp_path / "curated"
    curated.mkdir()
    (curated / "fm_secret.md").write_text(
        "---\nkb_ingest: true\nnote_finalized: true\nkb_status: curated\n"
        "summary: s\nkb_reviewed_at: 2026-05-29\n"
        "api_key = sk-abcdefghijklmnopqrstuvwxyz\n---\n\nClean body.\n",
        encoding="utf-8",
    )
    report = validate_corpus(tmp_path, policy=CurationPolicy())
    assert any(i.code == "secret_pattern" for i in report.issues)
