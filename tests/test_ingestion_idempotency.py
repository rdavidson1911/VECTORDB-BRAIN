from pathlib import Path

from omnikb.services.ingestion_service import IngestionService


class FakeStore:
    def __init__(self) -> None:
        self.collection_ensured = False
        self.deleted_sources: list[str] = []
        self.upserts: list[list] = []

    def ensure_collection(self, vector_size: int) -> None:
        self.collection_ensured = vector_size > 0

    def delete_by_source_path(self, source_path: str) -> None:
        self.deleted_sources.append(source_path)

    def count_points(self, must: list) -> int:  # noqa: ANN001
        return 0

    def upsert(self, records: list) -> None:
        self.upserts.append(records)


class FakeEmbedder:
    dimensions = 4

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]


def test_ingest_path_replaces_existing_source_vectors(tmp_path: Path) -> None:
    doc_path = tmp_path / "sample.txt"
    doc_path.write_text("one two three four five six seven eight", encoding="utf-8")

    store = FakeStore()
    svc = IngestionService(
        store=store,  # type: ignore[arg-type]
        embedder=FakeEmbedder(),  # type: ignore[arg-type]
        chunk_size=16,
        chunk_overlap=2,
        data_sources_path=str(tmp_path),
    )

    first = svc.ingest_path(str(doc_path), recursive=False)
    second = svc.ingest_path(str(doc_path), recursive=False)

    assert first.files_seen == 1 and second.files_seen == 1
    assert first.files_skipped == 0 and second.files_skipped == 0
    assert len(store.deleted_sources) == 2
    assert len(store.upserts) == 2
