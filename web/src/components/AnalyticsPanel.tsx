import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  axisLine,
  axisTick,
  barCursorFill,
  barFill,
  chartTooltipProps,
  gridStroke,
  piePalette,
  pieSliceStroke,
  pieSliceStrokeWidth,
} from '../chartTheme'
import { Multivariate3DTemplate, type MultivariatePoint } from '../charts'
import { PRODUCT_NAME, SECTION } from '../branding'
import type { CorpusSummary, SourceSummary } from '../types'
import { ChartErrorBoundary } from './ChartErrorBoundary'

export type AnalyticsPanelProps = {
  summary: CorpusSummary | null
  sources: SourceSummary[]
}

export function AnalyticsPanel({ summary, sources }: AnalyticsPanelProps) {
  const fileTypeChart = Object.entries(summary?.file_type_counts ?? {}).map(([name, value]) => ({
    name,
    value,
  }))

  const sourceChart = sources.slice(0, 12).map((source) => ({
    name: source.source_path.split('/').pop() ?? source.source_path,
    chunks: source.chunk_count,
  }))

  const liveTitles = { x: 'Source order', y: 'Chunk count', z: 'Path length (chars)' }
  let multivariate3d: { points: MultivariatePoint[]; axisTitles: typeof liveTitles }
  if (sources.length > 0) {
    const points: MultivariatePoint[] = sources.slice(0, 80).map((s, index) => ({
      x: index,
      y: s.chunk_count,
      z: s.source_path.length,
      value: s.chunk_count,
      magnitude: Math.sqrt(s.chunk_count + 1),
      label: s.source_path.split('/').pop() ?? s.source_path,
      id: `${index}-${s.source_path}`,
      meta: { chunks: s.chunk_count, path: s.source_path },
    }))
    multivariate3d = { points, axisTitles: liveTitles }
  } else {
    const demoTitles = { x: 'cos(t) · radius', y: 'sin(t) · radius', z: 'Depth' }
    const points: MultivariatePoint[] = Array.from({ length: 48 }, (_, i) => {
      const t = (i / 12) * Math.PI
      const radius = 6 + (i % 3)
      return {
        x: Math.cos(t) * radius,
        y: Math.sin(t) * radius,
        z: i * 0.35,
        value: i,
        magnitude: 2 + (i % 6),
        label: `synthetic-${i}`,
        id: `synthetic-${i}`,
        meta: { series: 'demo' },
      }
    })
    multivariate3d = { points, axisTitles: demoTitles }
  }

  return (
    <div className="analytics-stack">
      <section className="grid grid-2 analytics-charts">
        <article className="panel chart-panel">
          <h2>{SECTION.l0FileTypes}</h2>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
              <Pie
                data={fileTypeChart}
                dataKey="value"
                nameKey="name"
                outerRadius={90}
                stroke={pieSliceStroke}
                strokeWidth={pieSliceStrokeWidth}
              >
                {fileTypeChart.map((entry, i) => (
                  <Cell key={entry.name} fill={piePalette[i % piePalette.length]} />
                ))}
              </Pie>
              <Tooltip {...chartTooltipProps} />
            </PieChart>
          </ResponsiveContainer>
        </article>
        <article className="panel chart-panel">
          <h2>{SECTION.l0TopSources}</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={sourceChart} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
              <XAxis dataKey="name" hide />
              <YAxis tick={axisTick} axisLine={axisLine} tickLine={axisLine} width={36} />
              <Tooltip {...chartTooltipProps} cursor={{ fill: barCursorFill }} />
              <Bar dataKey="chunks" fill={barFill} radius={[4, 4, 0, 0]} maxBarSize={48} />
            </BarChart>
          </ResponsiveContainer>
        </article>
      </section>

      <section className="panel chart-panel chart-3d-panel analytics-3d">
        <h2>{SECTION.exploration3d}</h2>
        <p className="small">
          {PRODUCT_NAME} exploration surface — Plotly <code>scatter3d</code> over{' '}
          <code>MultivariatePoint[]</code>. Layer 0 corpus drives live axes; an empty corpus shows a
          synthetic helix until you ingest sources.
        </p>
        <ChartErrorBoundary
          chartName="Multivariate3DTemplate"
          fallbackMessage="Plotly failed to load or render. Check the Console for stack details; restart with npm run dev:fresh after Vite config changes."
        >
          <Multivariate3DTemplate
            points={multivariate3d.points}
            axisTitles={multivariate3d.axisTitles}
            height={440}
            colorBy="value"
            traceName="corpus-demo"
          />
        </ChartErrorBoundary>
      </section>
    </div>
  )
}
