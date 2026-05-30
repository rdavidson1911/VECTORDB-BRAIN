import json
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
        return []

    def corpus_summary(self) -> dict:
        return {
            "collection": "omnikb_documents",
            "vectors_count": 0,
            "chunks_count": 0,
            "sources_count": 0,
            "file_type_counts": {},
        }


class _FakeIngestionService:
    def ingest_path(self, path: str, recursive: bool = True, skip_unchanged: bool = False):  # noqa: ANN001
        return type(
            "R", (), {"files_seen": 0, "files_indexed": 0, "chunks_indexed": 0, "files_skipped": 0}
        )()

    def build_previews_for_files(self, files: list) -> list[dict]:  # noqa: ANN001
        return []

    def preview_path(self, path: str, recursive: bool = True, limit_files: int = 10) -> list[dict]:
        return []


class _FakeQueryService:
    def query(self, text: str, limit: int = 5, **kwargs) -> tuple[list[dict], dict]:  # noqa: ANN003
        return (
            [],
            {
                "latency_ms": 0,
                "returned_count": 0,
                "unique_sources": 0,
                "top_score": 0,
                "average_score": 0,
            },
        )


class _FakeSettings:
    qdrant_collection = "omnikb_documents"
    ui_logging_enabled = True
    request_logging_enabled = True
    logs_dir = "logs"


class _FakeState:
    settings = _FakeSettings()
    store = _FakeStore()
    ingestion_service = _FakeIngestionService()
    query_service = _FakeQueryService()


def _override_state() -> _FakeState:
    return _FakeState()


def _patch_log_settings(monkeypatch, logs_dir: str = "logs") -> _FakeSettings:  # noqa: ANN001
    settings = _FakeSettings()
    settings.logs_dir = logs_dir
    monkeypatch.setattr("omnikb.infra.file_log_writer.get_settings", lambda: settings)
    monkeypatch.setattr("omnikb.middleware.request_timing.get_settings", lambda: settings)
    return settings


def test_ui_logs_endpoint_writes_jsonl(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.chdir(tmp_path)
    _patch_log_settings(monkeypatch)
    app.dependency_overrides[get_app_state] = _override_state
    client = TestClient(app)
    payload = {
        "entries": [
            {
                "ts": "2026-05-15T12:00:00Z",
                "level": "info",
                "category": "ui",
                "event": "click",
                "message": "Search button",
                "duration_ms": 12.5,
                "correlation_id": "ui-test-1",
                "meta": {"handler": "runSearch"},
            }
        ]
    }
    res = client.post("/dev/ui-logs", json=payload)
    assert res.status_code == 200
    assert res.json()["accepted"] == 1
    log_files = list((tmp_path / "logs").glob("ui-client-*.jsonl"))
    assert len(log_files) == 1
    line = log_files[0].read_text(encoding="utf-8").strip()
    row = json.loads(line)
    assert row["event"] == "click"
    assert row["correlation_id"] == "ui-test-1"
    app.dependency_overrides.clear()


def test_health_returns_request_duration_header(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.chdir(tmp_path)
    _patch_log_settings(monkeypatch)
    app.dependency_overrides[get_app_state] = _override_state
    client = TestClient(app)
    res = client.get("/health", headers={"X-Correlation-Id": "ui-test-corr"})
    assert res.status_code == 200
    assert "x-request-duration-ms" in res.headers
    assert res.headers.get("x-correlation-id") == "ui-test-corr"
    app.dependency_overrides.clear()
