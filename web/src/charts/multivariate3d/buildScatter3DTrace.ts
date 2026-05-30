import type { Data } from 'plotly.js'
import type { ColorByMode, MultivariatePoint } from './types'

function finiteNumbers(values: number[]): number[] {
  return values.filter((v) => Number.isFinite(v))
}

function scaleSizes(values: number[], range: [number, number]): number[] {
  const nums = finiteNumbers(values)
  if (nums.length === 0) return values.map(() => range[0])
  const min = Math.min(...nums)
  const max = Math.max(...nums)
  const [lo, hi] = range
  if (max === min) return values.map(() => (lo + hi) / 2)
  return values.map((v) => {
    if (!Number.isFinite(v)) return lo
    const t = (v - min) / (max - min)
    return lo + t * (hi - lo)
  })
}

function colorArray(
  points: MultivariatePoint[],
  colorBy: ColorByMode,
): { colors: number[] | string; showscale: boolean } {
  if (colorBy === 'none') {
    return { colors: '#38bdf8', showscale: false }
  }
  const key = colorBy === 'value' ? 'value' : colorBy === 'magnitude' ? 'magnitude' : 'z'
  const values = points.map((p) => {
    if (key === 'value') return p.value ?? p.z
    if (key === 'magnitude') return p.magnitude ?? p.value ?? p.z
    return p.z
  })
  if (!values.every((v) => Number.isFinite(v))) {
    return { colors: '#38bdf8', showscale: false }
  }
  return { colors: values, showscale: true }
}

export type Scatter3DTraceOptions = {
  colorBy: ColorByMode
  colorscale?: string
  markerSizeRange: [number, number]
  name?: string
}

/**
 * Pure builder: maps domain points → Plotly `scatter3d` trace.
 * Other 3D chart types (mesh3d, surface) can follow the same pattern in sibling builders.
 */
export function buildScatter3DTrace(points: MultivariatePoint[], options: Scatter3DTraceOptions): Data[] {
  const xs = points.map((p) => p.x)
  const ys = points.map((p) => p.y)
  const zs = points.map((p) => p.z)
  const text = points.map((p) => p.label ?? '')
  const sizeSource = points.map((p) => p.magnitude ?? p.value ?? p.z)
  const sizes = scaleSizes(sizeSource, options.markerSizeRange)
  const { colors, showscale } = colorArray(points, options.colorBy)

  const metaKeys = new Set<string>()
  for (const p of points) {
    if (p.meta) for (const k of Object.keys(p.meta)) metaKeys.add(k)
  }
  const metaKeyList = [...metaKeys].sort()
  const customdata =
    metaKeyList.length === 0
      ? undefined
      : points.map((p) => metaKeyList.map((k) => String(p.meta?.[k] ?? '')))

  const baseHover = '%{text}<br>x=%{x:.4~f}<br>y=%{y:.4~f}<br>z=%{z:.4~f}'
  const metaHover =
    metaKeyList.length === 0 ? '' : metaKeyList.map((k, i) => `<br>${k}=%{customdata[${i}]}`).join('')
  const hovertemplate = `${baseHover}${metaHover}<extra></extra>`

  const trace: Data = {
    type: 'scatter3d',
    mode: 'markers',
    name: options.name ?? 'series',
    x: xs,
    y: ys,
    z: zs,
    text,
    customdata,
    hovertemplate,
    marker: {
      size: sizes,
      color: colors,
      colorscale: options.colorscale ?? 'Viridis',
      opacity: 0.92,
      line: {
        color: 'rgba(15, 23, 42, 0.85)',
        width: 0.35,
      },
      showscale,
      colorbar:
        showscale ?
          {
            thickness: 12,
            len: 0.55,
            tickfont: { color: '#94a3b8', size: 10 },
            title: { font: { color: '#cbd5e1', size: 11 } },
          }
        : undefined,
    },
  }

  return [trace]
}
