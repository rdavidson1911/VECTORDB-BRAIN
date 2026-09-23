"""Tests for idle dreaming pairwise edges."""

from __future__ import annotations

from pathlib import Path

from omnikb.adapters.interaction_store import InteractionStore
from omnikb.services.dreaming_service import DreamingService, _cosine
from omnikb.services.interaction_service import InteractionService


class _FakeQdrant:
    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self._vectors = vectors

    def retrieve_vectors(self, point_ids: list[str]) -> dict[str, list[float]]:
        return {pid: self._vectors[pid] for pid in point_ids if pid in self._vectors}


def test_cosine_identical() -> None:
    assert abs(_cosine([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-9


def test_dreaming_writes_edges(tmp_path: Path) -> None:
    store = InteractionStore(tmp_path / "dream.db")
    svc = InteractionService(store)
    for pid in ("a", "b", "c"):
        svc.record_events(
            session_id="s",
            events=[
                {
                    "event_type": "result_click",
                    "point_id": pid,
                    "memory_tier": "curated_note",
                    "query_text_hash": None,
                    "ts": None,
                }
            ],
        )
    vectors = {
        "a": [1.0, 0.0, 0.0],
        "b": [0.99, 0.1, 0.0],
        "c": [0.0, 1.0, 0.0],
    }
    dreaming = DreamingService(
        store=_FakeQdrant(vectors),
        interaction_store=store,
        idle_minutes=0.0,
        edge_min_score=0.9,
        candidate_limit=10,
    )
    result = dreaming.run(force=True, dry_run=False)
    assert result["skipped"] is False
    assert int(result["edges_written"]) >= 1
    edges = store.edges_for_points(["a", "b", "c"])
    assert any(e.src_point_id == "a" and e.dst_point_id == "b" for e in edges)


def test_dreaming_skips_when_not_idle(tmp_path: Path) -> None:
    store = InteractionStore(tmp_path / "busy.db")
    svc = InteractionService(store)
    svc.record_events(
        session_id="s",
        events=[
            {
                "event_type": "result_click",
                "point_id": "a",
                "memory_tier": "curated_note",
                "query_text_hash": None,
                "ts": None,
            }
        ],
    )
    dreaming = DreamingService(
        store=_FakeQdrant({"a": [1.0], "b": [1.0]}),
        interaction_store=store,
        idle_minutes=60.0,
        edge_min_score=0.5,
    )
    result = dreaming.run(force=False, dry_run=False)
    assert result["skipped"] is True
    assert result["reason"] == "not_idle"
