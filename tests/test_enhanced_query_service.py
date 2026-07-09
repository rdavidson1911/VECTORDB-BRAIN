from __future__ import annotations

import json
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from omnikb.adapters.l2_store import L2StoreAdapter
from omnikb.services.enhanced_query_service import (
    EnhancedQueryService,
    _tokenize,
    bm25_scores,
    coverage_score,
    normalize,
)

# ---------------------------------------------------------------------------
# Scoring primitive tests
# ---------------------------------------------------------------------------


def test_tokenize_strips_punctuation() -> None:
    assert _tokenize("Hello, World! 123") == ["hello", "world", "123"]


def test_tokenize_empty() -> None:
    assert _tokenize("") == []


def test_bm25_scores_returns_one_per_doc() -> None:
    scores = bm25_scores(["python", "query"], [["python", "is", "fast"], ["query", "data"]])
    assert len(scores) == 2
    assert all(s >= 0 for s in scores)


def test_bm25_scores_empty_query() -> None:
    assert bm25_scores([], [["some", "text"]]) == [0.0]


def test_bm25_scores_empty_docs() -> None:
    assert bm25_scores(["term"], []) == []


def test_bm25_term_in_all_docs_gets_low_idf() -> None:
    # "common" appears in every doc — IDF should be near-zero, score lower than unique term
    docs = [["common", "unique"], ["common", "other"], ["common", "third"]]
    scores_common = bm25_scores(["common"], docs)
    scores_unique = bm25_scores(["unique"], docs)
    # docs[0] has "unique" once; docs[1,2] don't — unique should score higher for docs[0]
    assert scores_unique[0] > scores_common[0]


def test_coverage_score_full_match() -> None:
    assert coverage_score(["a", "b", "c"], ["a", "b", "c", "d"]) == pytest.approx(1.0)


def test_coverage_score_no_match() -> None:
    assert coverage_score(["x", "y"], ["a", "b"]) == pytest.approx(0.0)


def test_coverage_score_partial() -> None:
    score = coverage_score(["python", "fast", "query"], ["python", "slow"])
    assert score == pytest.approx(1 / 3)


def test_coverage_score_empty_query() -> None:
    assert coverage_score([], ["a", "b"]) == pytest.approx(0.0)


def test_normalize_basic() -> None:
    result = normalize([0.0, 0.5, 1.0])
    assert result == pytest.approx([0.0, 0.5, 1.0])


def test_normalize_all_zeros() -> None:
    assert normalize([0.0, 0.0]) == [0.0, 0.0]


def test_normalize_scales_to_max() -> None:
    result = normalize([2.0, 4.0, 8.0])
    assert result == pytest.approx([0.25, 0.5, 1.0])


# ---------------------------------------------------------------------------
# EnhancedQueryService integration tests (file-based SQLite via tmp_path)
# ---------------------------------------------------------------------------


def _make_candidate(chunk_id: str, text: str, score: float) -> dict:
    return {
        "id": chunk_id,
        "score": score,
        "payload": {
            "text": text,
            "source_path": f"/data/sources/doc_{chunk_id}.md",
            "file_type": "md",
            "chunk_index": 0,
            "content_preview": text[:80],
            "content_hash": f"hash_{chunk_id}",
        },
    }


def _make_service(tmp_path: Path) -> tuple[EnhancedQueryService, MagicMock, MagicMock]:
    store = MagicMock()
    embedder = MagicMock()
    embedder.embed.return_value = [[0.1] * 384]
    l2_store = L2StoreAdapter(db_path=str(tmp_path / "l2.db"))
    svc = EnhancedQueryService(store=store, embedder=embedder, l2_store=l2_store)
    return svc, store, embedder


def test_query_enhanced_returns_top_k(tmp_path: Path) -> None:
    svc, store, _ = _make_service(tmp_path)
    cast(MagicMock, store).search.return_value = [
        _make_candidate("c1", "python chunking algorithm", 0.9),
        _make_candidate("c2", "qdrant vector store usage", 0.8),
        _make_candidate("c3", "embedding model architecture", 0.7),
        _make_candidate("c4", "unrelated topic about cats", 0.6),
        _make_candidate("c5", "another unrelated item", 0.5),
    ]
    result = svc.query_enhanced("python chunking", top_k=3)
    assert len(result["matches"]) == 3
    assert result["matches"][0]["rank"] == 1


