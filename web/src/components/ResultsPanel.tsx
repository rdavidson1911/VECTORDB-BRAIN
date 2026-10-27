import { SECTION } from '../branding'
import type { QueryMatch } from '../types'

export type ResultsPanelProps = {
  matches: QueryMatch[]
}

export function ResultsPanel({ matches }: ResultsPanelProps) {
  return (
    <section className="panel">
      <h2>{SECTION.queryResults}</h2>
      <div className="results">
        {matches.length === 0 && (
          <p className="small">
            No query results yet — run a query to feed the reactive memory layer.
          </p>
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
  )
}
