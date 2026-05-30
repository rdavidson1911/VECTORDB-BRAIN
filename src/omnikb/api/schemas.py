from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class IngestPathRequest(BaseModel):
    path: str
    recursive: bool = True
    skip_unchanged: bool = False
    allow_quality_override: bool = False


class IngestFileRequest(BaseModel):
    """Single-file ingest; path is sanitized and confined to the sources root."""

    path: str = Field(min_length=1, max_length=4096)
    skip_unchanged: bool = False
    allow_quality_override: bool = False


class IngestPreviewRequest(BaseModel):
    path: str
    recursive: bool = True
    limit_files: int = Field(default=10, ge=1, le=100)


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=50)
    source_path: str | None = None
    file_type: str | None = None
    document_id: str | None = None
    content_hash: str | None = None
    chunk_strategy: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    text_contains: str | None = None
    min_score: float | None = Field(default=None, ge=0.0, le=1.0)
    include_neighbors: bool = False
    neighbor_window: int = Field(default=1, ge=0, le=3)


class HealthResponse(BaseModel):
    service: Literal["ok", "unavailable"]
    qdrant: Literal["ok", "unavailable"]
    collection: str


class IngestPathResponse(BaseModel):
    files_seen: int
    files_indexed: int
    chunks_indexed: int
    files_skipped: int = 0
    resolved_path: str | None = None


class SourceSummary(BaseModel):
    source_path: str
    file_type: str
    chunk_count: int
    latest_updated_at: str | None = None
    content_hash: str | None = None


class CorpusSummaryResponse(BaseModel):
    collection: str
    vectors_count: int
    chunks_count: int
    sources_count: int
    file_type_counts: dict[str, int]


class QueryMatch(BaseModel):
    id: str
    score: float
    source_path: str | None = None
    file_type: str | None = None
    chunk_index: int | None = None
    content_preview: str | None = None
    text: str | None = None
    content_hash: str | None = None
    updated_at: str | None = None
    indexed_at: str | None = None
    payload: dict = Field(default_factory=dict)


class SearchAnalytics(BaseModel):
    latency_ms: float
    returned_count: int
    unique_sources: int
    top_score: float
    average_score: float


class QueryResponse(BaseModel):
    matches: list[QueryMatch]
    analytics: SearchAnalytics


class ChunkPreview(BaseModel):
    source_path: str
    strategy: str
    chunk_size: int
    chunk_overlap: int
    chunks: list[str]


class IngestPreviewResponse(BaseModel):
    files_seen: int
    previews: list[ChunkPreview]


class CurationValidateRequest(BaseModel):
    path: str
    recursive: bool = True


class CurationIssueOut(BaseModel):
    severity: str
    code: str
    message: str
    path: str | None = None


class CurationValidateResponse(BaseModel):
    entries_scanned: int
    error_count: int
    warn_count: int
    issues: list[CurationIssueOut]


class UiLogEntry(BaseModel):
    ts: str
    level: Literal["debug", "info", "warn", "error"] = "info"
    category: Literal["ui", "api", "perf", "system"] = "ui"
    event: str
    message: str
    duration_ms: float | None = None
    correlation_id: str | None = None
    meta: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class UiLogBatch(BaseModel):
    entries: list[UiLogEntry] = Field(default_factory=list, max_length=200)
