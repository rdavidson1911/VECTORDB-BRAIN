export type UiLogLevel = 'debug' | 'info' | 'warn' | 'error'

export type UiLogCategory = 'ui' | 'api' | 'perf' | 'system'

export type UiLogEntry = {
  id: string
  ts: string
  level: UiLogLevel
  category: UiLogCategory
  event: string
  message: string
  duration_ms?: number
  correlation_id?: string
  meta?: Record<string, string | number | boolean | null | undefined>
}

export type ApiRequestContext = {
  correlationId?: string
  label?: string
}
