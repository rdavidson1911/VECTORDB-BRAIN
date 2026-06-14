"""Run embedding comparison on research Qdrant (port 6334)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_BENCH_DIR = Path(__file__).resolve().parent
if str(_BENCH_DIR) not in sys.path:
    sys.path.insert(0, str(_BENCH_DIR))

from embedding_eval import run_all  # noqa: E402

ARTIFACT = Path(__file__).resolve().parents[1] / "artifacts" / "embedding_benchmark_latest.json"


@pytest.mark.timeout(3600)
def test_embedding_model_comparison(qdrant_url: str, research_collection: str) -> None:
    payload = run_all(qdrant_url=qdrant_url, collection=research_collection)
    assert payload["chunk_count"] >= 3
    assert len(payload["models"]) == 3
    for row in payload["models"]:
        assert row["recall_at_10"] >= 0.0
    assert ARTIFACT.is_file()
    saved = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert saved["models"][0]["composite_score"] >= saved["models"][-1]["composite_score"]
