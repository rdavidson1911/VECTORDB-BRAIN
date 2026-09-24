"""Layer 3 concept service: build concept nodes from persisted dreaming edges."""

from __future__ import annotations

from omnikb.adapters.interaction_store import InteractionStore
from omnikb.domain.concept_nodes import ConceptNode, build_concepts_from_edges
from omnikb.services.dreaming_service import SCORE_VERSION


class ConceptService:
    def __init__(self, store: InteractionStore) -> None:
        self.store = store

    def list_concepts(
        self,
        *,
        min_component_size: int = 2,
        score_version: str | None = SCORE_VERSION,
        edge_limit: int = 500,
    ) -> list[ConceptNode]:
        edges = self.store.list_edges(score_version=score_version, limit=edge_limit)
        return build_concepts_from_edges(
            edges,
            min_component_size=min_component_size,
            score_version=score_version,
        )
