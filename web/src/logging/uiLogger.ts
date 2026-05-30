import { API_BASE_URL } from '../lib/api'
import { getUiLogEntries, pushUiLog } from './uiLogStore'
import type { ApiRequestContext, UiLogCategory, UiLogLevel } from './types'

export const UI_LOGGING_ENABLED =
  import.meta.env.DEV || import.meta.env.VITE_UI_LOGGING === 'true'

export const UI_LOG_TO_SERVER =
  UI_LOGGING_ENABLED && import.meta.env.VITE_UI_LOG_TO_SERVER !== 'false'

let activeCorrelationId: string | null = null
const inFlight = new Map<string, number>()

const pendingServerFlush: Omit<import('./types').UiLogEntry, 'id'>[] = []
let flushTimer: number | null = null

export function newCorrelationId(): string {
  return `ui-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}

export function getActiveCorrelationId(): string | null {
  return activeCorrelationId
}

export function withCorrelation<T>(correlationId: string, fn: () => Promise<T>): Promise<T> {
  const previous = activeCorrelationId
  activeCorrelationId = correlationId
  return fn().finally(() => {
    activeCorrelationId = previous
  })
}

function scheduleServerFlush(): void {
  if (!UI_LOG_TO_SERVER || pendingServerFlush.length === 0) return
  if (flushTimer !== null) return
  flushTimer = window.setTimeout(() => {
    flushTimer = null
    void flushToServer()
  }, 1500)
}

async function flushToServer(): Promise<void> {
  if (pendingServerFlush.length === 0) return
  const batch = pendingServerFlush.splice(0, 200)
  try {
    await fetch(`${API_BASE_URL}/dev/ui-logs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entries: batch }),
    })
  } catch {
    // Best-effort; overlay + console remain source of truth in dev.
  }
}

function record(
  level: UiLogLevel,
  category: UiLogCategory,
  event: string,
  message: string,
  extra?: {
    duration_ms?: number
    correlation_id?: string
    meta?: Record<string, string | number | boolean | null | undefined>
  },
): void {
  if (!UI_LOGGING_ENABLED) return

  const row = {
    ts: new Date().toISOString(),
    level,
    category,
    event,
    message,
    duration_ms: extra?.duration_ms,
    correlation_id: extra?.correlation_id ?? activeCorrelationId ?? undefined,
    meta: extra?.meta,
  }

  pushUiLog(row)
  pendingServerFlush.push(row)
  scheduleServerFlush()

  const prefix = `[ui-log:${category}] ${event}`
  if (level === 'error') console.error(prefix, message, extra?.meta)
  else if (level === 'warn') console.warn(prefix, message, extra?.meta)
  else console.debug(prefix, message, extra?.meta)
}

export function uiLogInteraction(
  event: string,
  message: string,
  meta?: Record<string, string | number | boolean | null | undefined>,
  correlationId?: string,
): void {
  record('info', 'ui', event, message, {
    correlation_id: correlationId ?? activeCorrelationId ?? undefined,
    meta,
  })
}

export function uiLogHandlerStart(
  handler: string,
  correlationId: string,
  meta?: Record<string, string | number | boolean | null | undefined>,
): void {
  const count = (inFlight.get(handler) ?? 0) + 1
  inFlight.set(handler, count)
  if (count > 1) {
    record('warn', 'perf', 'handler.concurrent', `${handler} invoked while already in flight (${count})`, {
      correlation_id: correlationId,
      meta: { ...meta, in_flight: count },
    })
  }
  record('info', 'ui', `${handler}.start`, `Handler ${handler} started`, {
    correlation_id: correlationId,
    meta,
  })
}

export function uiLogHandlerEnd(
  handler: string,
  correlationId: string,
  durationMs: number,
  ok: boolean,
  meta?: Record<string, string | number | boolean | null | undefined>,
): void {
  const count = inFlight.get(handler) ?? 1
  inFlight.set(handler, Math.max(0, count - 1))
  record(ok ? 'info' : 'error', 'perf', `${handler}.end`, `Handler ${handler} finished`, {
    duration_ms: Math.round(durationMs * 100) / 100,
    correlation_id: correlationId,
    meta: { ...meta, ok },
  })
}

export function uiLogApiStart(path: string, method: string, ctx?: ApiRequestContext): void {
  record('debug', 'api', 'fetch.start', `${method} ${path}`, {
    correlation_id: ctx?.correlationId ?? activeCorrelationId ?? undefined,
    meta: { path, method, label: ctx?.label },
  })
}

export function uiLogApiEnd(
  path: string,
  method: string,
  status: number,
  durationMs: number,
  ctx?: ApiRequestContext,
  serverDurationMs?: string | null,
): void {
  const level: UiLogLevel = status >= 400 ? 'error' : durationMs > 2000 ? 'warn' : 'info'
  record(level, 'api', 'fetch.end', `${method} ${path} → ${status}`, {
    duration_ms: Math.round(durationMs * 100) / 100,
    correlation_id: ctx?.correlationId ?? activeCorrelationId ?? undefined,
    meta: {
      path,
      method,
      status,
      label: ctx?.label,
      server_duration_ms: serverDurationMs ?? undefined,
    },
  })
}

export function uiLogApiError(
  path: string,
  method: string,
  durationMs: number,
  error: unknown,
  ctx?: ApiRequestContext,
): void {
  const message = error instanceof Error ? error.message : String(error)
  record('error', 'api', 'fetch.error', `${method} ${path}: ${message}`, {
    duration_ms: Math.round(durationMs * 100) / 100,
    correlation_id: ctx?.correlationId ?? activeCorrelationId ?? undefined,
    meta: { path, method, label: ctx?.label },
  })
}

export function exportUiLogJson(): string {
  return JSON.stringify(getUiLogEntries(), null, 2)
}
