import { SECTION } from '../branding'
import type { CorpusSummary, SearchAnalytics, SourceSummary } from '../types'

export type CorpusPanelProps = {
  summary: CorpusSummary | null
  sources: SourceSummary[]
  analytics: SearchAnalytics | null
}

export function CorpusPanel({ summary, sources, analytics }: CorpusPanelProps) {
  return (
    <div className="grid grid-2">
      <article className="panel">
        <h2>{SECTION.l0Corpus}</h2>
        <p>Documents: {summary?.sources_count ?? 0}</p>
        <p>Chunks: {summary?.chunks_count ?? 0}</p>
        <p>Vectors: {summary?.vectors_count ?? 0}</p>
        <p className="small">Collection: {summary?.collection ?? '—'}</p>
      </article>
      <article className="panel">
        <h2>{SECTION.reactiveQuery}</h2>
        <p>Latency: {analytics?.latency_ms ?? 0} ms</p>
        <p>Results: {analytics?.returned_count ?? 0}</p>
        <p>Unique sources: {analytics?.unique_sources ?? 0}</p>
        <p>Top score: {analytics?.top_score?.toFixed(3) ?? '0.000'}</p>
      </article>
      <article className="panel corpus-sources">
        <h2>Sources</h2>
        {sources.length === 0 ? (
          <p className="small">No indexed sources yet.</p>
        ) : (
          <ul className="source-list">
            {sources.slice(0, 50).map((source) => (
              <li key={source.source_path}>
                <span className="mono">{source.source_path}</span>
                <span className="badge">{source.chunk_count} chunks</span>
              </li>
            ))}
          </ul>
        )}
      </article>
    </div>
  )
}
