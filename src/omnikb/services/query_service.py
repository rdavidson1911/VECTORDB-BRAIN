from __future__ import annotations

from datetime import datetime
from time import perf_counter

from omnikb.adapters.embedder import SentenceTransformerEmbedder
from omnikb.adapters.qdrant_store import QdrantStore


class QueryService:
    def __init__(self, store: QdrantStore, embedder: SentenceTransformerEmbedder) -> None:
        self.store = store
        self.embedder = embedder

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
    ) -> tuple[list[dict], dict]:
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
        elapsed_ms = (perf_counter() - started) * 1000.0
        scores = [float(match.get("score", 0.0)) for match in matches]
        unique_sources = {
            str((match.get("payload") or {}).get("source_path", "")) for match in matches
        }
        analytics = {
            "latency_ms": round(elapsed_ms, 3),
            "returned_count": len(matches),
            "unique_sources": len([source for source in unique_sources if source]),
            "top_score": max(scores) if scores else 0.0,
            "average_score": (sum(scores) / len(scores)) if scores else 0.0,
        }
        return matches, analytics


def _safe_parse_date_to_timestamp(value: str, end_of_day: bool = False) -> float | None:
    try:
        if len(value) == 10:
            suffix = "T23:59:59+00:00" if end_of_day else "T00:00:00+00:00"
            return datetime.fromisoformat(f"{value}{suffix}").timestamp()
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return None
