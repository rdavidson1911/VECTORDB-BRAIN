import { startTransition, useCallback, useEffect, useState } from 'react'
import { AppNav, type AppTab } from './components/AppNav'
import { CorpusPanel } from './components/CorpusPanel'
import { AnalyticsPanel } from './components/AnalyticsPanel'
import { HealthStrip } from './components/HealthStrip'
import { IngestPanel } from './components/IngestPanel'
import { QueryPanel, type QueryFormState } from './components/QueryPanel'
import { ResultsPanel } from './components/ResultsPanel'
import { useIngestCooldown } from './hooks/useIngestCooldown'
import {
  newCorrelationId,
  uiLogHandlerEnd,
  uiLogHandlerStart,
  uiLogInteraction,
  withCorrelation,
} from './logging/uiLogger'
import { api } from './lib/api'
import type {
  CorpusSummary,
  CurationValidateResponse,
  HealthResponse,
  IngestPathResponse,
  QueryMatch,
  QueryRequest,
  SearchAnalytics,
  SourceSummary,
} from './types'

/** Block repeat ingest clicks after a successful run (ms). */
const INGEST_SUCCESS_COOLDOWN_MS = 6000

const INITIAL_QUERY: QueryFormState = {
  query: '',
  limit: 10,
  source_path: '',
  file_type: '',
  document_id: '',
  content_hash: '',
  chunk_strategy: '',
  date_from: '',
  date_to: '',
  text_contains: '',
  min_score_text: '',
}

