from __future__ import annotations

from datetime import datetime
from time import perf_counter

from omnikb.adapters.embedder import SentenceTransformerEmbedder
from omnikb.adapters.qdrant_store import QdrantStore
from omnikb.services.interaction_service import InteractionService


class QueryService:
    def __init__(
        self,
        store: QdrantStore,
        embedder: SentenceTransformerEmbedder,
        interaction_service: InteractionService | None = None,
        boost_weight: float = 0.25,
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.interaction_service = interaction_service
        self.boost_weight = boost_weight

    def query(
        self,
        text: str,
        limit: int = 5,
        source_path: str | None = None,
        file_type: str | None = None,
        document_id: str | None = None,
        content_hash: str | None = None,
        chunk_strategy: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        text_contains: str | None = None,
        min_score: float | None = None,
        include_neighbors: bool = False,
        neighbor_window: int = 1,
        include_layer3: bool = False,
    ) -> tuple[list[dict], list[dict], list[dict], list[dict], dict]:
        """Return layer1, layer2, layer3 relations, legacy matches, analytics."""
        started = perf_counter()
        date_from_ts = _safe_parse_date_to_timestamp(date_from) if date_from else None
        date_to_ts = _safe_parse_date_to_timestamp(date_to, end_of_day=True) if date_to else None
        vector = self.embedder.embed([text])[0]
        matches = self.store.search(
            query_vector=vector,
            limit=limit,
            source_path=source_path,
            file_type=file_type,
            document_id=document_id,
            content_hash=content_hash,
            chunk_strategy=chunk_strategy,
            date_from_ts=date_from_ts,
            date_to_ts=date_to_ts,
        )
        if min_score is not None:
            matches = [match for match in matches if float(match.get("score", 0.0)) >= min_score]
        if text_contains:
            needle = text_contains.lower()
            matches = [
                match
                for match in matches
                if needle in str((match.get("payload") or {}).get("text", "")).lower()
            ]

        if include_neighbors and neighbor_window > 0:
            expanded: list[dict] = []
            seen: set[str] = set()
            for match in matches:
                mid = str(match.get("id", ""))
                if mid and mid not in seen:
                    expanded.append(match)
                    seen.add(mid)
                payload = dict(match.get("payload") or {})
                doc_id = payload.get("document_id")
                chunk_index = payload.get("chunk_index")
                if not isinstance(doc_id, str) or not isinstance(chunk_index, int):
                    continue
                for neighbor in self.store.get_neighbor_chunks(
                    document_id=doc_id,
                    chunk_index=chunk_index,
                    window=neighbor_window,
                    exclude_point_id=mid or None,
                ):
                    nid = str(neighbor.get("id", ""))
                    if nid and nid not in seen:
                        expanded.append(neighbor)
                        seen.add(nid)
            matches = expanded

        if self.interaction_service is not None:
            layer1, layer2 = self.interaction_service.fuse_matches(
                matches, boost_weight=self.boost_weight
            )
        else:
            layer1 = [dict(m) for m in matches]
            layer2 = [dict(m) for m in matches]

        layer3: list[dict] = []
        if include_layer3 and self.interaction_service is not None:
            point_ids = [str(m.get("id", "")) for m in layer1 if m.get("id") is not None]
            edges = self.interaction_service.store.edges_for_points(point_ids)
            layer3 = [
                {
                    "src_point_id": e.src_point_id,
                    "dst_point_id": e.dst_point_id,
                    "score": e.score,
                    "score_version": e.score_version,
                    "created_at": e.created_at,
                }
                for e in edges
            ]

        elapsed_ms = (perf_counter() - started) * 1000.0
        scores = [float(match.get("score", 0.0)) for match in layer1]
        unique_sources = {
            str((match.get("payload") or {}).get("source_path", "")) for match in layer1
        }
        analytics = {
            "latency_ms": round(elapsed_ms, 3),
            "returned_count": len(layer1),
            "unique_sources": len([source for source in unique_sources if source]),
            "top_score": max(scores) if scores else 0.0,
            "average_score": (sum(scores) / len(scores)) if scores else 0.0,
        }
        # Legacy `matches` mirrors Layer 1 cosine hits.
        return layer1, layer2, layer3, layer1, analytics


def _safe_parse_date_to_timestamp(value: str, end_of_day: bool = False) -> float | None:
    try:
        if len(value) == 10:
            suffix = "T23:59:59+00:00" if end_of_day else "T00:00:00+00:00"
            return datetime.fromisoformat(f"{value}{suffix}").timestamp()
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return None
