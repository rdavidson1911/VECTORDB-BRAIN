"""Consolidation trigger wires DreamingService and persists relationship edges."""

from __future__ import annotations

import time
from pathlib import Path

from omnikb.adapters.interaction_store import InteractionStore
from omnikb.consolidation.trigger import ConsolidationTriggerService
from omnikb.services.dreaming_service import DreamingService
from omnikb.services.interaction_service import InteractionService


class _FakeQdrant:
    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self._vectors = vectors

    def retrieve_vectors(self, point_ids: list[str]) -> dict[str, list[float]]:
        return {pid: self._vectors[pid] for pid in point_ids if pid in self._vectors}


def test_consolidation_trigger_runs_dreaming_and_writes_edges(tmp_path: Path) -> None:
    store = InteractionStore(tmp_path / "consol-dream.db")
    interactions = InteractionService(store)
    for pid in ("a", "b"):
        interactions.record_events(
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
    dreaming = DreamingService(
        store=_FakeQdrant({"a": [1.0, 0.0], "b": [0.99, 0.1]}),
        interaction_store=store,
        idle_minutes=0.0,
        edge_min_score=0.9,
        candidate_limit=10,
    )
    consolidation = ConsolidationTriggerService(
        enabled=True,
        dreaming_runner=dreaming.run,
        force_dreaming=True,
    )
    job = consolidation.submit_run(dry_run=False, reason="manual")
    for _ in range(50):
        current = consolidation.get_job(job.job_id)
        assert current is not None
        if current.status in ("completed", "failed"):
            assert current.status == "completed"
            assert current.message is not None
            assert "dreaming" in current.message
            break
        time.sleep(0.02)
    else:
        raise AssertionError("consolidation job did not complete")

    edges = store.edges_for_points(["a", "b"])
    assert any(e.src_point_id == "a" and e.dst_point_id == "b" for e in edges)
