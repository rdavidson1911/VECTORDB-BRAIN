"""Idle dreaming: pairwise cosine edges among boosted Layer 1 chunks."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Protocol

from omnikb.adapters.interaction_store import InteractionStore, RelationshipEdge
from omnikb.domain.memory_tier import dreaming_allowed

SCORE_VERSION = "pairwise_cosine_v1"


class VectorRetriever(Protocol):
    def retrieve_vectors(self, point_ids: list[str]) -> dict[str, list[float]]: ...


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b, strict=True):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return float(dot / (math.sqrt(na) * math.sqrt(nb)))


class DreamingService:
    def __init__(
        self,
        *,
        store: VectorRetriever,
        interaction_store: InteractionStore,
        idle_minutes: float = 30.0,
        edge_min_score: float = 0.72,
        candidate_limit: int = 48,
    ) -> None:
        self.store = store
        self.interaction_store = interaction_store
        self.idle_minutes = idle_minutes
        self.edge_min_score = edge_min_score
        self.candidate_limit = candidate_limit

    def is_idle(self) -> bool:
        seconds = self.interaction_store.seconds_since_last_event()
        if seconds is None:
            return True
        return seconds >= self.idle_minutes * 60.0

    def run(self, *, force: bool = False, dry_run: bool = False) -> dict[str, int | str | bool]:
        if not force and not self.is_idle():
            return {
                "skipped": True,
                "reason": "not_idle",
                "edges_written": 0,
            }
        boosts = self.interaction_store.list_boosted_points(limit=self.candidate_limit)
        eligible_ids = [
            b.point_id
            for b in boosts
            if dreaming_allowed(b.memory_tier, has_click_boost=b.click_count > 0)
        ]
        if len(eligible_ids) < 2:
            return {
                "skipped": False,
                "reason": "insufficient_candidates",
                "edges_written": 0,
                "candidates": len(eligible_ids),
            }
        vectors = self.store.retrieve_vectors(eligible_ids)
        created_at = datetime.now(UTC).isoformat()
        edges: list[RelationshipEdge] = []
        ids = [pid for pid in eligible_ids if pid in vectors]
        for i, src in enumerate(ids):
            for dst in ids[i + 1 :]:
                score = _cosine(vectors[src], vectors[dst])
                if score < self.edge_min_score:
                    continue
                edges.append(
                    RelationshipEdge(
                        src_point_id=src,
                        dst_point_id=dst,
                        score=score,
                        score_version=SCORE_VERSION,
                        created_at=created_at,
                    )
                )
        if dry_run:
            return {
                "skipped": False,
                "reason": "dry_run",
                "edges_written": 0,
                "edges_computed": len(edges),
                "candidates": len(ids),
            }
        written = self.interaction_store.upsert_edges(edges)
        return {
            "skipped": False,
            "reason": "ok",
            "edges_written": written,
            "candidates": len(ids),
            "score_version": SCORE_VERSION,
        }
