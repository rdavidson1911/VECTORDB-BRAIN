import { Component, type ErrorInfo, type ReactNode } from 'react'

type ChartErrorBoundaryProps = {
  children: ReactNode
  /** Shown in UI and console for DevTools triage. */
  chartName: string
  fallbackMessage?: string
}

type ChartErrorBoundaryState = {
  error: Error | null
}

/**
 * Isolates chart failures (e.g. Plotly) so the rest of the dashboard still renders
 * and React DevTools can show a clear error boundary in the tree.
 */
export class ChartErrorBoundary extends Component<ChartErrorBoundaryProps, ChartErrorBoundaryState> {
  state: ChartErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): ChartErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error(`[ChartErrorBoundary:${this.props.chartName}]`, error, info.componentStack)
  }

  render(): ReactNode {
    const { error } = this.state
    if (error) {
      return (
        <div className="panel error" data-chart-error={this.props.chartName} role="alert">
          <p>
            <strong>{this.props.chartName}</strong> failed to render.
          </p>
          <p className="small mono">{error.message}</p>
          {this.props.fallbackMessage ? <p className="small">{this.props.fallbackMessage}</p> : null}
          <button type="button" onClick={() => this.setState({ error: null })}>
            Retry
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
