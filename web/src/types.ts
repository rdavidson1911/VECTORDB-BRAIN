export type HealthResponse = {
  service: 'ok' | 'unavailable'
  qdrant: 'ok' | 'unavailable'
  collection: string
}

export type SourceSummary = {
  source_path: string
  file_type: string
  chunk_count: number
  latest_updated_at?: string | null
  content_hash?: string | null
}

export type CorpusSummary = {
  collection: string
  vectors_count: number
  chunks_count: number
  sources_count: number
  file_type_counts: Record<string, number>
}

export type QueryMatch = {
  id: string
  score: number
  source_path?: string | null
  file_type?: string | null
  chunk_index?: number | null
  content_preview?: string | null
  text?: string | null
  content_hash?: string | null
  updated_at?: string | null
  indexed_at?: string | null
  cosine_score?: number | null
  boost_norm?: number | null
  hit_count?: number | null
  payload: Record<string, unknown>
}

export type RelationHit = {
  src_point_id: string
  dst_point_id: string
  score: number
  score_version: string
  created_at: string
}

export type SearchAnalytics = {
  latency_ms: number
  returned_count: number
  unique_sources: number
  top_score: number
  average_score: number
}

export type QueryResponse = {
  matches: QueryMatch[]
  analytics: SearchAnalytics
  layer1_matches?: QueryMatch[]
  layer2_boosted_matches?: QueryMatch[]
  layer3_relations?: RelationHit[]
}

export type QueryRequest = {
  query: string
  limit: number
  source_path?: string
  file_type?: string
  document_id?: string
  content_hash?: string
  chunk_strategy?: string
  date_from?: string
  date_to?: string
  text_contains?: string
  min_score?: number
  include_neighbors?: boolean
  neighbor_window?: number
  include_layer3?: boolean
}

export type InteractionEvent = {
  event_type: 'query_impression' | 'result_click' | 'result_expand'
  point_id: string
  query_text_hash?: string
  memory_tier?: string
  ts?: string
}

export type InteractionEventsRequest = {
  session_id: string
  events: InteractionEvent[]
}

export type IngestPathRequest = {
  path: string
  recursive: boolean
  skip_unchanged?: boolean
}

export type IngestFileRequest = {
  path: string
  skip_unchanged?: boolean
}

export type IngestPathResponse = {
  files_seen: number
  files_indexed: number
  chunks_indexed: number
  files_skipped: number
  resolved_path?: string | null
}

export type ConsolidationRunRequest = {
  scope?: string | null
  dry_run?: boolean
  reason?: string | null
}

export type ConsolidationRunAccepted = {
  job_id: string
  accepted_at: string
  status: 'accepted'
}

export type ConsolidationJobResponse = {
  job_id: string
  status: string
  accepted_at: string
  scope?: string | null
  dry_run?: boolean
  reason?: string | null
  started_at?: string | null
  finished_at?: string | null
  message?: string | null
  error?: string | null
}
