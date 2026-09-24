"""Layer 3 concept nodes derived from relationship edges (pre-HDBSCAN slice).

Deterministic connected-component builder over dreaming edges. Full HDBSCAN /
embedding clustering remains Phase 2 (ADR 0002).
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1

from omnikb.adapters.interaction_store import RelationshipEdge


@dataclass(frozen=True, slots=True)
class ConceptNode:
    """Typed concept node: a connected component of Layer 3 relationship edges."""

    concept_id: str
    member_point_ids: tuple[str, ...]
    edge_count: int
    mean_score: float
    score_version: str
    builder: str = "connected_components_v1"


def build_concepts_from_edges(
    edges: list[RelationshipEdge],
    *,
    min_component_size: int = 2,
    score_version: str | None = None,
) -> list[ConceptNode]:
    """Build concept nodes as connected components of undirected edge pairs.

    Stable ordering: concepts sorted by descending mean_score, then concept_id.
    Member lists are sorted lexicographically. No external clustering dependency.
    """
    if min_component_size < 2:
        raise ValueError("min_component_size must be >= 2")

    filtered = [
        e
        for e in edges
        if e.src_point_id
        and e.dst_point_id
        and e.src_point_id != e.dst_point_id
        and (score_version is None or e.score_version == score_version)
    ]
    if not filtered:
        return []

    points: set[str] = set()
    for e in filtered:
        points.add(e.src_point_id)
        points.add(e.dst_point_id)

    parent = {pid: pid for pid in points}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        if ra < rb:
            parent[rb] = ra
        else:
            parent[ra] = rb

    for e in filtered:
        union(e.src_point_id, e.dst_point_id)

    members: dict[str, list[str]] = {}
    for pid in points:
        root = find(pid)
        members.setdefault(root, []).append(pid)

    edge_stats: dict[str, list[float]] = {root: [] for root in members}
    versions: dict[str, str] = {}
    for e in filtered:
        root = find(e.src_point_id)
        edge_stats[root].append(float(e.score))
        versions.setdefault(root, e.score_version)

    concepts: list[ConceptNode] = []
    for root, member_list in members.items():
        if len(member_list) < min_component_size:
            continue
        ordered = tuple(sorted(member_list))
        scores = edge_stats.get(root) or [0.0]
        mean = sum(scores) / len(scores)
        digest = sha1("|".join(ordered).encode("utf-8"), usedforsecurity=False).hexdigest()[:16]
        concepts.append(
            ConceptNode(
                concept_id=f"cc_{digest}",
                member_point_ids=ordered,
                edge_count=len(scores),
                mean_score=mean,
                score_version=versions.get(root, score_version or "unknown"),
            )
        )

    concepts.sort(key=lambda c: (-c.mean_score, c.concept_id))
    return concepts
