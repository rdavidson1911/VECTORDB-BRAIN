from pathlib import Path

from fastapi.testclient import TestClient

from omnikb.api.routes import get_app_state
from omnikb.main import app


class _FakeStore:
    def health(self) -> bool:
        return True

    def collection_stats(self) -> dict:
        return {"status": "ok"}

    def list_sources(self) -> list[dict]:
        return [
            {
                "source_path": "/a.md",
                "file_type": "md",
                "chunk_count": 2,
                "latest_updated_at": "2026-01-01T00:00:00+00:00",
                "content_hash": "abc",
            }
        ]

    def corpus_summary(self) -> dict:
        return {
            "collection": "omnikb_documents",
            "vectors_count": 2,
            "chunks_count": 2,
            "sources_count": 1,
            "file_type_counts": {"md": 1},
        }


class _FakeIngestionService:
    last_ingest_call: dict | None = None

    def ingest_path(self, path: str, recursive: bool = True, skip_unchanged: bool = False):  # noqa: ANN001
        _FakeIngestionService.last_ingest_call = {
            "path": path,
            "recursive": recursive,
            "skip_unchanged": skip_unchanged,
        }
        return type(
            "Result",
            (),
            {"files_seen": 1, "files_indexed": 1, "chunks_indexed": 3, "files_skipped": 0},
        )()

    def build_previews_for_files(self, files: list) -> list[dict]:  # noqa: ANN001
        return [
            {
                "source_path": str(f),
                "strategy": "recursive_char_v1",
                "chunk_size": 450,
                "chunk_overlap": 60,
                "chunks": ["a"],
            }
            for f in files
        ]

    def preview_path(self, path: str, recursive: bool = True, limit_files: int = 10) -> list[dict]:
        return self.build_previews_for_files([path])


class _FakeQueryService:
    def query(self, text: str, limit: int = 5, **kwargs) -> tuple[list[dict], dict]:  # noqa: ANN003
        return (
            [{"id": "1", "score": 0.9, "payload": {"text": "match", "source_path": "/a.md"}}],
            {
                "latency_ms": 1.2,
                "returned_count": 1,
                "unique_sources": 1,
                "top_score": 0.9,
                "average_score": 0.9,
            },
        )


class _FakeSettings:
    qdrant_collection = "omnikb_documents"


class _FakeState:
    settings = _FakeSettings()
    store = _FakeStore()
    ingestion_service = _FakeIngestionService()
    query_service = _FakeQueryService()


def _override_state() -> _FakeState:
    return _FakeState()


def test_health_endpoint() -> None:
    app.dependency_overrides[get_app_state] = _override_state
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["qdrant"] == "ok"
    app.dependency_overrides.clear()


def test_query_endpoint_returns_analytics() -> None:
    app.dependency_overrides[get_app_state] = _override_state
    client = TestClient(app)
    res = client.post("/query", json={"query": "hello", "limit": 3})
    assert res.status_code == 200
    body = res.json()
    assert "analytics" in body
    assert body["analytics"]["returned_count"] == 1
    assert body["analytics"]["unique_sources"] == 1
    assert body["analytics"]["top_score"] == 0.9
    assert body["matches"][0]["source_path"] == "/a.md"
    assert body["matches"][0]["text"] == "match"
    app.dependency_overrides.clear()


def test_corpus_summary_endpoint() -> None:
    app.dependency_overrides[get_app_state] = _override_state
    client = TestClient(app)
    res = client.get("/corpus/summary")
    assert res.status_code == 200
    body = res.json()
    assert body["collection"] == "omnikb_documents"
    assert body["vectors_count"] == 2
    assert body["chunks_count"] == 2
    assert body["sources_count"] == 1
    assert body["file_type_counts"] == {"md": 1}
    app.dependency_overrides.clear()


def test_corpus_sources_endpoint() -> None:
    app.dependency_overrides[get_app_state] = _override_state
    client = TestClient(app)
    res = client.get("/corpus/sources")
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["source_path"] == "/a.md"
    assert body[0]["file_type"] == "md"
    assert body[0]["chunk_count"] == 2
    app.dependency_overrides.clear()


def test_cors_simple_request_allows_localhost_origin() -> None:
    app.dependency_overrides[get_app_state] = _override_state
    client = TestClient(app)
    res = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == "http://localhost:5173"
    app.dependency_overrides.clear()


def test_cors_preflight_for_query_endpoint() -> None:
    app.dependency_overrides[get_app_state] = _override_state
    client = TestClient(app)
    res = client.options(
        "/query",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "POST" in res.headers["access-control-allow-methods"]
    app.dependency_overrides.clear()


def test_ingest_path_passes_skip_unchanged_flag() -> None:
    app.dependency_overrides[get_app_state] = _override_state
    client = TestClient(app)
    _FakeIngestionService.last_ingest_call = None
    res = client.post(
        "/ingest/path",
        json={"path": "/data/sources", "recursive": True, "skip_unchanged": True},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["files_skipped"] == 0
    assert _FakeIngestionService.last_ingest_call == {
        "path": "/data/sources",
        "recursive": True,
        "skip_unchanged": True,
    }
    app.dependency_overrides.clear()


def test_ingest_preview_reports_files_seen_and_respects_limit(monkeypatch) -> None:  # noqa: ANN001
    app.dependency_overrides[get_app_state] = _override_state
    client = TestClient(app)

    files = [Path("/data/sources/a.md"), Path("/data/sources/b.md"), Path("/data/sources/c.md")]
    monkeypatch.setattr("omnikb.api.routes.discover_files", lambda *_args, **_kwargs: files)

    res = client.post(
        "/ingest/preview",
        json={"path": "/data/sources", "recursive": True, "limit_files": 2},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["files_seen"] == 3
    assert len(body["previews"]) == 2
    assert body["previews"][0]["source_path"].replace("\\", "/").endswith("/data/sources/a.md")
    assert body["previews"][1]["source_path"].replace("\\", "/").endswith("/data/sources/b.md")
    app.dependency_overrides.clear()
