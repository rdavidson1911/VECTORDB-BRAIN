"""API test for POST /interactions/events (avoids loading embedder models)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from omnikb.adapters.interaction_store import InteractionStore
from omnikb.api.routes import get_app_state, router
from omnikb.consolidation.trigger import ConsolidationTriggerService
from omnikb.services.interaction_service import InteractionService


def test_interactions_events_endpoint(tmp_path: Path) -> None:
    store = InteractionStore(tmp_path / "api-interactions.db")
    interaction_service = InteractionService(store)

    settings = SimpleNamespace(
        qdrant_collection="omnikb_documents",
        ui_logging_enabled=False,
    )
    state = SimpleNamespace(
        settings=settings,
        store=None,
        ingestion_service=None,
        query_service=None,
        interaction_service=interaction_service,
        consolidation_service=ConsolidationTriggerService(enabled=True),
        dreaming_service=None,
    )

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_app_state] = lambda: state
    client = TestClient(app)
    res = client.post(
        "/interactions/events",
        json={
            "session_id": "sess-1",
            "events": [
                {
                    "event_type": "result_click",
                    "point_id": "abc",
                    "memory_tier": "curated_note",
                }
            ],
        },
    )
    assert res.status_code == 200
    assert res.json()["accepted"] == 1
    assert "abc" in store.get_boosts(["abc"])
    app.dependency_overrides.clear()
