/** Recharts styling aligned with dark UI (`index.css` slate palette). */

export const chartTooltipProps = {
  contentStyle: {
    backgroundColor: "rgba(15, 23, 42, 0.96)",
    border: "1px solid #475569",
    borderRadius: "8px",
    color: "#e2e8f0",
    boxShadow: "0 10px 28px rgba(0, 0, 0, 0.45)",
  },
  labelStyle: {
    color: "#cbd5e1",
    fontWeight: 600,
    marginBottom: "0.25rem",
  },
  itemStyle: { color: "#e2e8f0" },
  wrapperStyle: { outline: "none" },
} as const

export const barCursorFill = "rgba(56, 189, 248, 0.14)"

export const axisTick = { fill: "#94a3b8", fontSize: 11 }

export const axisLine = { stroke: "#475569" }

export const gridStroke = "rgba(148, 163, 184, 0.22)"

export const pieSliceStroke = "#0f172a"

export const pieSliceStrokeWidth = 1

/** Distinct fills for pie segments (cycles if more types than colors). */
export const piePalette = [
  "#6366f1",
  "#8b5cf6",
  "#a78bfa",
  "#0ea5e9",
  "#22d3ee",
  "#2dd4bf",
  "#34d399",
  "#fbbf24",
]

export const barFill = "#38bdf8"
