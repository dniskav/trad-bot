import React, { useEffect, useState } from 'react'
import BotControl from './BotControl'

interface BotSignalsProps {
  signals: {
    conservative: string
    aggressive: string
    current_price: number
    symbol?: string // Agregamos el símbolo
    positions?: {
      conservative: any
      aggressive: any
      last_signals: any
    }
  } | null
}

const BotSignals: React.FC<BotSignalsProps> = ({ signals }) => {
  const [botStatus, setBotStatus] = useState({
    conservative: false,
    aggressive: false
  })

  const [dynamicLimits, setDynamicLimits] = useState({
    total_max_positions: 10,
    active_bots: 2,
    available_positions_per_bot: 5,
    current_positions: {
      conservative: 0,
      aggressive: 0
    }
  })

  const [accordionOpen, setAccordionOpen] = useState({
    conservative: false,
    aggressive: false
  })

  const [botProcessInfo, setBotProcessInfo] = useState({
    conservative: {
      active: false,
      pid: null,
      memory_mb: 0,
      cpu_percent: 0,
      create_time: null
    },
    aggressive: {
      active: false,
      pid: null,
      memory_mb: 0,
      cpu_percent: 0,
      create_time: null
    }
  })

  // Fetch bot status and dynamic limits on component mount
  useEffect(() => {
    const fetchBotStatus = async () => {
      try {
        const response = await fetch('http://localhost:8000/bot/status')
        const result = await response.json()
        if (result.status === 'success') {
          // Use real process status from backend
          setBotStatus(result.data.bot_status)
          if (result.data.dynamic_limits) {
            setDynamicLimits(result.data.dynamic_limits)
          }
        }
      } catch (error) {
        console.error('Error fetching bot status:', error)
      }
    }

    const fetchBotProcessInfo = async () => {
      try {
        const response = await fetch('http://localhost:8000/bot/process-info')
        const result = await response.json()
        if (result.status === 'success') {
          setBotProcessInfo(result.data)
        }
      } catch (error) {
        console.error('Error fetching bot process info:', error)
      }
    }

    // Fetch initial status
    fetchBotStatus()
    fetchBotProcessInfo()

    // Set up automatic polling every 3 seconds
    const interval = setInterval(() => {
      fetchBotStatus()
      fetchBotProcessInfo()
    }, 3000)

    // Cleanup interval on component unmount
    return () => clearInterval(interval)
  }, [])

  const handleBotToggle = async (botType: string, newStatus: boolean) => {
    setBotStatus((prev) => ({
      ...prev,
      [botType]: newStatus
    }))

    // Refresh dynamic limits after bot status change
    try {
      const response = await fetch('http://localhost:8000/bot/status')
      const result = await response.json()
      if (result.status === 'success' && result.data.dynamic_limits) {
        setDynamicLimits(result.data.dynamic_limits)
      }
    } catch (error) {
      console.error('Error refreshing dynamic limits:', error)
    }
  }

  const toggleAccordion = (botType: 'conservative' | 'aggressive') => {
    setAccordionOpen((prev) => ({
      ...prev,
      [botType]: !prev[botType]
    }))
  }
  if (!signals) {
    return (
      <div className="bot-signals">
        <h3>🤖 Trading Bot Signals</h3>
        <div className="bot-status">
          <p>Esperando datos del bot...</p>
        </div>
      </div>
    )
  }

  const getSignalColor = (signal: string) => {
    switch (signal) {
      case 'BUY':
        return '#26a69a' // Verde
      case 'SELL':
        return '#ef5350' // Rojo
      case 'HOLD':
        return '#ffa726' // Naranja
      default:
        return '#666'
    }
  }

  const getSignalIcon = (signal: string) => {
    switch (signal) {
      case 'BUY':
        return '📈'
      case 'SELL':
        return '📉'
      case 'HOLD':
        return '⏸️'
      default:
        return '❓'
    }
  }

  const formatPnL = (pnl: number, pnlPct: number, isNet: boolean = false) => {
    const isPositive = pnl >= 0
    const color = isPositive ? '#26a69a' : '#ef5350'
    const sign = isPositive ? '+' : ''
    const label = isNet ? 'Neto' : 'Bruto'

    return (
      <div className="pnl-item">
        <span className="pnl-label">{label}:</span>
        <span className="pnl-value" style={{ color }}>
          {sign}${pnl.toFixed(4)} ({sign}
          {pnlPct.toFixed(2)}%)
        </span>
      </div>
    )
  }

  const getPositionInfo = (botType: 'conservative' | 'aggressive') => {
    const position = signals?.positions?.[botType]
    if (!position) return null

    const positionClass = position.type === 'BUY' ? 'buy' : 'sell'

    // Detectar proximidad al stop loss o take profit
    let proximityClass = ''
    if (position.stop_loss && position.take_profit) {
      const currentPrice = position.current_price
      const stopLoss = position.stop_loss
      const takeProfit = position.take_profit

      // Calcular distancia porcentual
      const stopLossDistance = Math.abs(currentPrice - stopLoss) / stopLoss
      const takeProfitDistance = Math.abs(currentPrice - takeProfit) / takeProfit

      // Si está cerca del stop loss (dentro del 0.2%)
      if (stopLossDistance < 0.002) {
        proximityClass = 'near-stop-loss'
      }
      // Si está cerca del take profit (dentro del 0.2%)
      else if (takeProfitDistance < 0.002) {
        proximityClass = 'near-take-profit'
      }
    }

    return (
      <div className={`position-info ${positionClass} ${proximityClass}`}>
        <div className="position-details">
          <span className="position-type">{position.type}</span>
          <span className="entry-price">Entrada: ${position.entry_price?.toFixed(4)}</span>
          <span className="current-price">Actual: ${position.current_price?.toFixed(4)}</span>
          {position.stop_loss && (
            <span className="stop-loss">Stop Loss: ${position.stop_loss?.toFixed(4)}</span>
          )}
          {position.take_profit && (
            <span className="take-profit">Take Profit: ${position.take_profit?.toFixed(4)}</span>
          )}
        </div>
        <div className="pnl-display">
          {formatPnL(position.pnl || 0, position.pnl_pct || 0, false)}
          {formatPnL(position.pnl_net || 0, position.pnl_net_pct || 0, true)}
          {position.total_fees && (
            <div className="fees-info">
              <span className="fees-label">Comisiones:</span>
              <span className="fees-value">${position.total_fees.toFixed(4)}</span>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="bot-signals">
      <h3>🤖 Trading Bot Signals</h3>

      {/* Bot Controls */}
      <div className="bot-controls">
        <BotControl
          botType="conservative"
          isActive={botStatus.conservative}
          onToggle={handleBotToggle}
        />
        <BotControl
          botType="aggressive"
          isActive={botStatus.aggressive}
          onToggle={handleBotToggle}
        />
      </div>

      <div className="bot-status">
        <div className="price-display">
          <span className="price-label">Precio Actual:</span>
          <span className="price-value">${signals.current_price.toFixed(5)}</span>
        </div>

        <div className="signals-container">
          <div className="signal-box conservative">
            <div className="signal-header">
              <span className="signal-icon">🐌</span>
              <span className="signal-title">Conservador</span>
            </div>
            <div className="signal-value" style={{ color: getSignalColor(signals.conservative) }}>
              {getSignalIcon(signals.conservative)} {signals.conservative}
            </div>
            <div className="signal-description">SMA 8 vs 21, Threshold 0.0005</div>
            {getPositionInfo('conservative')}

            {/* Info Box - Siempre mostrar, cambiar color según estado */}
            <div
              className={`bot-info-box ${
                botProcessInfo.conservative.active ? 'active' : 'inactive'
              }`}>
              <div className="info-header" onClick={() => toggleAccordion('conservative')}>
                ℹ️ Info {accordionOpen.conservative ? '▼' : '▶'}
              </div>
              {accordionOpen.conservative && (
                <div className="info-content">
                  <div className="info-item">
                    <span className="info-label">Proceso:</span>
                    <span
                      className={`info-value ${
                        botProcessInfo.conservative.active ? 'active' : 'inactive'
                      }`}>
                      {botProcessInfo.conservative.active
                        ? `activo (PID: ${botProcessInfo.conservative.pid})`
                        : 'inactivo'}
                    </span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">Memoria:</span>
                    <span
                      className={`info-value ${
                        botProcessInfo.conservative.active ? 'active' : 'inactive'
                      }`}>
                      {botProcessInfo.conservative.memory_mb} MB
                    </span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">CPU:</span>
                    <span
                      className={`info-value ${
                        botProcessInfo.conservative.active ? 'active' : 'inactive'
                      }`}>
                      {botProcessInfo.conservative.cpu_percent}%
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="signal-box aggressive">
            <div className="signal-header">
              <span className="signal-icon">⚡</span>
              <span className="signal-title">Agresivo</span>
            </div>
            <div className="signal-value" style={{ color: getSignalColor(signals.aggressive) }}>
              {getSignalIcon(signals.aggressive)} {signals.aggressive}
            </div>
            <div className="signal-description">SMA 5 vs 13, Threshold 0.0008</div>
            {getPositionInfo('aggressive')}

            {/* Info Box - Siempre mostrar, cambiar color según estado */}
            <div
              className={`bot-info-box ${
                botProcessInfo.aggressive.active ? 'active' : 'inactive'
              }`}>
              <div className="info-header" onClick={() => toggleAccordion('aggressive')}>
                ℹ️ Info {accordionOpen.aggressive ? '▼' : '▶'}
              </div>
              {accordionOpen.aggressive && (
                <div className="info-content">
                  <div className="info-item">
                    <span className="info-label">Proceso:</span>
                    <span
                      className={`info-value ${
                        botProcessInfo.aggressive.active ? 'active' : 'inactive'
                      }`}>
                      {botProcessInfo.aggressive.active
                        ? `activo (PID: ${botProcessInfo.aggressive.pid})`
                        : 'inactivo'}
                    </span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">Memoria:</span>
                    <span
                      className={`info-value ${
                        botProcessInfo.aggressive.active ? 'active' : 'inactive'
                      }`}>
                      {botProcessInfo.aggressive.memory_mb} MB
                    </span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">CPU:</span>
                    <span
                      className={`info-value ${
                        botProcessInfo.aggressive.active ? 'active' : 'inactive'
                      }`}>
                      {botProcessInfo.aggressive.cpu_percent}%
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="dynamic-limits-info">
          <h4>📊 Límites Dinámicos de Posiciones</h4>
          <div className="limits-grid">
            <div className="limit-item">
              <span className="limit-label">Total Máximo:</span>
              <span className="limit-value">{dynamicLimits.total_max_positions}</span>
            </div>
            <div className="limit-item">
              <span className="limit-label">Bots Activos:</span>
              <span className="limit-value">{dynamicLimits.active_bots}</span>
            </div>
            <div className="limit-item">
              <span className="limit-label">Por Bot Activo:</span>
              <span className="limit-value">{dynamicLimits.available_positions_per_bot}</span>
            </div>
            <div className="limit-item">
              <span className="limit-label">Conservador:</span>
              <span className="limit-value">{dynamicLimits.current_positions.conservative}</span>
            </div>
            <div className="limit-item">
              <span className="limit-label">Agresivo:</span>
              <span className="limit-value">{dynamicLimits.current_positions.aggressive}</span>
            </div>
          </div>
        </div>

        <div className="bot-info">
          <div className="info-item">
            <span className="info-label">Estrategia:</span>
            <span className="info-value">SMA Cross</span>
          </div>
          <div className="info-item">
            <span className="info-label">Símbolo:</span>
            <span className="info-value">{signals.symbol || 'ADAUSDT'}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Intervalo:</span>
            <span className="info-value">1m</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default BotSignals
