from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from omnikb.adapters.document_loader import discover_files
from omnikb.api.schemas import (
    ChunkPreview,
    ConceptHit,
    ConceptListResponse,
    ConsolidationRunRequest,
    ConsolidationRunResponse,
    ConsolidationStatusResponse,
    CorpusSummaryResponse,
    CurationIssueOut,
    CurationValidateRequest,
    CurationValidateResponse,
    HealthResponse,
    IngestFileRequest,
    IngestPathRequest,
    IngestPathResponse,
    IngestPreviewRequest,
    IngestPreviewResponse,
    InteractionEventsRequest,
    InteractionEventsResponse,
    QueryMatch,
    QueryRequest,
    QueryResponse,
    RelationHit,
    SearchAnalytics,
    SourceSummary,
    UiLogBatch,
)
from omnikb.app_state import AppState, get_app_state
from omnikb.consolidation.trigger import ConsolidationBusyError, ConsolidationDisabledError
from omnikb.curation.exceptions import CurationGateError
from omnikb.curation.validate import (
    curation_errors,
    report_to_dict,
    validate_corpus,
    validate_ingest_files,
)
from omnikb.domain.path_safety import UnsafePathError
from omnikb.infra.file_log_writer import append_jsonl

router = APIRouter()


@router.get("/health")
def health(state: AppState = Depends(get_app_state)) -> HealthResponse:
    qdrant_ok = state.store.health()
    return HealthResponse(
        service="ok",
        qdrant="ok" if qdrant_ok else "unavailable",
        collection=state.settings.qdrant_collection,
    )


