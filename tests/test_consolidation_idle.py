"""Idle gate for consolidation → dreaming (ADR 0002)."""

from __future__ import annotations

import time
from pathlib import Path

from omnikb.adapters.interaction_store import InteractionStore
from omnikb.consolidation.trigger import ConsolidationTriggerService
from omnikb.services.dreaming_service import DreamingService
from omnikb.services.interaction_service import InteractionService


class _FakeQdrant:
    def retrieve_vectors(self, point_ids: list[str]) -> dict[str, list[float]]:
        return {pid: [1.0, 0.0] for pid in point_ids}


def test_idle_reason_skips_when_recent_events(tmp_path: Path) -> None:
    store = InteractionStore(tmp_path / "idle.db")
    interactions = InteractionService(store)
    interactions.record_events(
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
        store=_FakeQdrant(),
        interaction_store=store,
        idle_minutes=60.0,
        edge_min_score=0.5,
    )
    consolidation = ConsolidationTriggerService(
        enabled=True,
        dreaming_runner=dreaming.run,
        force_dreaming=False,
    )
    job = consolidation.submit_run(dry_run=False, reason="idle")
    for _ in range(50):
        current = consolidation.get_job(job.job_id)
        assert current is not None
        if current.status in ("completed", "failed"):
            assert current.status == "completed"
            assert current.message is not None
            assert "not_idle" in current.message
            break
        time.sleep(0.02)
    else:
        raise AssertionError("job did not complete")
