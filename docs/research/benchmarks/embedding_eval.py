"""Embedding model comparison harness (Research Agent; port 6334 only)."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from omnikb.adapters.document_loader import discover_files, load_document
from omnikb.adapters.embedder import SentenceTransformerEmbedder
from omnikb.domain.chunking import ChunkingConfig, chunk_text

ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = ROOT / "data" / "sources"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "queries.json"
OUT_DIR = ROOT / "docs" / "research" / "artifacts"

ALL_MODELS: list[tuple[str, str]] = [
    ("all-MiniLM-L6-v2", "sentence-transformers/all-MiniLM-L6-v2"),
    ("all-mpnet-base-v2", "sentence-transformers/all-mpnet-base-v2"),
    ("bge-m3", "BAAI/bge-m3"),
]


def _models_to_run() -> list[tuple[str, str]]:
    import os

    raw = os.environ.get("RESEARCH_BENCHMARK_MODELS", "").strip()
    if not raw:
        return list(ALL_MODELS)
    slugs = {s.strip() for s in raw.split(",") if s.strip()}
    return [pair for pair in ALL_MODELS if pair[0] in slugs]


CHUNK_CONFIG = ChunkingConfig(strategy="recursive_char_v1", chunk_size=450, chunk_overlap=60)

# Composite score weights (documented in embedding-model-comparison.md)
W_RECALL10 = 0.45
W_RECALL5 = 0.15
W_LATENCY = 0.25
W_MEMORY = 0.10
W_BUILD = 0.05


@dataclass(slots=True)
class ChunkRecord:
    point_id: str
    source_file: str
    chunk_index: int
    text: str


@dataclass(slots=True)
class ModelMetrics:
    model_slug: str
    model_name: str
    dimensions: int
    chunk_count: int
    recall_at_5: float
    recall_at_10: float
    latency_ms_p50: float
    latency_ms_p95: float
    index_build_ms: float
    memory_mb_rss_delta: float | None
    composite_score: float


def _load_queries() -> list[dict[str, str]]:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def _build_chunks() -> list[ChunkRecord]:
    files = sorted(discover_files(str(SOURCE_DIR), recursive=True))
    records: list[ChunkRecord] = []
    for file_path in files:
        rel = file_path.name
        text = load_document(file_path).text
        chunks = chunk_text(text, CHUNK_CONFIG)
        for idx, chunk in enumerate(chunks):
            pid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{rel}:{idx}"))
            records.append(
                ChunkRecord(
                    point_id=pid,
                    source_file=rel,
                    chunk_index=idx,
                    text=chunk,
                )
            )
    return records


def _relevant_ids(chunks: list[ChunkRecord], source_file: str) -> set[str]:
    return {c.point_id for c in chunks if c.source_file == source_file}


def _try_rss_mb() -> float | None:
    try:
        import psutil

        return psutil.Process().memory_info().rss / (1024 * 1024)
    except ImportError:
        return None


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(ordered) - 1)
    if f == c:
        return ordered[f]
    return ordered[f] + (ordered[c] - ordered[f]) * (k - f)


def _normalize_inverse(values: list[float]) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi <= lo:
        return [1.0 for _ in values]
    return [1.0 - (v - lo) / (hi - lo) for v in values]


def evaluate_model(
    *,
    qdrant_url: str,
    collection: str,
    model_slug: str,
    model_name: str,
    chunks: list[ChunkRecord],
    queries: list[dict[str, str]],
) -> ModelMetrics:
    coll_name = f"{collection}_{model_slug}"
    client = QdrantClient(url=qdrant_url, timeout=60, check_compatibility=False)
    if client.collection_exists(coll_name):
        client.delete_collection(coll_name)

    embedder = SentenceTransformerEmbedder(model_name=model_name)
    rss_before = _try_rss_mb()

    texts = [c.text for c in chunks]
    t0 = time.perf_counter()
    vectors = embedder.embed(texts)
    embed_ms = (time.perf_counter() - t0) * 1000.0

    t1 = time.perf_counter()
    client.create_collection(
        collection_name=coll_name,
        vectors_config=VectorParams(size=embedder.dimensions, distance=Distance.COSINE),
    )
    points = [
        PointStruct(
            id=c.point_id,
            vector=vectors[i],
            payload={
                "source_file": c.source_file,
                "chunk_index": c.chunk_index,
                "text": c.text[:500],
            },
        )
        for i, c in enumerate(chunks)
    ]
    client.upsert(collection_name=coll_name, points=points)
    index_build_ms = (time.perf_counter() - t1) * 1000.0 + embed_ms

    rss_after = _try_rss_mb()
    mem_delta = (
        (rss_after - rss_before) if rss_before is not None and rss_after is not None else None
    )

    latencies: list[float] = []
    hits5 = 0
    hits10 = 0
    for q in queries:
        rel = _relevant_ids(chunks, q["source_file"])
        qv = embedder.embed([q["query"]])[0]
        tq = time.perf_counter()
        results = client.query_points(
            collection_name=coll_name,
            query=qv,
            limit=10,
            with_payload=True,
        ).points
        latencies.append((time.perf_counter() - tq) * 1000.0)
        ranked = [str(p.id) for p in results]
        top5 = set(ranked[:5])
        top10 = set(ranked[:10])
        if rel & top5:
            hits5 += 1
        if rel & top10:
            hits10 += 1

    nq = len(queries)
    recall5 = hits5 / nq if nq else 0.0
    recall10 = hits10 / nq if nq else 0.0

    return ModelMetrics(
        model_slug=model_slug,
        model_name=model_name,
        dimensions=embedder.dimensions,
        chunk_count=len(chunks),
        recall_at_5=round(recall5, 4),
        recall_at_10=round(recall10, 4),
        latency_ms_p50=round(_percentile(latencies, 50), 3),
        latency_ms_p95=round(_percentile(latencies, 95), 3),
        index_build_ms=round(index_build_ms, 3),
        memory_mb_rss_delta=round(mem_delta, 2) if mem_delta is not None else None,
        composite_score=0.0,
    )


def score_models(metrics: list[ModelMetrics]) -> list[ModelMetrics]:
    lat_p50 = [m.latency_ms_p50 for m in metrics]
    lat_norm = _normalize_inverse(lat_p50)
    build = [m.index_build_ms for m in metrics]
    build_norm = _normalize_inverse(build)
    mem = [m.memory_mb_rss_delta or 0.0 for m in metrics]
    mem_norm = _normalize_inverse(mem)

    scored: list[ModelMetrics] = []
    for i, m in enumerate(metrics):
        composite = (
            W_RECALL10 * m.recall_at_10
            + W_RECALL5 * m.recall_at_5
            + W_LATENCY * lat_norm[i]
            + W_MEMORY * mem_norm[i]
            + W_BUILD * build_norm[i]
        )
        scored.append(ModelMetrics(**{**asdict(m), "composite_score": round(composite, 4)}))
    return sorted(scored, key=lambda x: x.composite_score, reverse=True)


def run_all(*, qdrant_url: str, collection: str) -> dict:
    chunks = _build_chunks()
    queries = _load_queries()
    results: list[ModelMetrics] = []
    for slug, name in _models_to_run():
        print(f"[research] evaluating {slug} ...", flush=True)
        results.append(
            evaluate_model(
                qdrant_url=qdrant_url,
                collection=collection,
                model_slug=slug,
                model_name=name,
                chunks=chunks,
                queries=queries,
            )
        )
    results = score_models(results)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "embedding_benchmark_latest.json"
    payload = {
        "qdrant_url": qdrant_url,
        "collection_prefix": collection,
        "chunk_config": asdict(CHUNK_CONFIG),
        "query_count": len(queries),
        "chunk_count": len(chunks),
        "weights": {
            "recall_at_10": W_RECALL10,
            "recall_at_5": W_RECALL5,
            "latency": W_LATENCY,
            "memory": W_MEMORY,
            "index_build": W_BUILD,
        },
        "models": [asdict(m) for m in results],
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    import os

    url = os.environ.get("QDRANT_URL", "http://localhost:6334")
    run_all(qdrant_url=url, collection="research_lab")
