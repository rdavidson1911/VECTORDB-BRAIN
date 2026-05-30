import type { UiLogEntry } from './types'

const MAX_ENTRIES = 400

type Listener = () => void

let entries: UiLogEntry[] = []
const listeners = new Set<Listener>()

export function subscribeUiLog(listener: Listener): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function getUiLogEntries(): readonly UiLogEntry[] {
  return entries
}

export function clearUiLog(): void {
  entries = []
  listeners.forEach((l) => l())
}

export function pushUiLog(entry: Omit<UiLogEntry, 'id'>): UiLogEntry {
  const full: UiLogEntry = {
    ...entry,
    id: `log-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
  }
  entries = [full, ...entries].slice(0, MAX_ENTRIES)
  listeners.forEach((l) => l())
  return full
}
