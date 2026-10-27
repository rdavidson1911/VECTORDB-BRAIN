import type { Dispatch, SetStateAction } from 'react'
import { ACTIONS, SECTION } from '../branding'
import type { SearchAnalytics } from '../types'

export type QueryFormState = {
  query: string
  limit: number
  source_path: string
  file_type: string
  document_id: string
  content_hash: string
  chunk_strategy: string
  date_from: string
  date_to: string
  text_contains: string
  min_score_text: string
}

export type QueryPanelProps = {
  queryForm: QueryFormState
  setQueryForm: Dispatch<SetStateAction<QueryFormState>>
  analytics: SearchAnalytics | null
  loading: boolean
  onSearch: () => void
  onClear: () => void
}

export function QueryPanel({
  queryForm,
  setQueryForm,
  analytics,
  loading,
  onSearch,
  onClear,
}: QueryPanelProps) {
  return (
    <section className="panel query-primary">
      <div className="query-primary__head">
        <h2>{SECTION.queryExplore}</h2>
        {analytics && (
          <p className="small query-primary__stats">
            Last: {analytics.latency_ms} ms · {analytics.returned_count} hits · top{' '}
            {analytics.top_score.toFixed(3)}
          </p>
        )}
      </div>
      <label className="field field-query">
        Query
        <input
          value={queryForm.query}
          onChange={(e) => setQueryForm((prev) => ({ ...prev, query: e.target.value }))}
          onKeyDown={(e) => {
            if (e.key === 'Enter') onSearch()
          }}
          placeholder="Find exact text/documents of interest"
          autoComplete="off"
        />
      </label>
      <details className="query-filters">
        <summary>Filters &amp; options</summary>
        <div className="grid grid-4">
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
      </details>
      <div className="actions">
        <button type="button" className="btn-primary" onClick={onSearch} disabled={loading}>
          {ACTIONS.runQuery}
        </button>
        <button type="button" onClick={onClear}>
          {ACTIONS.clearQuery}
        </button>
      </div>
    </section>
  )
}
