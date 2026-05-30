import type { ApiRequestContext } from '../logging/types'
import {
  uiLogApiEnd,
  uiLogApiError,
  uiLogApiStart,
  getActiveCorrelationId,
} from '../logging/uiLogger'
import type {
  CorpusSummary,
  HealthResponse,
  IngestFileRequest,
  IngestPathRequest,
  IngestPathResponse,
  QueryRequest,
  QueryResponse,
  SourceSummary,
} from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function requestJson<T>(path: string, init?: RequestInit, ctx?: ApiRequestContext): Promise<T> {
  const method = init?.method ?? 'GET'
  const isJsonBodyRequest = method !== 'GET' && method !== 'HEAD'
  const correlationId = ctx?.correlationId ?? getActiveCorrelationId() ?? undefined
  const headers: Record<string, string> = {}
  if (isJsonBodyRequest) {
    headers['Content-Type'] = 'application/json'
  }
  if (correlationId) {
    headers['X-Correlation-Id'] = correlationId
  }
  const mergedHeaders = { ...headers, ...(init?.headers as Record<string, string> | undefined) }

  uiLogApiStart(path, method, { ...ctx, correlationId })
  const started = performance.now()
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: mergedHeaders,
    })
    const durationMs = performance.now() - started
    const serverDurationMs = response.headers.get('X-Request-Duration-Ms')
    if (!response.ok) {
      const message = await response.text()
      uiLogApiEnd(path, method, response.status, durationMs, { ...ctx, correlationId }, serverDurationMs)
      throw new Error(message || `Request failed for ${path}`)
    }
    uiLogApiEnd(path, method, response.status, durationMs, { ...ctx, correlationId }, serverDurationMs)
    return (await response.json()) as T
  } catch (err) {
    const durationMs = performance.now() - started
    if (!(err instanceof Error && err.message.includes('Request failed'))) {
      uiLogApiError(path, method, durationMs, err, { ...ctx, correlationId })
    }
    throw err
  }
}

export const api = {
  getHealth(ctx?: ApiRequestContext) {
    return requestJson<HealthResponse>('/health', undefined, { ...ctx, label: ctx?.label ?? 'dashboard.health' })
  },
  getCorpusSummary(ctx?: ApiRequestContext) {
    return requestJson<CorpusSummary>('/corpus/summary', undefined, {
      ...ctx,
      label: ctx?.label ?? 'dashboard.summary',
    })
  },
  getCorpusSources(ctx?: ApiRequestContext) {
    return requestJson<SourceSummary[]>('/corpus/sources', undefined, {
      ...ctx,
      label: ctx?.label ?? 'dashboard.sources',
    })
  },
  query(body: QueryRequest, ctx?: ApiRequestContext) {
    return requestJson<QueryResponse>(
      '/query',
      { method: 'POST', body: JSON.stringify(body) },
      { ...ctx, label: ctx?.label ?? 'search.query' },
    )
  },
  ingestPath(body: IngestPathRequest, ctx?: ApiRequestContext) {
    return requestJson<IngestPathResponse>(
      '/ingest/path',
      { method: 'POST', body: JSON.stringify(body) },
      { ...ctx, label: ctx?.label ?? 'ingest.path' },
    )
  },
  ingestFile(body: IngestFileRequest, ctx?: ApiRequestContext) {
    return requestJson<IngestPathResponse>(
      '/ingest/file',
      { method: 'POST', body: JSON.stringify(body) },
      { ...ctx, label: ctx?.label ?? 'ingest.file' },
    )
  },
}

export { API_BASE_URL }