def _raise_ingest_error(exc: Exception) -> None:
    if isinstance(exc, CurationGateError):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "curation_gate_failed",
                "issues": [
                    {
                        "severity": i.severity,
                        "code": i.code,
                        "message": i.message,
                        "path": i.path,
                    }
                    for i in exc.issues
                ],
            },
        ) from exc
    if isinstance(exc, UnsafePathError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if isinstance(exc, FileNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise exc


def _to_query_match(item: dict) -> QueryMatch:
    result = dict(item)
    payload_dict = dict(result.get("payload") or {})
    return QueryMatch(
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
        cosine_score=(
            float(result["cosine_score"])
            if result.get("cosine_score") is not None
            else (
                float(payload_dict["cosine_score"])
                if payload_dict.get("cosine_score") is not None
                else None
            )
        ),
        boost_norm=(
            float(result["boost_norm"])
            if result.get("boost_norm") is not None
            else (
                float(payload_dict["boost_norm"])
                if payload_dict.get("boost_norm") is not None
                else None
            )
        ),
        hit_count=(
            float(result["hit_count"])
            if result.get("hit_count") is not None
            else (
                float(payload_dict["hit_count"])
                if payload_dict.get("hit_count") is not None
                else None
            )
        ),
        payload=payload_dict,
    )


@router.post("/ingest/file")
def ingest_file(
    payload: IngestFileRequest, state: AppState = Depends(get_app_state)
) -> IngestPathResponse:
    try:
        result = state.ingestion_service.ingest_file(
            payload.path,
            skip_unchanged=payload.skip_unchanged,
            allow_quality_override=payload.allow_quality_override,
        )
    except (UnsafePathError, FileNotFoundError, ValueError, CurationGateError) as exc:
        _raise_ingest_error(exc)
    return IngestPathResponse(
        files_seen=result.files_seen,
        files_indexed=result.files_indexed,
        chunks_indexed=result.chunks_indexed,
        files_skipped=result.files_skipped,
        resolved_path=result.resolved_path,
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
            allow_quality_override=payload.allow_quality_override,
        )
    except (UnsafePathError, FileNotFoundError, ValueError, CurationGateError) as exc:
        _raise_ingest_error(exc)
    return IngestPathResponse(
        files_seen=result.files_seen,
        files_indexed=result.files_indexed,
        chunks_indexed=result.chunks_indexed,
        files_skipped=result.files_skipped,
    )


@router.post("/query")
def query(payload: QueryRequest, state: AppState = Depends(get_app_state)) -> QueryResponse:
    layer1_raw, layer2_raw, layer3_raw, legacy_raw, analytics = state.query_service.query(
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
        include_neighbors=payload.include_neighbors,
        neighbor_window=payload.neighbor_window,
        include_layer3=payload.include_layer3,
    )
    matches = [_to_query_match(item) for item in legacy_raw]
    layer1 = [_to_query_match(item) for item in layer1_raw]
    layer2 = [_to_query_match(item) for item in layer2_raw]
    layer3 = [RelationHit(**item) for item in layer3_raw]
    return QueryResponse(
        matches=matches,
        analytics=SearchAnalytics(**analytics),
        layer1_matches=layer1,
        layer2_boosted_matches=layer2,
        layer3_relations=layer3,
    )


@router.post("/interactions/events")
def interactions_events(
    payload: InteractionEventsRequest, state: AppState = Depends(get_app_state)
) -> InteractionEventsResponse:
    events = [
        {
            "event_type": e.event_type,
            "point_id": e.point_id,
            "query_text_hash": e.query_text_hash,
            "memory_tier": e.memory_tier or "default",
            "ts": e.ts,
        }
        for e in payload.events
    ]
    accepted = state.interaction_service.record_events(session_id=payload.session_id, events=events)
    return InteractionEventsResponse(accepted=accepted)


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
        resolved = state.ingestion_service._resolve_user_path(payload.path)
        files = discover_files(str(resolved), recursive=payload.recursive)
    except (UnsafePathError, FileNotFoundError, ValueError) as exc:
        _raise_ingest_error(exc)
    files_seen = len(files)
    previews = state.ingestion_service.build_previews_for_files(files[: payload.limit_files])
    preview_models = [ChunkPreview(**item) for item in previews]
    return IngestPreviewResponse(files_seen=files_seen, previews=preview_models)


@router.post("/curation/validate")
def curation_validate(
    payload: CurationValidateRequest, state: AppState = Depends(get_app_state)
) -> CurationValidateResponse:
    try:
        resolved = state.ingestion_service._resolve_user_path(payload.path)
    except (UnsafePathError, FileNotFoundError, ValueError) as exc:
        _raise_ingest_error(exc)
    policy = state.ingestion_service.curation_policy
    corpus_root = Path(state.settings.data_sources_path)
    if resolved.is_file():
        report = validate_ingest_files([resolved], corpus_root=corpus_root, policy=policy)
    else:
        report = validate_corpus(
            resolved,
            recursive=payload.recursive,
            policy=policy,
        )
    errors = curation_errors(report)
    warns = [i for i in report.issues if i.severity == "warn"]
    return CurationValidateResponse(
        entries_scanned=report.entries_scanned,
        error_count=len(errors),
        warn_count=len(warns),
        issues=[CurationIssueOut(**item) for item in report_to_dict(report)["issues"]],
    )


@router.post("/consolidation/run", status_code=202)
def consolidation_run(
    payload: ConsolidationRunRequest, state: AppState = Depends(get_app_state)
) -> ConsolidationRunResponse:
    try:
        job = state.consolidation_service.submit_run(
            scope=payload.scope,
            dry_run=payload.dry_run,
            reason=payload.reason,
        )
    except ConsolidationDisabledError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ConsolidationBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ConsolidationRunResponse(
        job_id=job.job_id,
        accepted_at=job.accepted_at,
        status="accepted",
    )


@router.get("/consolidation/status/{job_id}")
def consolidation_status(
    job_id: str, state: AppState = Depends(get_app_state)
) -> ConsolidationStatusResponse:
    job = state.consolidation_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown job_id: {job_id}")
    return ConsolidationStatusResponse(
        job_id=job.job_id,
        accepted_at=job.accepted_at,
        status=job.status,
        scope=job.scope,
        dry_run=job.dry_run,
        reason=job.reason,
        started_at=job.started_at,
        finished_at=job.finished_at,
        message=job.message,
        error=job.error,
    )


@router.get("/relations/concepts")
def list_concepts(
    min_size: int = 2,
    edge_limit: int = 500,
    state: AppState = Depends(get_app_state),
) -> ConceptListResponse:
    """Layer 3 concept nodes from connected components of dreaming edges (pre-HDBSCAN)."""
    if min_size < 2:
        raise HTTPException(status_code=400, detail="min_size must be >= 2")
    if edge_limit < 1 or edge_limit > 5000:
        raise HTTPException(status_code=400, detail="edge_limit must be 1..5000")
    concepts = state.concept_service.list_concepts(
        min_component_size=min_size,
        edge_limit=edge_limit,
    )
    edges = state.interaction_service.store.list_edges(
        score_version=None,
        limit=edge_limit,
    )
    return ConceptListResponse(
        concepts=[
            ConceptHit(
                concept_id=c.concept_id,
                member_point_ids=list(c.member_point_ids),
                edge_count=c.edge_count,
                mean_score=c.mean_score,
                score_version=c.score_version,
                builder=c.builder,
            )
            for c in concepts
        ],
        edge_count=len(edges),
    )


@router.post("/dev/ui-logs")
def ingest_ui_logs(batch: UiLogBatch, state: AppState = Depends(get_app_state)) -> dict[str, int]:
    if not state.settings.ui_logging_enabled:
        raise HTTPException(status_code=404, detail="UI logging is disabled.")
    for entry in batch.entries:
        append_jsonl("ui-client", entry.model_dump())
    return {"accepted": len(batch.entries)}
