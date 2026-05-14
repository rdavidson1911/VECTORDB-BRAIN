from __future__ import annotations

from dataclasses import dataclass

from omnikb.adapters.embedder import SentenceTransformerEmbedder
from omnikb.adapters.qdrant_store import QdrantStore
from omnikb.config.settings import Settings, get_settings
from omnikb.services.ingestion_service import IngestionService
from omnikb.services.query_service import QueryService


@dataclass(slots=True)
class AppState:
    settings: Settings
    store: QdrantStore
    ingestion_service: IngestionService
    query_service: QueryService


def build_state() -> AppState:
    settings = get_settings()
    store = QdrantStore(
        url=settings.qdrant_url,
        collection=settings.qdrant_collection,
        timeout_seconds=settings.qdrant_timeout_seconds,
    )
    embedder = SentenceTransformerEmbedder(model_name=settings.embedding_model)
    return AppState(
        settings=settings,
        store=store,
        ingestion_service=IngestionService(
            store=store,
            embedder=embedder,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            chunk_strategy=settings.chunk_strategy,
            embedding_model=settings.embedding_model,
            pipeline_version=settings.pipeline_version,
            normalization_profile=settings.normalization_profile,
        ),
        query_service=QueryService(store=store, embedder=embedder),
    )


_STATE: AppState | None = None


def get_app_state() -> AppState:
    global _STATE
    if _STATE is None:
        _STATE = build_state()
    return _STATE
