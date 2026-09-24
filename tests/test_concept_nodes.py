"""Tests for Layer 3 connected-component concept builder (pre-HDBSCAN)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from omnikb.adapters.interaction_store import InteractionStore, RelationshipEdge
from omnikb.api.routes import get_app_state, router
from omnikb.domain.concept_nodes import build_concepts_from_edges
from omnikb.services.concept_service import ConceptService
from omnikb.services.dreaming_service import SCORE_VERSION


def test_build_concepts_merges_connected_edges() -> None:
    edges = [
        RelationshipEdge("a", "b", 0.95, SCORE_VERSION, "t0"),
        RelationshipEdge("b", "c", 0.90, SCORE_VERSION, "t0"),
        RelationshipEdge("x", "y", 0.80, SCORE_VERSION, "t0"),
    ]
    concepts = build_concepts_from_edges(edges, min_component_size=2)
    assert len(concepts) == 2
    members = {c.member_point_ids for c in concepts}
    assert ("a", "b", "c") in members
    assert ("x", "y") in members
    # Deterministic ids for the same membership.
    again = build_concepts_from_edges(edges, min_component_size=2)
    assert [c.concept_id for c in concepts] == [c.concept_id for c in again]


def test_build_concepts_skips_singletons() -> None:
    edges = [RelationshipEdge("a", "b", 0.99, SCORE_VERSION, "t0")]
    concepts = build_concepts_from_edges(edges, min_component_size=3)
    assert concepts == []


def test_concept_service_and_api(tmp_path: Path) -> None:
    db = InteractionStore(tmp_path / "concepts.db")
    db.upsert_edges(
        [
            RelationshipEdge("p1", "p2", 0.93, SCORE_VERSION, "t1"),
            RelationshipEdge("p2", "p3", 0.91, SCORE_VERSION, "t1"),
        ]
    )
    svc = ConceptService(db)
    concepts = svc.list_concepts(min_component_size=2)
    assert len(concepts) == 1
    assert concepts[0].member_point_ids == ("p1", "p2", "p3")

    class _FakeSettings:
        qdrant_collection = "omnikb_documents"
        ui_logging_enabled = False

    class _Interactions:
        store = db

    class _FakeState:
        settings = _FakeSettings()
        store = None
        ingestion_service = None
        query_service = None
        consolidation_service = None
        interaction_service = _Interactions()
        dreaming_service = None
        concept_service = svc

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_app_state] = lambda: _FakeState()
    client = TestClient(app)
    res = client.get("/relations/concepts")
    assert res.status_code == 200
    body = res.json()
    assert body["edge_count"] == 2
    assert len(body["concepts"]) == 1
    assert body["concepts"][0]["builder"] == "connected_components_v1"
    app.dependency_overrides.clear()
