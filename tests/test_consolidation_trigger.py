import time

from fastapi.testclient import TestClient

from omnikb.api.routes import get_app_state
from omnikb.consolidation.trigger import ConsolidationTriggerService
from omnikb.main import app


class _FakeSettings:
    qdrant_collection = "omnikb_documents"
    ui_logging_enabled = False


_shared_consolidation = ConsolidationTriggerService(enabled=True)


class _FakeState:
    settings = _FakeSettings()
    store = None  # type: ignore[assignment]
    ingestion_service = None  # type: ignore[assignment]
    query_service = None  # type: ignore[assignment]
    consolidation_service = _shared_consolidation


def _override_state() -> _FakeState:
    return _FakeState()


def test_consolidation_run_accepted_and_status_poll() -> None:
    app.dependency_overrides[get_app_state] = _override_state
    client = TestClient(app)
    res = client.post(
        "/consolidation/run",
        json={"dry_run": True, "reason": "manual"},
    )
    assert res.status_code == 202
    body = res.json()
    assert body["status"] == "accepted"
    job_id = body["job_id"]
    assert body["accepted_at"]

    for _ in range(50):
        status_res = client.get(f"/consolidation/status/{job_id}")
        assert status_res.status_code == 200
        status_body = status_res.json()
        if status_body["status"] in ("completed", "failed"):
            assert status_body["status"] == "completed"
            assert status_body["dry_run"] is True
            assert "dry_run" in (status_body.get("message") or "")
            break
        time.sleep(0.02)
    else:
        raise AssertionError("job did not complete in time")

    app.dependency_overrides.clear()


def test_consolidation_busy_returns_409() -> None:
    busy_svc = ConsolidationTriggerService(enabled=True)
    busy_svc._flight_lock.acquire()
    busy_svc._active_job_id = "blocking"

    class _BusyState(_FakeState):
        consolidation_service = busy_svc

    app.dependency_overrides[get_app_state] = _BusyState
    client = TestClient(app)
    res = client.post("/consolidation/run", json={"dry_run": True})
    assert res.status_code == 409
    busy_svc._active_job_id = None
    busy_svc._flight_lock.release()
    app.dependency_overrides.clear()


def test_consolidation_unknown_job_404() -> None:
    app.dependency_overrides[get_app_state] = _override_state
    client = TestClient(app)
    res = client.get("/consolidation/status/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404
    app.dependency_overrides.clear()
