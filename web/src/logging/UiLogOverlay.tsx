import { useEffect, useMemo, useState } from 'react'
import { clearUiLog, getUiLogEntries, subscribeUiLog } from './uiLogStore'
import { exportUiLogJson, UI_LOGGING_ENABLED } from './uiLogger'
import type { UiLogCategory, UiLogEntry } from './types'

type Filter = 'all' | UiLogCategory

function durationClass(ms: number | undefined): string {
  if (ms === undefined) return ''
  if (ms > 2000) return 'ui-log-ms-slow'
  if (ms > 500) return 'ui-log-ms-warn'
  return 'ui-log-ms-ok'
}

function Row({ entry }: { entry: UiLogEntry }) {
  return (
    <div className={`ui-log-row ui-log-level-${entry.level}`}>
      <span className="ui-log-ts">{entry.ts.slice(11, 23)}</span>
      <span className="ui-log-cat">{entry.category}</span>
      <span className="ui-log-event">{entry.event}</span>
      {entry.duration_ms !== undefined ? (
        <span className={`ui-log-ms ${durationClass(entry.duration_ms)}`}>{entry.duration_ms} ms</span>
      ) : null}
      <span className="ui-log-msg">{entry.message}</span>
      {entry.correlation_id ? (
        <span className="ui-log-corr mono" title={entry.correlation_id}>
          {entry.correlation_id.slice(0, 12)}…
        </span>
      ) : null}
    </div>
  )
}

export function UiLogOverlay() {
  const [open, setOpen] = useState(false)
  const [filter, setFilter] = useState<Filter>('all')
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    if (!UI_LOGGING_ENABLED) return
    return subscribeUiLog(() => setRevision((n) => n + 1))
  }, [])

  const entries = useMemo(() => {
    void revision // subscribeUiLog bumps revision to refresh entries
    const all = [...getUiLogEntries()]
    if (filter === 'all') return all
    return all.filter((e) => e.category === filter)
  }, [filter, revision])

  if (!UI_LOGGING_ENABLED) return null

  return (
    <div className="ui-log-root" data-testid="ui-log-overlay">
      <button
        type="button"
        className="ui-log-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        VECTORDB-BRAIN log {entries.length > 0 ? `(${entries.length})` : ''}
      </button>
      {open ? (
        <div className="ui-log-panel" role="log" aria-live="polite">
          <div className="ui-log-toolbar">
            <select value={filter} onChange={(e) => setFilter(e.target.value as Filter)} aria-label="Filter">
              <option value="all">All</option>
              <option value="ui">UI</option>
              <option value="api">API</option>
              <option value="perf">Perf</option>
              <option value="system">System</option>
            </select>
            <button
              type="button"
              onClick={() => {
                const blob = new Blob([exportUiLogJson()], { type: 'application/json' })
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = `ui-log-${Date.now()}.json`
                a.click()
                URL.revokeObjectURL(url)
              }}
            >
              Export
            </button>
            <button type="button" onClick={() => clearUiLog()}>
              Clear
            </button>
          </div>
          <div className="ui-log-list">
            {entries.length === 0 ? (
              <p className="small">No events yet. Run a query or ingest a Layer 0 source file.</p>
            ) : null}
            {entries.map((entry) => (
              <Row key={entry.id} entry={entry} />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
