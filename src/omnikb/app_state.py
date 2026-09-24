from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from omnikb.adapters.embedder import SentenceTransformerEmbedder
from omnikb.adapters.interaction_store import InteractionStore
from omnikb.adapters.qdrant_store import QdrantStore
from omnikb.config.host_paths import canonical_data_sources_path, resolve_host_sources_root
from omnikb.config.settings import Settings, get_settings
from omnikb.consolidation.trigger import ConsolidationTriggerService
from omnikb.curation.validate import CurationPolicy
from omnikb.services.dreaming_service import DreamingService
from omnikb.services.ingestion_service import IngestionService
from omnikb.services.interaction_service import InteractionService
from omnikb.services.query_service import QueryService


@dataclass(slots=True)
class AppState:
    settings: Settings
    store: QdrantStore
    ingestion_service: IngestionService
    query_service: QueryService
    consolidation_service: ConsolidationTriggerService
    interaction_service: InteractionService
    dreaming_service: DreamingService


def build_state() -> AppState:
    settings = get_settings()
    data_sources_path = canonical_data_sources_path(settings.data_sources_path)
    store = QdrantStore(
        url=settings.qdrant_url,
        collection=settings.qdrant_collection,
        timeout_seconds=settings.qdrant_timeout_seconds,
    )
    embedder = SentenceTransformerEmbedder(model_name=settings.embedding_model)
    interaction_store = InteractionStore(Path(settings.interactions_db_path))
    interaction_service = InteractionService(interaction_store)
    dreaming_service = DreamingService(
        store=store,
        interaction_store=interaction_store,
        idle_minutes=settings.dreaming_idle_minutes,
        edge_min_score=settings.dreaming_edge_min_score,
        candidate_limit=settings.dreaming_candidate_limit,
    )
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
            data_sources_path=data_sources_path,
            host_data_sources_path=resolve_host_sources_root(
                settings.host_data_sources_path,
                data_sources_path,
            ),
            curation_policy=CurationPolicy(
                gate_enabled=settings.curation_gate_enabled,
                gate_roots=list(settings.curation_gate_roots),
            ),
            curation_allow_override=settings.curation_allow_override,
        ),
        query_service=QueryService(
            store=store,
            embedder=embedder,
            interaction_service=interaction_service,
            boost_weight=settings.interaction_boost_weight,
        ),
        consolidation_service=ConsolidationTriggerService(
            enabled=settings.consolidation_enabled,
            min_chunk_threshold=settings.consolidation_min_chunk_threshold,
            dreaming_runner=dreaming_service.run,
            force_dreaming=True,
        ),
        interaction_service=interaction_service,
        dreaming_service=dreaming_service,
    )


_STATE: AppState | None = None


def get_app_state() -> AppState:
    global _STATE
    if _STATE is None:
        _STATE = build_state()
    return _STATE
