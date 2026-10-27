import { PRODUCT_NAME, PRODUCT_TAGLINE } from '../branding'
import type { HealthResponse } from '../types'

export type HealthStripProps = {
  health: HealthResponse | null
}

export function HealthStrip({ health }: HealthStripProps) {
  return (
    <header className="topbar">
      <div className="topbar-brand">
        <h1>{PRODUCT_NAME}</h1>
        <p className="topbar-tagline">{PRODUCT_TAGLINE}</p>
      </div>
      <div className="status-row" aria-live="polite">
        <span className="badge">API: {health?.service ?? '...'}</span>
        <span className="badge">Qdrant: {health?.qdrant ?? '...'}</span>
        <span className="badge">Collection: {health?.collection ?? '...'}</span>
      </div>
    </header>
  )
}
