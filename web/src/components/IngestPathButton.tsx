import { useCallback, useState, type MouseEvent } from 'react'

const PRESS_FLASH_MS = 220

export type IngestPathButtonProps = {
  onClick: () => void
  /** Label when idle (default: Ingest file) */
  idleLabel?: string
  /** Ingest request in flight */
  busy: boolean
  /** Cooldown after success (impatient double-click guard) */
  cooldownActive: boolean
  cooldownSecondsLeft: number
  disabled?: boolean
}

export function IngestPathButton({
  onClick,
  idleLabel = 'Ingest file',
  busy,
  cooldownActive,
  cooldownSecondsLeft,
  disabled = false,
}: IngestPathButtonProps) {
  const [pressed, setPressed] = useState(false)
  const isDisabled = disabled || busy || cooldownActive

  const flashPress = useCallback(() => {
    setPressed(true)
    window.setTimeout(() => setPressed(false), PRESS_FLASH_MS)
  }, [])

  const handleClick = (event: MouseEvent<HTMLButtonElement>) => {
    if (isDisabled) {
      event.preventDefault()
      return
    }
    flashPress()
    onClick()
  }

  let caption = idleLabel
  if (busy) caption = 'Ingesting…'
  else if (cooldownActive) caption = `Done — wait ${cooldownSecondsLeft}s`

  return (
    <button
      type="button"
      className={[
        'btn-ingest-3d',
        pressed ? 'is-pressed' : '',
        busy ? 'is-busy' : '',
        cooldownActive ? 'is-cooldown' : '',
      ]
        .filter(Boolean)
        .join(' ')}
      onClick={handleClick}
      disabled={isDisabled}
      aria-busy={busy}
      aria-disabled={isDisabled}
      aria-live="polite"
      data-testid="ingest-path-button"
    >
      <span className="btn-ingest-3d__face" aria-hidden="true" />
      <span className="btn-ingest-3d__label">{caption}</span>
      {busy ? <span className="btn-ingest-3d__spinner" aria-hidden="true" /> : null}
    </button>
  )
}
