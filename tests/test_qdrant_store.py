from omnikb.adapters.qdrant_store import QdrantStore, VectorRecord


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[list] = []

    def upsert(self, collection_name: str, points: list) -> None:  # noqa: ANN001
        self.calls.append(points)


def test_upsert_batches_when_estimated_payload_would_exceed_limit() -> None:
    store = QdrantStore.__new__(QdrantStore)
    store.collection = "omnikb_documents"
    store.max_upsert_payload_bytes = 3000
    store.client = _FakeClient()

    large_text = "x" * 1800
    records = [
        VectorRecord(point_id="1", vector=[0.1, 0.2, 0.3], payload={"text": large_text}),
        VectorRecord(point_id="2", vector=[0.1, 0.2, 0.3], payload={"text": large_text}),
        VectorRecord(point_id="3", vector=[0.1, 0.2, 0.3], payload={"text": large_text}),
    ]

    store.upsert(records)

    assert len(store.client.calls) == 3
    assert all(len(batch) == 1 for batch in store.client.calls)