def test_query_enhanced_scoring_fields_present(tmp_path: Path) -> None:
    svc, store, _ = _make_service(tmp_path)
    cast(MagicMock, store).search.return_value = [
        _make_candidate("c1", "semantic search with vectors", 0.85),
        _make_candidate("c2", "vector database qdrant", 0.70),
    ]
    result = svc.query_enhanced("semantic vector search", top_k=2)
    for match in result["matches"]:
        s = match["scoring"]
        assert "composite" in s
        assert "semantic" in s
        assert "bm25_norm" in s
        assert "coverage" in s
        assert "memory_boost" in s
        # composite can exceed 1 when individual signals aren't pre-normalized
        assert 0.0 <= s["composite"] <= 1.5


def test_query_enhanced_saves_memory_artifact(tmp_path: Path) -> None:
    svc, store, _ = _make_service(tmp_path)
    cast(MagicMock, store).search.return_value = [
        _make_candidate("c1", "chunking strategies", 0.9),
        _make_candidate("c2", "overlap settings", 0.7),
    ]
    result = svc.query_enhanced("chunking", session_id="sess-001")
    assert result["memory_id"] is not None
    artifacts = svc._l2.get_session_artifacts("sess-001")
    assert len(artifacts) == 1
    assert artifacts[0]["artifact_type"] == "query_memory"
    assert "chunking" in artifacts[0]["text_content"]


def test_query_enhanced_memory_boost_on_repeat(tmp_path: Path) -> None:
    svc, store, _ = _make_service(tmp_path)
    # First query: c1 gets retrieved
    cast(MagicMock, store).search.return_value = [
        _make_candidate("c1", "chunking text documents", 0.9),
        _make_candidate("c2", "vector embedding model", 0.5),
    ]
    svc.query_enhanced("chunking documents", session_id="s1")

    # Second query: c1 should now have memory_boost > 0
    result2 = svc.query_enhanced("chunking documents", session_id="s2")
    c1_match = next((m for m in result2["matches"] if m["id"] == "c1"), None)
    assert c1_match is not None
    assert c1_match["scoring"]["memory_boost"] > 0.0


def test_query_enhanced_no_save_memory(tmp_path: Path) -> None:
    svc, store, _ = _make_service(tmp_path)
    cast(MagicMock, store).search.return_value = [
        _make_candidate("c1", "some text", 0.8),
    ]
    result = svc.query_enhanced("some", save_memory=False)
    assert result["memory_id"] is None


def test_query_enhanced_empty_candidates(tmp_path: Path) -> None:
    svc, store, _ = _make_service(tmp_path)
    cast(MagicMock, store).search.return_value = []
    result = svc.query_enhanced("anything")
    assert result["matches"] == []
    assert result["memory_id"] is None
    assert result["analytics"]["candidate_pool"] == 0


