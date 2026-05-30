import { useCallback, useEffect, useState } from 'react'

/** Lock ingest button for `durationMs` after a successful ingest. */
export function useIngestCooldown(durationMs: number) {
  const [cooldownEnd, setCooldownEnd] = useState(0)
  const [secondsLeft, setSecondsLeft] = useState(0)

  const startCooldown = useCallback(() => {
    const end = Date.now() + durationMs
    setCooldownEnd(end)
    setSecondsLeft(Math.ceil(durationMs / 1000))
  }, [durationMs])

  useEffect(() => {
    if (cooldownEnd <= 0) return

    const tick = () => {
      const remaining = Math.max(0, Math.ceil((cooldownEnd - Date.now()) / 1000))
      setSecondsLeft(remaining)
      if (remaining <= 0) {
        setCooldownEnd(0)
      }
    }

    const immediate = window.setTimeout(tick, 0)
    const id = window.setInterval(tick, 250)
    return () => {
      window.clearTimeout(immediate)
      window.clearInterval(id)
    }
  }, [cooldownEnd])

  return {
    cooldownActive: secondsLeft > 0,
    cooldownSecondsLeft: secondsLeft,
    startCooldown,
  }
}
