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
  payload: Record<string, unknown>
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
