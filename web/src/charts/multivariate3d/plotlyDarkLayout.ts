import type { Layout } from 'plotly.js'

const paper = 'rgba(15, 23, 42, 0)'
const plot = 'rgba(15, 23, 42, 0)'
const text = '#cbd5e1'
const grid = 'rgba(148, 163, 184, 0.28)'
const sceneBg = 'rgba(2, 6, 23, 0.65)'

/**
 * Base dark layout for 3D scenes; keep presentation tokens here so future Plotly chart
 * templates can reuse the same look without copying literals.
 */
export function buildScatter3DLayout(
  axisTitles: Partial<Record<'x' | 'y' | 'z', string>>,
  height: number,
  patch?: Partial<Layout>,
): Partial<Layout> {
  const axis = (title: string) => ({
    title: { text: title, font: { color: text, size: 12 } },
    backgroundcolor: plot,
    gridcolor: grid,
    showbackground: true,
    color: text,
    tickfont: { color: '#94a3b8', size: 11 },
  })

  return {
    autosize: true,
    paper_bgcolor: paper,
    plot_bgcolor: plot,
    font: { color: text, family: 'Inter, Segoe UI, Roboto, Arial, sans-serif', size: 12 },
    showlegend: false,
    margin: { l: 0, r: 0, t: 8, b: 0 },
    height,
    scene: {
      xaxis: axis(axisTitles.x ?? ''),
      yaxis: axis(axisTitles.y ?? ''),
      zaxis: axis(axisTitles.z ?? ''),
      bgcolor: sceneBg,
      camera: {
        eye: { x: 1.35, y: 1.35, z: 0.9 },
      },
    },
    ...patch,
  }
}
