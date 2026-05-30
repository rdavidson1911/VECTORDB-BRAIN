import type { Layout } from 'plotly.js'

/**
 * Canonical point model for 3D multivariate templates.
 * Extend with new optional fields as additional encodings are added (e.g. symbol, opacity).
 */
export type MultivariatePoint = {
  x: number
  y: number
  z: number
  /** Fourth numeric dimension: color scale (defaults to `z` when unset and colorBy asks for value). */
  value?: number
  /** Fifth numeric dimension: marker size after normalization. */
  magnitude?: number
  /** Short label (hover + future selection APIs). */
  label?: string
  /** Stable id for brushing / callbacks. */
  id?: string
  /** Extra columns surfaced in hover via customdata (stringified). */
  meta?: Record<string, string | number | boolean | null | undefined>
}

export type Axis3DTitle = Partial<Record<'x' | 'y' | 'z', string>>

export type ColorByMode = 'value' | 'z' | 'magnitude' | 'none'

export type Multivariate3DTemplateProps = {
  points: MultivariatePoint[]
  axisTitles?: Axis3DTitle
  /** Plot height in CSS pixels. */
  height?: number
  className?: string
  colorBy?: ColorByMode
  /** Plotly colorscale name (e.g. Viridis, Plasma). */
  colorscale?: string
  /** Min/max marker diameter in plot units after scaling `magnitude` or `value`. */
  markerSizeRange?: [number, number]
  /** Merged after the built-in dark layout (escape hatch for new chart variants). */
  layoutPatch?: Partial<Layout>
  traceName?: string
  emptyMessage?: string
}
