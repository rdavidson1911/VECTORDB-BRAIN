import { ACTIONS, SECTION } from '../branding'
import type { CurationValidateResponse, IngestPathResponse } from '../types'
import { IngestPathButton } from './IngestPathButton'

export type IngestPanelProps = {
  ingestPath: string
  setIngestPath: (value: string) => void
  ingestWholeDirectory: boolean
  setIngestWholeDirectory: (value: boolean) => void
  ingestBusy: boolean
  validateBusy: boolean
  cooldownActive: boolean
  cooldownSecondsLeft: number
  loading: boolean
  ingestResponse: IngestPathResponse | null
  validateResponse: CurationValidateResponse | null
  onValidate: () => void
  onIngest: () => void
}

export function IngestPanel({
  ingestPath,
  setIngestPath,
  ingestWholeDirectory,
  setIngestWholeDirectory,
  ingestBusy,
  validateBusy,
  cooldownActive,
  cooldownSecondsLeft,
  loading,
  ingestResponse,
  validateResponse,
  onValidate,
  onIngest,
}: IngestPanelProps) {
  const gateBlocked = (validateResponse?.error_count ?? 0) > 0

  return (
    <section className="panel">
      <h2>{SECTION.l0Ingest}</h2>
      <p className="small">
        Desktop path ingest against the private API host. Mobile upload → staging is a follow-up
        (ADR-0002). Run the curation gate dry-run before indexing curated roots.
      </p>
      <label className="field">
        {ingestWholeDirectory ? 'Source directory' : 'Source file'}
        <input
          value={ingestPath}
          onChange={(e) => setIngestPath(e.target.value)}
          placeholder={
            ingestWholeDirectory
              ? '/data/sources/curated or host path under DATA_SOURCES_PATH'
              : '/data/sources/curated/my-doc.md'
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
      <div className="actions actions-wrap">
        <button
          type="button"
          onClick={onValidate}
          disabled={validateBusy || ingestBusy || loading}
        >
          {validateBusy ? 'Validating…' : ACTIONS.validateGate}
        </button>
        <IngestPathButton
          idleLabel={ingestWholeDirectory ? ACTIONS.ingestDirectory : ACTIONS.ingestFile}
          busy={ingestBusy}
          cooldownActive={cooldownActive}
          cooldownSecondsLeft={cooldownSecondsLeft}
          disabled={(loading && !ingestBusy && !cooldownActive) || gateBlocked}
          onClick={onIngest}
        />
      </div>
      {gateBlocked && (
        <p className="gate-banner" role="status">
          Gate blocked ingest ({validateResponse?.error_count} error
          {(validateResponse?.error_count ?? 0) === 1 ? '' : 's'}). Fix source notes, then
          re-validate.
        </p>
      )}
      {validateResponse && (
        <div className="validate-summary">
          <h3>{SECTION.curationValidate}</h3>
          <p className="small">
            Scanned {validateResponse.entries_scanned} · Errors {validateResponse.error_count} ·
            Warnings {validateResponse.warn_count}
          </p>
          {validateResponse.issues.length > 0 && (
            <ul className="issue-list">
              {validateResponse.issues.slice(0, 40).map((issue, index) => (
                <li
                  key={`${issue.code}-${issue.path ?? ''}-${index}`}
                  className={
                    issue.severity === 'error' ? 'issue-list__item is-error' : 'issue-list__item'
                  }
                >
                  <span className="badge">{issue.severity}</span>{' '}
                  <span className="mono">{issue.code}</span> {issue.message}
                  {issue.path ? <span className="mono"> — {issue.path}</span> : null}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {ingestResponse && (
        <div className="small ingest-summary">
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
    </section>
  )
}
