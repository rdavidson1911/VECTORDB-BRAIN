from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, cast

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    Range,
    VectorParams,
)


@dataclass(slots=True)
class VectorRecord:
    point_id: str
    vector: list[float]
    payload: dict[str, Any]


class QdrantStore:
    def __init__(
        self,
        url: str,
        collection: str,
        timeout_seconds: float = 15.0,
        max_upsert_payload_bytes: int = 28 * 1024 * 1024,
    ) -> None:
        self.collection = collection
        self.max_upsert_payload_bytes = max_upsert_payload_bytes
        self.client = QdrantClient(url=url, timeout=int(timeout_seconds), check_compatibility=False)

    def ensure_collection(self, vector_size: int) -> None:
        collections = self.client.get_collections().collections
        if any(c.name == self.collection for c in collections):
            return
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return

        batch_records: list[VectorRecord] = []
        # Rough JSON envelope + separators.
        batch_size_bytes = 256
        for record in records:
            estimated_size = self._estimate_point_json_bytes(record)
            if batch_records and batch_size_bytes + estimated_size > self.max_upsert_payload_bytes:
                self._upsert_batch(batch_records)
                batch_records = []
                batch_size_bytes = 256
            batch_records.append(record)
            batch_size_bytes += estimated_size

        if batch_records:
            self._upsert_batch(batch_records)

    def _upsert_batch(self, records: list[VectorRecord]) -> None:
        points = [
            PointStruct(id=record.point_id, vector=record.vector, payload=record.payload)
            for record in records
        ]
        if points:
            self.client.upsert(collection_name=self.collection, points=points)

    def _estimate_point_json_bytes(self, record: VectorRecord) -> int:
        point_dict = {"id": record.point_id, "vector": record.vector, "payload": record.payload}
        point_json = json.dumps(point_dict, ensure_ascii=False, default=str)
        # Include a small separator/structure margin per point.
        return len(point_json.encode("utf-8")) + 16

    def delete_by_source_path(self, source_path: str) -> None:
        self.client.delete(
            collection_name=self.collection,
            points_selector=Filter(
                must=[FieldCondition(key="source_path", match=MatchValue(value=source_path))]
            ),
        )

    def count_points(self, must: list[FieldCondition]) -> int:
        """Count points matching payload filters (scroll, no vectors)."""
        total = 0
        offset = None
        flt = Filter(must=cast(Any, must))
        while True:
            points, next_offset = self.client.scroll(
                collection_name=self.collection,
                scroll_filter=flt,
                limit=256,
                offset=offset,
                with_payload=False,
                with_vectors=False,
            )
            total += len(points)
            if next_offset is None:
                break
            offset = next_offset
        return total

    def search(
        self,
        query_vector: list[float],
        limit: int = 5,
        source_path: str | None = None,
        file_type: str | None = None,
        document_id: str | None = None,
        content_hash: str | None = None,
        chunk_strategy: str | None = None,
        date_from_ts: float | None = None,
        date_to_ts: float | None = None,
    ) -> list[dict[str, Any]]:
        must: list[FieldCondition] = []
        if source_path:
            must.append(FieldCondition(key="source_path", match=MatchValue(value=source_path)))
        if file_type:
            must.append(FieldCondition(key="file_type", match=MatchValue(value=file_type)))
        if document_id:
            must.append(FieldCondition(key="document_id", match=MatchValue(value=document_id)))
        if content_hash:
            must.append(FieldCondition(key="content_hash", match=MatchValue(value=content_hash)))
        if chunk_strategy:
            must.append(
                FieldCondition(key="chunk_strategy", match=MatchValue(value=chunk_strategy))
            )
        if date_from_ts is not None or date_to_ts is not None:
            must.append(
                FieldCondition(
                    key="indexed_at_ts",
                    range=Range(gte=date_from_ts, lte=date_to_ts),
                )
            )
        query_filter = Filter(must=cast(Any, must)) if must else None
        hits = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
        ).points
        return [
            {
                "id": hit.id,
                "score": hit.score,
                "payload": dict(hit.payload or {}),
            }
            for hit in hits
        ]

    def health(self) -> bool:
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False

    def collection_stats(self) -> dict[str, Any]:
        info = self.client.get_collection(self.collection)
        return asdict(info) if hasattr(info, "__dataclass_fields__") else info.model_dump()

    def list_sources(self, limit: int = 1000) -> list[dict[str, Any]]:
        points, _ = self.client.scroll(
            collection_name=self.collection,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        by_source: dict[str, dict[str, Any]] = {}
        for point in points:
            payload = dict(point.payload or {})
            source_path = str(payload.get("source_path", "unknown"))
            entry = by_source.setdefault(
                source_path,
                {
                    "source_path": source_path,
                    "file_type": str(payload.get("file_type", "unknown")),
                    "chunk_count": 0,
                    "latest_updated_at": payload.get("updated_at"),
                    "content_hash": payload.get("content_hash"),
                },
            )
            entry["chunk_count"] += 1
            updated_at = payload.get("updated_at")
            if isinstance(updated_at, str) and (
                entry["latest_updated_at"] is None or updated_at > entry["latest_updated_at"]
            ):
                entry["latest_updated_at"] = updated_at
        return sorted(by_source.values(), key=lambda item: item["chunk_count"], reverse=True)

    def corpus_summary(self) -> dict[str, Any]:
        sources = self.list_sources(limit=5000)
        file_type_counts: dict[str, int] = {}
        chunk_count = 0
        for source in sources:
            file_type = source.get("file_type") or "unknown"
            file_type_counts[file_type] = file_type_counts.get(file_type, 0) + 1
            chunk_count += int(source.get("chunk_count", 0))
        stats = self.collection_stats()
        vectors_count = int(stats.get("vectors_count", chunk_count))
        return {
            "collection": self.collection,
            "vectors_count": vectors_count,
            "chunks_count": chunk_count,
            "sources_count": len(sources),
            "file_type_counts": file_type_counts,
        }