function App() {
  const [activeTab, setActiveTab] = useState<AppTab>('query')
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [summary, setSummary] = useState<CorpusSummary | null>(null)
  const [sources, setSources] = useState<SourceSummary[]>([])
  const [queryForm, setQueryForm] = useState<QueryFormState>(INITIAL_QUERY)
  const [matches, setMatches] = useState<QueryMatch[]>([])
  const [analytics, setAnalytics] = useState<SearchAnalytics | null>(null)
  const [error, setError] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(false)
  const [ingestPath, setIngestPath] = useState('')
  const [ingestWholeDirectory, setIngestWholeDirectory] = useState(false)
  const [ingestResponse, setIngestResponse] = useState<IngestPathResponse | null>(null)
  const [validateResponse, setValidateResponse] = useState<CurationValidateResponse | null>(null)
  const [ingestBusy, setIngestBusy] = useState(false)
  const [validateBusy, setValidateBusy] = useState(false)
  const { cooldownActive, cooldownSecondsLeft, startCooldown } = useIngestCooldown(
    INGEST_SUCCESS_COOLDOWN_MS,
  )

  const loadDashboardData = useCallback(async (parentCorrelationId?: string) => {
    const correlationId = parentCorrelationId ?? newCorrelationId()
    uiLogHandlerStart('loadDashboardData', correlationId)
    const t0 = performance.now()
    try {
      const ctx = { correlationId }
      const [healthResp, summaryResp, sourceResp] = await Promise.all([
        api.getHealth(ctx),
        api.getCorpusSummary(ctx),
        api.getCorpusSources(ctx),
      ])
      startTransition(() => {
        setHealth(healthResp)
        setSummary(summaryResp)
        setSources(sourceResp)
      })
      uiLogHandlerEnd('loadDashboardData', correlationId, performance.now() - t0, true)
    } catch (err) {
      startTransition(() => {
        setError(err instanceof Error ? err.message : 'Failed to load corpus dashboard.')
      })
      uiLogHandlerEnd('loadDashboardData', correlationId, performance.now() - t0, false, {
        error: err instanceof Error ? err.message : 'unknown',
      })
    }
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadDashboardData()
    }, 0)
    return () => window.clearTimeout(timer)
  }, [loadDashboardData])

  useEffect(() => {
    setValidateResponse(null)
  }, [ingestPath, ingestWholeDirectory])

  async function runSearch() {
    const correlationId = newCorrelationId()
    uiLogInteraction('click', 'Search button', { handler: 'runSearch' }, correlationId)
    if (!queryForm.query.trim()) {
      uiLogInteraction('validation', 'Query text is required', {}, correlationId)
      setError('Query text is required.')
      return
    }
    await withCorrelation(correlationId, async () => {
      uiLogHandlerStart('runSearch', correlationId, { limit: queryForm.limit })
      const t0 = performance.now()
      setLoading(true)
      setError('')
      try {
        const request: QueryRequest = {
          query: queryForm.query,
          limit: queryForm.limit,
        }
        if (queryForm.source_path) request.source_path = queryForm.source_path
        if (queryForm.file_type) request.file_type = queryForm.file_type
        if (queryForm.document_id) request.document_id = queryForm.document_id
        if (queryForm.content_hash) request.content_hash = queryForm.content_hash
        if (queryForm.chunk_strategy) request.chunk_strategy = queryForm.chunk_strategy
        if (queryForm.date_from) request.date_from = queryForm.date_from
        if (queryForm.date_to) request.date_to = queryForm.date_to
        if (queryForm.text_contains) request.text_contains = queryForm.text_contains
        if (queryForm.min_score_text) request.min_score = Number(queryForm.min_score_text)
        const response = await api.query(request, { correlationId })
        setMatches(response.matches)
        setAnalytics(response.analytics)
        setActiveTab('query')
        uiLogHandlerEnd('runSearch', correlationId, performance.now() - t0, true, {
          matches: response.matches.length,
          latency_ms: response.analytics.latency_ms,
        })
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Query failed.')
        uiLogHandlerEnd('runSearch', correlationId, performance.now() - t0, false, {
          error: err instanceof Error ? err.message : 'unknown',
        })
      } finally {
        setLoading(false)
      }
    })
  }

  async function runValidate() {
    const correlationId = newCorrelationId()
    uiLogInteraction('click', 'Validate gate', { path: ingestPath }, correlationId)
    await withCorrelation(correlationId, async () => {
      uiLogHandlerStart('runValidate', correlationId, { path: ingestPath })
      const t0 = performance.now()
      setValidateBusy(true)
      setError('')
      try {
        const trimmed = ingestPath.trim()
        if (!trimmed) {
          throw new Error('Enter a path to validate (file or directory under DATA_SOURCES_PATH).')
        }
        const response = await api.validateCuration(
          { path: trimmed, recursive: ingestWholeDirectory || trimmed.endsWith('/') },
          { correlationId },
        )
        setValidateResponse(response)
        if (response.error_count > 0) {
          setError(
            `Curation gate: ${response.error_count} error(s), ${response.warn_count} warning(s). Fix notes before ingest.`,
          )
        }
        uiLogHandlerEnd('runValidate', correlationId, performance.now() - t0, true, {
          error_count: response.error_count,
          warn_count: response.warn_count,
        })
      } catch (err) {
        setValidateResponse(null)
        setError(err instanceof Error ? err.message : 'Curation validate failed.')
        uiLogHandlerEnd('runValidate', correlationId, performance.now() - t0, false, {
          error: err instanceof Error ? err.message : 'unknown',
        })
      } finally {
        setValidateBusy(false)
      }
    })
  }

  async function runIngest() {
    if (ingestBusy || cooldownActive || loading) return
    if ((validateResponse?.error_count ?? 0) > 0) {
      setError('Curation gate still has errors. Re-validate after fixing source notes.')
      return
    }
    const correlationId = newCorrelationId()
    const mode = ingestWholeDirectory ? 'directory' : 'file'
    uiLogInteraction('click', 'Ingest button', { path: ingestPath, mode }, correlationId)
    await withCorrelation(correlationId, async () => {
      uiLogHandlerStart('runIngest', correlationId, { path: ingestPath, mode })
      const t0 = performance.now()
      setIngestBusy(true)
      setLoading(true)
      setError('')
      try {
        const trimmed = ingestPath.trim()
        if (!trimmed) {
          throw new Error('Enter a file path (or enable directory ingest and provide a folder path).')
        }
        const response = ingestWholeDirectory
          ? await api.ingestPath({ path: trimmed, recursive: true }, { correlationId })
          : await api.ingestFile({ path: trimmed }, { correlationId })
        setIngestResponse(response)
        await loadDashboardData(correlationId)
        startCooldown()
        uiLogHandlerEnd('runIngest', correlationId, performance.now() - t0, true, {
          files_indexed: response.files_indexed,
          chunks_indexed: response.chunks_indexed,
        })
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Ingestion failed.')
        uiLogHandlerEnd('runIngest', correlationId, performance.now() - t0, false, {
          error: err instanceof Error ? err.message : 'unknown',
        })
      } finally {
        setIngestBusy(false)
        setLoading(false)
      }
    })
  }

  return (
    <main className="app-shell">
      <HealthStrip health={health} />
      <AppNav active={activeTab} onChange={setActiveTab} />

      {error && (
        <section className="panel error" role="alert">
          {error}
          <button type="button" className="error-dismiss" onClick={() => setError('')}>
            Dismiss
          </button>
        </section>
      )}

      {activeTab === 'query' && (
        <>
          <QueryPanel
            queryForm={queryForm}
            setQueryForm={setQueryForm}
            analytics={analytics}
            loading={loading}
            onSearch={() => void runSearch()}
            onClear={() => {
              setQueryForm(INITIAL_QUERY)
              setMatches([])
              setAnalytics(null)
            }}
          />
          <ResultsPanel matches={matches} />
        </>
      )}

      {activeTab === 'ingest' && (
        <IngestPanel
          ingestPath={ingestPath}
          setIngestPath={setIngestPath}
          ingestWholeDirectory={ingestWholeDirectory}
          setIngestWholeDirectory={setIngestWholeDirectory}
          ingestBusy={ingestBusy}
          validateBusy={validateBusy}
          cooldownActive={cooldownActive}
          cooldownSecondsLeft={cooldownSecondsLeft}
          loading={loading}
          ingestResponse={ingestResponse}
          validateResponse={validateResponse}
          onValidate={() => void runValidate()}
          onIngest={() => void runIngest()}
        />
      )}

      {activeTab === 'corpus' && (
        <CorpusPanel summary={summary} sources={sources} analytics={analytics} />
      )}

      {activeTab === 'analytics' && <AnalyticsPanel summary={summary} sources={sources} />}
    </main>
  )
}

export default App
