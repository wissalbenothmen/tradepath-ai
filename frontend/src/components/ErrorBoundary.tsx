import { Component, type ReactNode } from 'react'
import { AlertTriangle, RotateCcw } from 'lucide-react'

interface Props {
  children: ReactNode
}
interface State {
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    // eslint-disable-next-line no-console
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  reset = () => this.setState({ error: null })

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-6">
        <div className="max-w-md w-full bg-white shadow-soft-3 border border-slate-200 rounded-2xl p-6 text-center">
          <div className="mx-auto w-12 h-12 rounded-full bg-red-50 flex items-center justify-center mb-3">
            <AlertTriangle className="text-red-500" size={22} />
          </div>
          <h2 className="text-lg font-semibold text-slate-900">Something went wrong</h2>
          <p className="text-sm text-slate-500 mt-1">
            We logged this to the console. Reload the page or try again.
          </p>
          <pre className="text-2xs text-left bg-slate-50 border border-slate-200 rounded-lg p-3 mt-4 max-h-32 overflow-auto text-slate-600">
            {this.state.error.message || String(this.state.error)}
          </pre>
          <button
            onClick={() => { this.reset(); window.location.reload() }}
            className="btn-primary mt-4 w-full justify-center"
          >
            <RotateCcw size={14} /> Reload
          </button>
        </div>
      </div>
    )
  }
}
