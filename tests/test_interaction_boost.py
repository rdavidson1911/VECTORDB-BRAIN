"""Unit tests for Layer 2 interaction boosts and score fusion."""

from __future__ import annotations

from pathlib import Path

from omnikb.adapters.interaction_store import InteractionStore, boost_norm
from omnikb.domain.memory_tier import assign_memory_tier, boost_allowed
from omnikb.services.interaction_service import InteractionService


def test_assign_memory_tier_paths() -> None:
    assert assign_memory_tier("curated/seed.md", "md") == "curated_note"
    assert assign_memory_tier("curated/ref.pdf", "pdf") == "reference_pdf"
    assert assign_memory_tier("_samples/sample-note.md", "md") == "samples"
    assert assign_memory_tier("staging/devdocs/x.md", "md") == "staging"
    assert assign_memory_tier("sample-note.md", "md") == "samples"


def test_boost_allowed_by_tier() -> None:
    assert boost_allowed("samples", "query_impression") is False
    assert boost_allowed("reference_pdf", "query_impression") is False
    assert boost_allowed("reference_pdf", "result_click") is True
    assert boost_allowed("curated_note", "query_impression") is True


def test_boost_norm_monotonic() -> None:
    assert boost_norm(0, 10) == 0.0
    assert boost_norm(1, 10) < boost_norm(5, 10)
    assert boost_norm(10, 10) == 1.0


def test_interaction_store_and_fusion(tmp_path: Path) -> None:
    store = InteractionStore(tmp_path / "interactions.db")
    svc = InteractionService(store)
    svc.record_events(
        session_id="s1",
        events=[
            {
                "event_type": "query_impression",
                "point_id": "p1",
                "memory_tier": "curated_note",
                "query_text_hash": None,
                "ts": None,
            },
            {
                "event_type": "result_click",
                "point_id": "p1",
                "memory_tier": "curated_note",
                "query_text_hash": None,
                "ts": None,
            },
            {
                "event_type": "query_impression",
                "point_id": "p2",
                "memory_tier": "samples",
                "query_text_hash": None,
                "ts": None,
            },
        ],
    )
    boosts = store.get_boosts(["p1", "p2"])
    assert "p1" in boosts
    assert boosts["p1"].hit_count > 0
    assert "p2" not in boosts  # samples never boost

    matches = [
        {"id": "p1", "score": 0.8, "payload": {"source_path": "curated/a.md"}},
        {"id": "p2", "score": 0.9, "payload": {"source_path": "_samples/x.md"}},
    ]
    layer1, layer2 = svc.fuse_matches(matches, boost_weight=0.25)
    assert len(layer1) == 2
    p1_l2 = next(m for m in layer2 if m["id"] == "p1")
    assert float(p1_l2["boost_norm"]) > 0
    assert float(p1_l2["score"]) != 0.8
