from __future__ import annotations

import math
import re
import time
import uuid
from collections import Counter
from datetime import UTC, datetime

from omnikb.adapters.embedder import SentenceTransformerEmbedder
from omnikb.adapters.l2_store import L2StoreAdapter
from omnikb.adapters.qdrant_store import QdrantStore

# ---------------------------------------------------------------------------
# Scoring primitives (pure functions — easy to unit-test)
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokens; strips punctuation."""
    return re.findall(r"[a-z0-9]+", text.lower())


def bm25_scores(
    query_terms: list[str],
    doc_term_lists: list[list[str]],
    k1: float = 1.5,
    b: float = 0.75,
) -> list[float]:
    """BM25 score for each doc in a small candidate pool.

    Uses BM25+ IDF to avoid negative values when a term appears in all docs.
    """
    n = len(doc_term_lists)
    if n == 0 or not query_terms:
        return [0.0] * n

    avg_dl = sum(len(d) for d in doc_term_lists) / n

    # document frequency per term across the candidate pool
    df: dict[str, int] = {}
    for doc in doc_term_lists:
        for term in set(doc):
            df[term] = df.get(term, 0) + 1

    scores: list[float] = []
    for doc in doc_term_lists:
        dl = len(doc)
        tf_map = Counter(doc)
        score = 0.0
        for term in set(query_terms):
            tf = tf_map.get(term, 0)
            if tf == 0:
                continue
            idf = math.log((n - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5) + 1.0)
            score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl / avg_dl))
        scores.append(score)
    return scores


def coverage_score(query_terms: list[str], chunk_terms: list[str]) -> float:
    """Fraction of unique query terms present in the chunk."""
    unique_q = set(query_terms)
    if not unique_q:
        return 0.0
    chunk_set = set(chunk_terms)
    return len(unique_q & chunk_set) / len(unique_q)


def normalize(values: list[float]) -> list[float]:
    """Min-max normalize to [0, 1] relative to the candidate set."""
    max_v = max(values) if values else 0.0
    if max_v == 0.0:
        return [0.0] * len(values)
    return [v / max_v for v in values]


# ---------------------------------------------------------------------------
# Enhanced query service
# ---------------------------------------------------------------------------


class EnhancedQueryService:
    """Layer-2 re-ranking: combines semantic similarity with BM25, coverage,
    and episodic memory boost, then persists a query_memory artifact.

    Weights (must sum to 1.0):
      semantic  0.50 �� Qdrant cosine similarity; primary signal
      bm25      0.20 — lexical match over the candidate pool
      coverage  0.15 — query-term presence ratio in the chunk
      memory    0.15 — prior retrieval frequency from L2 store
    """

    _L1_POOL = 15  # candidates fetched from Qdrant before re-ranking

    def __init__(
        self,
        store: QdrantStore,
        embedder: SentenceTransformerEmbedder,
        l2_store: L2StoreAdapter,
        weight_semantic: float = 0.50,
        weight_bm25: float = 0.20,
        weight_coverage: float = 0.15,
        weight_memory: float = 0.15,
    ) -> None:
        self._store = store
        self._embedder = embedder
        self._l2 = l2_store
        self._w_sem = weight_semantic
        self._w_bm25 = weight_bm25
        self._w_cov = weight_coverage
        self._w_mem = weight_memory

    def query_enhanced(
        self,
        query: str,
        top_k: int = 3,
        session_id: str | None = None,
        save_memory: bool = True,
    ) -> dict:
        """Retrieve, re-rank, and record a query_memory artifact.

        Returns a dict with keys: session_id, memory_id, matches, analytics.
        Each match carries a scoring breakdown so callers can inspect
        which signal drove the ranking.
        """
        t0 = time.perf_counter()
        sid = session_id or str(uuid.uuid4())

        # ── L1: embed query and pull candidate pool ──────────────────────
        vector = self._embedder.embed([query])[0]
        candidates = self._store.search(query_vector=vector, limit=self._L1_POOL)

        if not candidates:
            return {
                "session_id": sid,
                "memory_id": None,
                "matches": [],
                "analytics": {
                    "latency_ms": round((time.perf_counter() - t0) * 1000, 3),
                    "candidate_pool": 0,
                    "returned_count": 0,
                    "top_composite": 0.0,
                    "scoring_weights": self._weights_dict(),
                },
            }

        chunk_ids = [str(c.get("id", "")) for c in candidates]
        chunk_texts = [str((c.get("payload") or {}).get("text", "")) for c in candidates]
        semantic_scores = [float(c.get("score", 0.0)) for c in candidates]

        # ── scoring signals ───────────────────────────────────────────────
        q_terms = _tokenize(query)
        doc_terms = [_tokenize(t) for t in chunk_texts]

        norm_bm25 = normalize(bm25_scores(q_terms, doc_terms))
        cov_scores = [coverage_score(q_terms, dt) for dt in doc_terms]

        freq_map = self._l2.get_chunk_retrieval_counts(chunk_ids)
        norm_mem = normalize([float(freq_map.get(cid, 0)) for cid in chunk_ids])

        # ── composite score ───────────────────────────────────────────────
        composite = [
            self._w_sem * sem + self._w_bm25 * bm25 + self._w_cov * cov + self._w_mem * mem
            for sem, bm25, cov, mem in zip(semantic_scores, norm_bm25, cov_scores, norm_mem)
        ]

        # ── select top_k ──────────────────────────────────────────────────
        ranked_idx = sorted(range(len(candidates)), key=lambda i: composite[i], reverse=True)[
            :top_k
        ]

        matches: list[dict] = []
        for rank, i in enumerate(ranked_idx):
            payload = dict(candidates[i].get("payload") or {})
            matches.append(
                {
                    "rank": rank + 1,
                    "id": chunk_ids[i],
                    "source_path": payload.get("source_path"),
                    "file_type": payload.get("file_type"),
                    "chunk_index": payload.get("chunk_index"),
                    "text": payload.get("text"),
                    "content_preview": payload.get("content_preview"),
                    "content_hash": payload.get("content_hash"),
                    "scoring": {
                        "composite": round(composite[i], 4),
                        "semantic": round(semantic_scores[i], 4),
                        "bm25_norm": round(norm_bm25[i], 4),
                        "coverage": round(cov_scores[i], 4),
                        "memory_boost": round(norm_mem[i], 4),
                    },
                }
            )

        # ── persist L2 memory artifact ���───────────────────────────────────
        memory_id: int | None = None
        if save_memory:
            parts = [f"Query: {query}", ""]
            for m in matches:
                parts.append(
                    f"[{m['rank']}] {m.get('source_path', '?')} "
                    f"(composite={m['scoring']['composite']:.3f})\n"
                    f"{str(m.get('content_preview') or '')[:200]}"
                )
            memory_id = self._l2.record_artifact(
                session_id=sid,
                artifact_type="query_memory",
                text_content="\n".join(parts),
                source_chunk_ids=[chunk_ids[i] for i in ranked_idx],
                metadata={
                    "query": query,
                    "top_k": top_k,
                    "scores": [
                        {
                            "chunk_id": chunk_ids[i],
                            "composite": round(composite[i], 4),
                            "semantic": round(semantic_scores[i], 4),
                            "bm25_norm": round(norm_bm25[i], 4),
                            "coverage": round(cov_scores[i], 4),
                            "memory_boost": round(norm_mem[i], 4),
                        }
                        for i in ranked_idx
                    ],
                    "retrieved_at": datetime.now(UTC).isoformat(),
                },
            )

        top_composite = matches[0]["scoring"]["composite"] if matches else 0.0
        return {
            "session_id": sid,
            "memory_id": memory_id,
            "matches": matches,
            "analytics": {
                "latency_ms": round((time.perf_counter() - t0) * 1000, 3),
                "candidate_pool": len(candidates),
                "returned_count": len(matches),
                "top_composite": top_composite,
                "scoring_weights": self._weights_dict(),
            },
        }

    def _weights_dict(self) -> dict[str, float]:
        return {
            "semantic": self._w_sem,
            "bm25": self._w_bm25,
            "coverage": self._w_cov,
            "memory": self._w_mem,
        }
