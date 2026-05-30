import { useEffect, useMemo, useState, type ComponentType, type CSSProperties } from 'react'
import type { Config, Data, Layout } from 'plotly.js'
import { buildScatter3DTrace } from './buildScatter3DTrace'
import { buildScatter3DLayout } from './plotlyDarkLayout'
import type { Multivariate3DTemplateProps } from './types'

type PlotlyFigure = ComponentType<{
  data: Data[]
  layout: Partial<Layout>
  config?: Partial<Config>
  style?: CSSProperties
  useResizeHandler?: boolean
  className?: string
}>

/** Vite/Rollup CJS interop: chunk default may be `{ __esModule, default: Component }` not the component. */
function resolvePlotlyFigure(mod: typeof import('react-plotly.js')): PlotlyFigure | null {
  const exported = mod.default as unknown
  if (typeof exported === 'function') return exported as PlotlyFigure
  if (
    exported !== null &&
    typeof exported === 'object' &&
    'default' in exported &&
    typeof (exported as { default: unknown }).default === 'function'
  ) {
    return (exported as { default: PlotlyFigure }).default
  }
  return null
}

const defaultConfig: Partial<Config> = {
  displaylogo: false,
  responsive: true,
  scrollZoom: true,
}

/**
 * Generalized 3D scatter template: `MultivariatePoint` → Plotly `scatter3d`.
 * Plotly loads asynchronously so the main dashboard bundle stays smaller.
 *
 * Future variants: add sibling builders (e.g. `buildSurface3DTrace`) and either
 * swap traces here or compose dedicated templates that reuse `buildScatter3DLayout`.
 */
export function Multivariate3DTemplate({
  points,
  axisTitles,
  height = 420,
  className,
  colorBy = 'value',
  colorscale,
  markerSizeRange = [3.2, 9],
  layoutPatch,
  traceName,
  emptyMessage = 'No points to plot yet.',
}: Multivariate3DTemplateProps) {
  const [Plot, setPlot] = useState<PlotlyFigure | null>(null)
  const [plotLoadError, setPlotLoadError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void import('react-plotly.js')
      .then((mod) => {
        if (cancelled) return
        const Resolved = resolvePlotlyFigure(mod)
        if (Resolved) {
          setPlotLoadError(null)
          setPlot(() => Resolved)
        } else {
          setPlotLoadError(
            'Plotly chart module loaded but no React component was found (unexpected bundler export). Try npm run dev:fresh.',
          )
        }
      })
      .catch(() => {
        if (cancelled) return
        setPlotLoadError(
          'Failed to load Plotly. Check the console; restart with npm run dev:fresh after Vite or dependency changes.',
        )
      })
    return () => {
      cancelled = true
    }
  }, [])

  const data = useMemo(
    () =>
      buildScatter3DTrace(points, {
        colorBy,
        colorscale,
        markerSizeRange,
        name: traceName,
      }),
    [points, colorBy, colorscale, markerSizeRange, traceName],
  )

  const layout = useMemo(
    () => buildScatter3DLayout(axisTitles ?? {}, height, layoutPatch),
    [axisTitles, height, layoutPatch],
  )

  if (points.length === 0) {
    return (
      <div
        className={className}
        style={{ minHeight: height }}
        data-chart="multivariate-3d-empty"
      >
        <p className="small">{emptyMessage}</p>
      </div>
    )
  }

  if (plotLoadError) {
    return (
      <div
        className={className}
        style={{ minHeight: height }}
        role="alert"
        data-chart="multivariate-3d-error"
      >
        <p className="small">{plotLoadError}</p>
      </div>
    )
  }

  if (!Plot) {
    return (
      <div
        className={className}
        style={{ minHeight: height }}
        aria-busy="true"
        data-chart="multivariate-3d-loading"
      >
        <p className="small">Loading 3D view…</p>
      </div>
    )
  }

  return (
    <Plot
      data={data}
      layout={layout}
      config={defaultConfig}
      style={{ width: '100%', height }}
      useResizeHandler
      className={className}
    />
  )
}