def test_query_enhanced_analytics_shape(tmp_path: Path) -> None:
    svc, store, _ = _make_service(tmp_path)
    cast(MagicMock, store).search.return_value = [
        _make_candidate("c1", "test content", 0.9),
    ]
    result = svc.query_enhanced("test", top_k=1)
    a = result["analytics"]
    assert "latency_ms" in a
    assert a["candidate_pool"] == 1
    assert a["returned_count"] == 1
    assert "scoring_weights" in a
    weights = a["scoring_weights"]
    assert abs(sum(weights.values()) - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# Scoring-log tests
# ---------------------------------------------------------------------------


def test_score_log_emitted_when_enabled(tmp_path: Path) -> None:
    svc, store, _ = _make_service(tmp_path)
    cast(MagicMock, store).search.return_value = [
        _make_candidate("c1", "chunking pipeline text", 0.9),
        _make_candidate("c2", "vector embedding model", 0.6),
    ]
    log_records: list[dict] = []
    with (
        patch(
            "omnikb.services.enhanced_query_service.append_jsonl",
            side_effect=lambda stream, rec: log_records.append({"stream": stream, **rec}),
        ),
        patch(
            "omnikb.services.enhanced_query_service.get_settings",
            return_value=MagicMock(l2_scoring_log_enabled=True),
        ),
    ):
        svc.query_enhanced("chunking pipeline", top_k=2, session_id="log-test")

    assert len(log_records) == 1
    rec = log_records[0]
    assert rec["stream"] == "l2-scoring"
    assert rec["query"] == "chunking pipeline"
    assert rec["session_id"] == "log-test"
    assert rec["candidate_pool"] == 2
    assert "scoring_weights" in rec
    assert len(rec["results"]) == 2


def test_score_log_not_emitted_when_disabled(tmp_path: Path) -> None:
    svc, store, _ = _make_service(tmp_path)
    cast(MagicMock, store).search.return_value = [
        _make_candidate("c1", "some content", 0.8),
    ]
    log_records: list[dict] = []
    with (
        patch(
            "omnikb.services.enhanced_query_service.append_jsonl",
            side_effect=lambda stream, rec: log_records.append(rec),
        ),
        patch(
            "omnikb.services.enhanced_query_service.get_settings",
            return_value=MagicMock(l2_scoring_log_enabled=False),
        ),
    ):
        svc.query_enhanced("some query")

    assert log_records == []


def test_score_log_result_fields(tmp_path: Path) -> None:
    svc, store, _ = _make_service(tmp_path)
    cast(MagicMock, store).search.return_value = [
        _make_candidate("c1", "rag chunking strategy", 0.9),
        _make_candidate("c2", "unrelated noise text", 0.3),
    ]
    log_records: list[dict] = []
    with (
        patch(
            "omnikb.services.enhanced_query_service.append_jsonl",
            side_effect=lambda stream, rec: log_records.append(rec),
        ),
        patch(
            "omnikb.services.enhanced_query_service.get_settings",
            return_value=MagicMock(l2_scoring_log_enabled=True),
        ),
    ):
        svc.query_enhanced("rag chunking", top_k=2)

    result_entry = log_records[0]["results"][0]
    required = {
        "rank",
        "l1_rank",
        "rank_delta",
        "id",
        "source_path",
        "chunk_index",
        "composite",
        "semantic",
        "bm25_norm",
        "coverage",
        "memory_boost",
        "dominant_signal",
        "weighted_contributions",
    }
    assert required.issubset(result_entry.keys())
    # weighted contributions must sum to composite (within float tolerance)
    wc = result_entry["weighted_contributions"]
    assert abs(sum(wc.values()) - result_entry["composite"]) < 1e-3


def test_score_log_rank_delta_on_rerank(tmp_path: Path) -> None:
    svc, store, _ = _make_service(tmp_path)
    # c2 has low semantic but very high lexical overlap — should be promoted
    cast(MagicMock, store).search.return_value = [
        _make_candidate("c1", "unrelated completely different", 0.95),
        _make_candidate("c2", "rag chunking strategy pipeline", 0.50),
    ]
    log_records: list[dict] = []
    with (
        patch(
            "omnikb.services.enhanced_query_service.append_jsonl",
            side_effect=lambda stream, rec: log_records.append(rec),
        ),
        patch(
            "omnikb.services.enhanced_query_service.get_settings",
            return_value=MagicMock(l2_scoring_log_enabled=True),
        ),
    ):
        svc.query_enhanced("rag chunking strategy", top_k=2)

    results = log_records[0]["results"]
    # rank_delta > 0 means promoted; rank_delta < 0 means demoted
    # All entries must have an integer rank_delta
    for r in results:
        assert isinstance(r["rank_delta"], int)
        assert r["l1_rank"] - r["rank"] == r["rank_delta"]


def test_score_log_dominant_signal_is_valid(tmp_path: Path) -> None:
    svc, store, _ = _make_service(tmp_path)
    cast(MagicMock, store).search.return_value = [
        _make_candidate("c1", "semantic retrieval pipeline", 0.85),
    ]
    log_records: list[dict] = []
    with (
        patch(
            "omnikb.services.enhanced_query_service.append_jsonl",
            side_effect=lambda stream, rec: log_records.append(rec),
        ),
        patch(
            "omnikb.services.enhanced_query_service.get_settings",
            return_value=MagicMock(l2_scoring_log_enabled=True),
        ),
    ):
        svc.query_enhanced("semantic retrieval", top_k=1)

    dominant = log_records[0]["results"][0]["dominant_signal"]
    assert dominant in {"semantic", "bm25", "coverage", "memory"}


def test_score_log_is_valid_json_serialisable(tmp_path: Path) -> None:
    svc, store, _ = _make_service(tmp_path)
    cast(MagicMock, store).search.return_value = [
        _make_candidate("c1", "test document content", 0.8),
        _make_candidate("c2", "another document here", 0.7),
        _make_candidate("c3", "third result item", 0.6),
    ]
    log_records: list[dict] = []
    with (
        patch(
            "omnikb.services.enhanced_query_service.append_jsonl",
            side_effect=lambda stream, rec: log_records.append(rec),
        ),
        patch(
            "omnikb.services.enhanced_query_service.get_settings",
            return_value=MagicMock(l2_scoring_log_enabled=True),
        ),
    ):
        svc.query_enhanced("test query", top_k=3)

    # Must serialise cleanly — this is what append_jsonl does internally
    serialised = json.dumps(log_records[0], default=str)
    parsed = json.loads(serialised)
    assert len(parsed["results"]) == 3
