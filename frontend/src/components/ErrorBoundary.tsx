import { Component, ErrorInfo, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('🚨 ErrorBoundary capturó un error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div
            style={{
              padding: '20px',
              border: '1px solid #ef5350',
              borderRadius: '8px',
              backgroundColor: '#2a1e1e',
              color: '#ef5350',
              margin: '10px'
            }}>
            <h3>🚨 Error en el componente</h3>
            <p>Algo salió mal al renderizar este componente.</p>
            <details style={{ marginTop: '10px' }}>
              <summary>Detalles del error</summary>
              <pre
                style={{
                  marginTop: '10px',
                  padding: '10px',
                  backgroundColor: '#1a1a1a',
                  borderRadius: '4px',
                  fontSize: '12px',
                  overflow: 'auto'
                }}>
                {this.state.error?.message}
              </pre>
            </details>
            <button
              onClick={() => this.setState({ hasError: false, error: undefined })}
              style={{
                marginTop: '10px',
                padding: '8px 16px',
                backgroundColor: '#ef5350',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}>
              Reintentar
            </button>
          </div>
        )
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
