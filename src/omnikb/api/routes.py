from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from omnikb.adapters.document_loader import discover_files
from omnikb.api.schemas import (
    ChunkPreview,
    CorpusSummaryResponse,
    HealthResponse,
    IngestPathRequest,
    IngestPathResponse,
    IngestPreviewRequest,
    IngestPreviewResponse,
    QueryMatch,
    QueryRequest,
    QueryResponse,
    SearchAnalytics,
    SourceSummary,
)
from omnikb.app_state import AppState, get_app_state

router = APIRouter()


@router.get("/health")
def health(state: AppState = Depends(get_app_state)) -> HealthResponse:
    qdrant_ok = state.store.health()
    return HealthResponse(
        service="ok",
        qdrant="ok" if qdrant_ok else "unavailable",
        collection=state.settings.qdrant_collection,
    )


@router.post("/ingest/path")
def ingest_path(
    payload: IngestPathRequest, state: AppState = Depends(get_app_state)
) -> IngestPathResponse:
    try:
        result = state.ingestion_service.ingest_path(
            payload.path,
            recursive=payload.recursive,
            skip_unchanged=payload.skip_unchanged,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return IngestPathResponse(
        files_seen=result.files_seen,
        files_indexed=result.files_indexed,
        chunks_indexed=result.chunks_indexed,
        files_skipped=result.files_skipped,
    )


@router.post("/query")
def query(payload: QueryRequest, state: AppState = Depends(get_app_state)) -> QueryResponse:
    raw_matches, analytics = state.query_service.query(
        text=payload.query,
        limit=payload.limit,
        source_path=payload.source_path,
        file_type=payload.file_type,
        document_id=payload.document_id,
        content_hash=payload.content_hash,
        chunk_strategy=payload.chunk_strategy,
        date_from=payload.date_from,
        date_to=payload.date_to,
        text_contains=payload.text_contains,
        min_score=payload.min_score,
    )
    matches = []
    for item in raw_matches:
        result = dict(item)
        payload_dict = dict(result.get("payload") or {})
        matches.append(
            QueryMatch(
                id=str(result.get("id", "")),
                score=float(result.get("score", 0.0)),
                source_path=payload_dict.get("source_path"),
                file_type=payload_dict.get("file_type"),
                chunk_index=payload_dict.get("chunk_index"),
                content_preview=payload_dict.get("content_preview"),
                text=payload_dict.get("text"),
                content_hash=payload_dict.get("content_hash"),
                updated_at=payload_dict.get("updated_at"),
                indexed_at=payload_dict.get("indexed_at"),
                payload=payload_dict,
            )
        )
    return QueryResponse(matches=matches, analytics=SearchAnalytics(**analytics))


@router.get("/collections/{name}/stats")
def collection_stats(name: str, state: AppState = Depends(get_app_state)) -> dict:
    if name != state.settings.qdrant_collection:
        raise HTTPException(status_code=404, detail=f"Collection '{name}' is not configured.")
    return state.store.collection_stats()


@router.get("/corpus/sources")
def corpus_sources(state: AppState = Depends(get_app_state)) -> list[SourceSummary]:
    return [SourceSummary(**item) for item in state.store.list_sources()]


@router.get("/corpus/summary")
def corpus_summary(state: AppState = Depends(get_app_state)) -> CorpusSummaryResponse:
    return CorpusSummaryResponse(**state.store.corpus_summary())


@router.post("/ingest/preview")
def ingest_preview(
    payload: IngestPreviewRequest, state: AppState = Depends(get_app_state)
) -> IngestPreviewResponse:
    try:
        files = discover_files(payload.path, recursive=payload.recursive)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    files_seen = len(files)
    previews = state.ingestion_service.build_previews_for_files(files[: payload.limit_files])
    preview_models = [ChunkPreview(**item) for item in previews]
    return IngestPreviewResponse(files_seen=files_seen, previews=preview_models)
