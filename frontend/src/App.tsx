import React, { useState } from 'react'
import './App.css'
import Accordion from './components/Accordion'
import AccountBalance from './components/AccountBalance'
import ActivePositions from './components/ActivePositions'
import BotSignals from './components/BotSignals'
import CandlestickChart from './components/CandlestickChart'
import PositionHistory from './components/PositionHistory'
import TimeframeSelector from './components/TimeframeSelector'
import Toast from './components/Toast'
import WebSocketStatus from './components/WebSocketStatus'
import { WebSocketProvider, useWebSocketContext } from './contexts/WebSocketContext'

interface AppContentProps {
  selectedTimeframe: string
  onTimeframeChange: (timeframe: string) => void
}

function AppContent({ selectedTimeframe, onTimeframeChange }: AppContentProps) {
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState<{
    message: string
    type: 'success' | 'error' | 'info'
  } | null>(null)

  const { isConnected, lastMessage } = useWebSocketContext()

  // Separate price and candle data
  const [priceData, setPriceData] = useState<any>(null)
  const [candleData, setCandleData] = useState<any>(null)
  const [botSignals, setBotSignals] = useState<any>(null)
  const [positionHistory, setPositionHistory] = useState<any[]>([])
  const [botStatistics, setBotStatistics] = useState<any>(null)
  const [accountBalance, setAccountBalance] = useState<any>(null)
  const [activePositions, setActivePositions] = useState<any>(null)

  // Update data based on message type
  React.useEffect(() => {
    if (lastMessage) {
      if (lastMessage.type === 'price') {
        setPriceData(lastMessage)
      } else if (lastMessage.type === 'candles') {
        setCandleData(lastMessage)

        // Extract bot signals if available
        if (lastMessage.data && lastMessage.data.bot_signals) {
          setBotSignals({
            ...lastMessage.data.bot_signals,
            symbol: lastMessage.data.symbol // Agregamos el símbolo
          })

          // Extract position history and statistics
          if (lastMessage.data.bot_signals && lastMessage.data.bot_signals.positions) {
            const positions = lastMessage.data.bot_signals.positions
            console.log('🔍 Debug - positions data:', positions)

            if (positions.history) {
              console.log('📋 Setting position history:', positions.history.length, 'items')
              setPositionHistory(positions.history)
            }
            if (positions.statistics) {
              console.log('📊 Setting bot statistics:', positions.statistics)
              setBotStatistics(positions.statistics)
            }
            if (positions.account_balance) {
              console.log('💰 Setting account balance:', positions.account_balance)
              setAccountBalance(positions.account_balance)
            }
            if (positions.active_positions) {
              console.log('📊 Setting active positions:', positions.active_positions)
              setActivePositions(positions.active_positions)
            }
          } else {
            console.log('❌ No positions data found in:', lastMessage.data)
          }
        }
      }
    }
  }, [lastMessage])

  const checkHealth = async () => {
    try {
      setLoading(true)

      const response = await fetch('http://localhost:8000/health')

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()

      // Show success toast
      setToast({
        message: `Servidor funcionando - ${data.status}`,
        type: 'success'
      })
    } catch (err) {
      console.error('Error checking health:', err)
      const errorMessage = err instanceof Error ? err.message : 'Error desconocido'

      // Show error toast
      setToast({
        message: `Error de conexión: ${errorMessage}`,
        type: 'error'
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="App">
      {/* Toast */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          duration={3000}
          onClose={() => setToast(null)}
        />
      )}

      <header className="App-header">
        <div className="header-content">
          {/* Status Boxes */}
          <div className="status-boxes">
            <div className="status-box green-box">
              <WebSocketStatus />
            </div>
          </div>

          {/* Title Section */}
          <div className="header-title">
            <h1>🚀 Trading Bot</h1>
            <p>Server Health Monitor</p>
          </div>

          {/* Status Boxes */}
          <div className="status-boxes">
            <div className="status-box red-box">
              <button onClick={checkHealth} className="health-button-compact" disabled={loading}>
                Status
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="App-main">
        <div className="health-container">
          {/* Account Balance */}
          {accountBalance && (
            <AccountBalance balance={accountBalance} currentPrice={priceData?.data?.price} />
          )}

          {/* Bot Signals Accordion */}
          <Accordion
            title="Señales de Trading"
            icon="🤖"
            defaultExpanded={false}
            className="bot-signals-accordion"
            storageKey="bot-signals">
            <BotSignals signals={botSignals} />
          </Accordion>

          {/* Active Positions */}
          <ActivePositions positions={activePositions} currentPrice={priceData?.data?.price} />

          {/* Price Data Accordion */}
          <Accordion
            title="Datos de Precio"
            icon="💰"
            defaultExpanded={false}
            className="websocket-accordion"
            storageKey="price-data">
            <div className="websocket-data-box">
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
          </Accordion>

          {/* Candlestick Data Accordion */}
          <Accordion
            title="Datos de Velas"
            icon="📊"
            defaultExpanded={false}
            className="websocket-accordion"
            storageKey="candle-data">
            <div className="websocket-data-box">
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
          </Accordion>

          {/* Position History */}
          {positionHistory.length > 0 && botStatistics && (
            <PositionHistory history={positionHistory} statistics={botStatistics} />
          )}

          {/* Chart Section */}
          <div className="chart-section">
            <div className="chart-container">
              <h3>📈 Gráfico de Velas</h3>
              <Accordion
                title="Seleccionar Timeframe"
                icon="⏱️"
                defaultExpanded={false}
                className="timeframe-accordion"
                storageKey="timeframe-selector">
                <TimeframeSelector
                  selectedTimeframe={selectedTimeframe}
                  onTimeframeChange={onTimeframeChange}
                />
              </Accordion>
              <CandlestickChart
                timeframe={selectedTimeframe}
                symbol={candleData?.data?.symbol || 'DOGEUSDT'}
              />
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
