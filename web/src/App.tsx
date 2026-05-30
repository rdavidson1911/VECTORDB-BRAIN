import { startTransition, useCallback, useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  axisLine,
  axisTick,
  barCursorFill,
  barFill,
  chartTooltipProps,
  gridStroke,
  piePalette,
  pieSliceStroke,
  pieSliceStrokeWidth,
} from './chartTheme'
import { ACTIONS, PRODUCT_NAME, PRODUCT_TAGLINE, SECTION } from './branding'
import { Multivariate3DTemplate, type MultivariatePoint } from './charts'
import { ChartErrorBoundary } from './components/ChartErrorBoundary'
import { IngestPathButton } from './components/IngestPathButton'
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
  HealthResponse,
  IngestPathResponse,
  QueryMatch,
  QueryRequest,
  SearchAnalytics,
  SourceSummary,
} from './types'

type QueryForm = QueryRequest & {
  min_score_text: string
}

/** Block repeat ingest clicks after a successful run (ms). */
const INGEST_SUCCESS_COOLDOWN_MS = 6000

const INITIAL_QUERY: QueryForm = {
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
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [summary, setSummary] = useState<CorpusSummary | null>(null)
  const [sources, setSources] = useState<SourceSummary[]>([])
  const [queryForm, setQueryForm] = useState<QueryForm>(INITIAL_QUERY)
  const [matches, setMatches] = useState<QueryMatch[]>([])
  const [analytics, setAnalytics] = useState<SearchAnalytics | null>(null)
  const [error, setError] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(false)
  const [ingestPath, setIngestPath] = useState('')
  const [ingestWholeDirectory, setIngestWholeDirectory] = useState(false)
  const [ingestResponse, setIngestResponse] = useState<IngestPathResponse | null>(null)
  const [ingestBusy, setIngestBusy] = useState(false)
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

  async function runIngest() {
    if (ingestBusy || cooldownActive || loading) return
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

  const fileTypeChart = useMemo(
    () =>
      Object.entries(summary?.file_type_counts ?? {}).map(([name, value]) => ({
        name,
        value,
      })),
    [summary],
  )

  const sourceChart = useMemo(
    () =>
      sources.slice(0, 12).map((source) => ({
        name: source.source_path.split('/').pop() ?? source.source_path,
        chunks: source.chunk_count,
      })),
    [sources],
  )

  const multivariate3d = useMemo(() => {
    const liveTitles = { x: 'Source order', y: 'Chunk count', z: 'Path length (chars)' }
    if (sources.length > 0) {
      const points: MultivariatePoint[] = sources.slice(0, 80).map((s, index) => ({
        x: index,
        y: s.chunk_count,
        z: s.source_path.length,
        value: s.chunk_count,
        magnitude: Math.sqrt(s.chunk_count + 1),
        label: s.source_path.split('/').pop() ?? s.source_path,
        id: `${index}-${s.source_path}`,
        meta: { chunks: s.chunk_count, path: s.source_path },
      }))
      return { points, axisTitles: liveTitles }
    }
    const demoTitles = { x: 'cos(t) · radius', y: 'sin(t) · radius', z: 'Depth' }
    const points: MultivariatePoint[] = Array.from({ length: 48 }, (_, i) => {
      const t = (i / 12) * Math.PI
      const radius = 6 + (i % 3)
      return {
        x: Math.cos(t) * radius,
        y: Math.sin(t) * radius,
        z: i * 0.35,
        value: i,
        magnitude: 2 + (i % 6),
        label: `synthetic-${i}`,
        id: `synthetic-${i}`,
        meta: { series: 'demo' },
      }
    })
    return { points, axisTitles: demoTitles }
  }, [sources])

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="topbar-brand">
          <h1>{PRODUCT_NAME}</h1>
          <p className="topbar-tagline">{PRODUCT_TAGLINE}</p>
        </div>
        <div className="status-row">
          <span className="badge">API: {health?.service ?? '...'}</span>
          <span className="badge">Qdrant: {health?.qdrant ?? '...'}</span>
          <span className="badge">Collection: {health?.collection ?? '...'}</span>
        </div>
      </header>

      {error && <section className="panel error">{error}</section>}

      <section className="grid grid-3">
        <article className="panel">
          <h2>{SECTION.l0Corpus}</h2>
          <p>Documents: {summary?.sources_count ?? 0}</p>
          <p>Chunks: {summary?.chunks_count ?? 0}</p>
          <p>Vectors: {summary?.vectors_count ?? 0}</p>
        </article>
        <article className="panel">
          <h2>{SECTION.reactiveQuery}</h2>
          <p>Latency: {analytics?.latency_ms ?? 0} ms</p>
          <p>Results: {analytics?.returned_count ?? 0}</p>
          <p>Unique sources: {analytics?.unique_sources ?? 0}</p>
          <p>Top score: {analytics?.top_score?.toFixed(3) ?? '0.000'}</p>
        </article>
        <article className="panel">
          <h2>{SECTION.l0Ingest}</h2>
          <label className="field">
            {ingestWholeDirectory ? 'Source directory' : 'Source file'}
            <input
              value={ingestPath}
              onChange={(e) => setIngestPath(e.target.value)}
              placeholder={
                ingestWholeDirectory
                  ? '/data/sources or I:\\VECTORDB-BRAIN\\data\\sources'
                  : '/data/sources/my-doc.md or I:\\...\\data\\sources\\my-doc.md'
              }
            />
          </label>
          <label className="field checkbox-row">
            <input
              type="checkbox"
              checked={ingestWholeDirectory}
              onChange={(e) => setIngestWholeDirectory(e.target.checked)}
            />
            Ingest entire directory (advanced)
          </label>
          <IngestPathButton
            idleLabel={ingestWholeDirectory ? 'Ingest directory' : 'Ingest file'}
            busy={ingestBusy}
            cooldownActive={cooldownActive}
            cooldownSecondsLeft={cooldownSecondsLeft}
            disabled={loading && !ingestBusy && !cooldownActive}
            onClick={() => void runIngest()}
          />
          {ingestResponse && (
            <div className="small">
              Seen {ingestResponse.files_seen} | Indexed {ingestResponse.files_indexed} | Skipped{' '}
              {ingestResponse.files_skipped ?? 0} | Chunks {ingestResponse.chunks_indexed}
              {ingestResponse.resolved_path ? (
                <>
                  <br />
                  Resolved: {ingestResponse.resolved_path}
                </>
              ) : null}
            </div>
          )}
        </article>
      </section>

      <section className="panel">
        <h2>{SECTION.queryExplore}</h2>
        <div className="grid grid-4">
          <label className="field">
            Query
            <input
              value={queryForm.query}
              onChange={(e) => setQueryForm((prev) => ({ ...prev, query: e.target.value }))}
              placeholder="Find exact text/documents of interest"
            />
          </label>
          <label className="field">
            Text contains
            <input
              value={queryForm.text_contains}
              onChange={(e) =>
                setQueryForm((prev) => ({ ...prev, text_contains: e.target.value }))
              }
              placeholder="post-filter text fragment"
            />
          </label>
          <label className="field">
            Source path
            <input
              value={queryForm.source_path}
              onChange={(e) => setQueryForm((prev) => ({ ...prev, source_path: e.target.value }))}
              placeholder="/data/sources/file.md"
            />
          </label>
          <label className="field">
            File type
            <input
              value={queryForm.file_type}
              onChange={(e) => setQueryForm((prev) => ({ ...prev, file_type: e.target.value }))}
              placeholder="md, txt, pdf"
            />
          </label>
          <label className="field">
            Date added from
            <input
              type="date"
              value={queryForm.date_from}
              onChange={(e) => setQueryForm((prev) => ({ ...prev, date_from: e.target.value }))}
            />
          </label>
          <label className="field">
            Date added to
            <input
              type="date"
              value={queryForm.date_to}
              onChange={(e) => setQueryForm((prev) => ({ ...prev, date_to: e.target.value }))}
            />
          </label>
          <label className="field">
            Min score
            <input
              type="number"
              step="0.01"
              min="0"
              max="1"
              value={queryForm.min_score_text}
              onChange={(e) =>
                setQueryForm((prev) => ({ ...prev, min_score_text: e.target.value }))
              }
            />
          </label>
          <label className="field">
            Limit
            <input
              type="number"
              min="1"
              max="50"
              value={queryForm.limit}
              onChange={(e) =>
                setQueryForm((prev) => ({ ...prev, limit: Number(e.target.value || 10) }))
              }
            />
          </label>
          <label className="field">
            Document ID
            <input
              value={queryForm.document_id}
              onChange={(e) => setQueryForm((prev) => ({ ...prev, document_id: e.target.value }))}
              placeholder="sha256(source_path)"
            />
          </label>
          <label className="field">
            Content hash
            <input
              value={queryForm.content_hash}
              onChange={(e) => setQueryForm((prev) => ({ ...prev, content_hash: e.target.value }))}
            />
          </label>
          <label className="field">
            Chunk strategy
            <input
              value={queryForm.chunk_strategy}
              onChange={(e) =>
                setQueryForm((prev) => ({ ...prev, chunk_strategy: e.target.value }))
              }
              placeholder="recursive_char_v1"
            />
          </label>
        </div>
        <div className="actions">
          <button onClick={() => void runSearch()} disabled={loading}>
            {ACTIONS.runQuery}
          </button>
          <button
            onClick={() => {
              setQueryForm(INITIAL_QUERY)
              setMatches([])
              setAnalytics(null)
            }}
          >
            {ACTIONS.clearQuery}
          </button>
        </div>
      </section>

      <section className="grid grid-2">
        <article className="panel chart-panel">
          <h2>{SECTION.l0FileTypes}</h2>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
              <Pie
                data={fileTypeChart}
                dataKey="value"
                nameKey="name"
                outerRadius={90}
                stroke={pieSliceStroke}
                strokeWidth={pieSliceStrokeWidth}
              >
                {fileTypeChart.map((entry, i) => (
                  <Cell key={entry.name} fill={piePalette[i % piePalette.length]} />
                ))}
              </Pie>
              <Tooltip {...chartTooltipProps} />
            </PieChart>
          </ResponsiveContainer>
        </article>
        <article className="panel chart-panel">
          <h2>{SECTION.l0TopSources}</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={sourceChart} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
              <XAxis dataKey="name" hide />
              <YAxis tick={axisTick} axisLine={axisLine} tickLine={axisLine} width={36} />
              <Tooltip {...chartTooltipProps} cursor={{ fill: barCursorFill }} />
              <Bar dataKey="chunks" fill={barFill} radius={[4, 4, 0, 0]} maxBarSize={48} />
            </BarChart>
          </ResponsiveContainer>
        </article>
      </section>

      <section className="panel chart-panel chart-3d-panel">
        <h2>{SECTION.exploration3d}</h2>
        <p className="small">
          {PRODUCT_NAME} exploration surface — Plotly <code>scatter3d</code> over{' '}
          <code>MultivariatePoint[]</code>. Layer 0 corpus drives live axes; an empty corpus shows
          a synthetic helix until you ingest sources and run queries that shape the memory layer.
        </p>
        <ChartErrorBoundary
          chartName="Multivariate3DTemplate"
          fallbackMessage="Plotly failed to load or render. Check the Console for stack details; restart with npm run dev:fresh after Vite config changes."
        >
          <Multivariate3DTemplate
            points={multivariate3d.points}
            axisTitles={multivariate3d.axisTitles}
            height={440}
            colorBy="value"
            traceName="corpus-demo"
          />
        </ChartErrorBoundary>
      </section>

      <section className="panel">
        <h2>{SECTION.queryResults}</h2>
        <div className="results">
          {matches.length === 0 && (
            <p className="small">No query results yet — run a query to feed the reactive memory layer.</p>
          )}
          {matches.map((match) => (
            <article key={match.id} className="result-card">
              <div className="result-head">
                <span className="badge">Score: {match.score.toFixed(4)}</span>
                <span className="badge">{match.file_type ?? 'unknown'}</span>
                <span className="badge">Chunk: {match.chunk_index ?? '-'}</span>
              </div>
              <p className="mono">{match.source_path}</p>
              <p>{match.content_preview || match.text || ''}</p>
              <details>
                <summary>Full text and metadata</summary>
                <pre>{match.text}</pre>
                <pre>{JSON.stringify(match.payload, null, 2)}</pre>
              </details>
            </article>
          ))}
        </div>
      </section>
    </main>
  )
}

export default App
