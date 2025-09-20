import React, { useState } from 'react'
import './App.css'
import CandlestickChart from './components/CandlestickChart'
import TimeframeSelector from './components/TimeframeSelector'
import WebSocketStatus from './components/WebSocketStatus'
import { WebSocketProvider, useWebSocketContext } from './contexts/WebSocketContext'

interface HealthStatus {
  status: string
  timestamp: string
  message: string
}

interface AppContentProps {
  selectedTimeframe: string
  onTimeframeChange: (timeframe: string) => void
}

function AppContent({ selectedTimeframe, onTimeframeChange }: AppContentProps) {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { isConnected, lastMessage } = useWebSocketContext()

  // Separate price and candle data
  const [priceData, setPriceData] = useState<any>(null)
  const [candleData, setCandleData] = useState<any>(null)

  // Update data based on message type
  React.useEffect(() => {
    if (lastMessage) {
      if (lastMessage.type === 'price') {
        setPriceData(lastMessage)
      } else if (lastMessage.type === 'candles') {
        setCandleData(lastMessage)
      }
    }
  }, [lastMessage])

  const checkHealth = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch('http://localhost:8000/health')

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setHealth(data)
    } catch (err) {
      console.error('Error checking health:', err)
      setError(err instanceof Error ? err.message : 'Error desconocido')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="App">
      <WebSocketStatus />

      <header className="App-header">
        <h1>🚀 Trading Bot</h1>
        <p>Server Health Monitor</p>
      </header>

      <main className="App-main">
        <div className="health-container">
          <div className="status-card">
            <div className="status-icon">🔍</div>
            <h3>Estado del Servidor</h3>
            <p>Verifica el estado del servidor manualmente</p>
            <button onClick={checkHealth} className="check-button" disabled={loading}>
              {loading ? '🔄 Verificando...' : '🔍 Verificar Health'}
            </button>
          </div>

          {error && (
            <div className="status-card error">
              <div className="status-icon">❌</div>
              <h3>Error de conexión</h3>
              <p>{error}</p>
            </div>
          )}

          {health && (
            <div className="status-card success">
              <div className="status-icon">✅</div>
              <h3>Servidor funcionando</h3>
              <div className="health-details">
                <p>
                  <strong>Status:</strong> <span className="status-value">{health.status}</span>
                </p>
                <p>
                  <strong>Mensaje:</strong> {health.message}
                </p>
                <p>
                  <strong>Última verificación:</strong>{' '}
                  {new Date(health.timestamp).toLocaleString()}
                </p>
              </div>
            </div>
          )}

          {/* Price Data Box */}
          <div className="websocket-boxes-container">
            <div className="websocket-data-box">
              <h3>💰 Datos de Precio</h3>
              <div className="websocket-status">
                <span>Estado: </span>
                <span className={isConnected ? 'connected' : 'disconnected'}>
                  {isConnected ? '🟢 Conectado' : '🔴 Desconectado'}
                </span>
              </div>
              <div className="json-display">
                <pre>
                  {priceData ? JSON.stringify(priceData, null, 2) : 'Esperando datos de precio...'}
                </pre>
              </div>
            </div>

            {/* Candlestick Data Box */}
            <div className="websocket-data-box">
              <h3>📊 Datos de Velas</h3>
              <div className="websocket-status">
                <span>Estado: </span>
                <span className={isConnected ? 'connected' : 'disconnected'}>
                  {isConnected ? '🟢 Conectado' : '🔴 Desconectado'}
                </span>
              </div>
              <div className="json-display">
                <pre>
                  {candleData ? JSON.stringify(candleData, null, 2) : 'Esperando datos de velas...'}
                </pre>
              </div>
            </div>
          </div>

          {/* Chart Section */}
          <div className="chart-section">
            <div className="chart-container">
              <h3>📈 Gráfico de Velas</h3>
              <TimeframeSelector
                selectedTimeframe={selectedTimeframe}
                onTimeframeChange={onTimeframeChange}
              />
              <CandlestickChart timeframe={selectedTimeframe} />
            </div>
          </div>
        </div>
      </main>

      <footer className="App-footer">
        <p>&copy; 2024 Trading Bot - Minimal Version</p>
      </footer>
    </div>
  )
}

function AppWithTimeframe() {
  const [selectedTimeframe, setSelectedTimeframe] = useState('1m')

  return (
    <WebSocketProvider timeframe={selectedTimeframe}>
      <AppContent selectedTimeframe={selectedTimeframe} onTimeframeChange={setSelectedTimeframe} />
    </WebSocketProvider>
  )
}

function App() {
  return <AppWithTimeframe />
}

export default App
