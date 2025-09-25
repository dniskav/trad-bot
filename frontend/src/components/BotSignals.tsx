import React, { useEffect, useState } from 'react'
import { useApiProcessInfo } from '../hooks'
import { useUniqueId } from '../hooks/useUniqueId'
import { InfoBox } from './InfoBox'

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
  const uniqueId = useUniqueId('bot-signals')

  // TODOS LOS HOOKS DEBEN IR AL INICIO - ANTES DE CUALQUIER RETURN CONDICIONAL
  const [botStatus, setBotStatus] = useState({
    conservative: false,
    aggressive: false
  })

  const [dynamicLimits] = useState({
    total_max_positions: 10,
    active_bots: 2,
    available_positions_per_bot: 5,
    current_positions: {
      conservative: 0,
      aggressive: 0
    }
  })

  // Estado del acordeón ahora manejado por InfoBox
  // const [accordionOpen, setAccordionOpen] = useState(() => {
  //   if (typeof window !== 'undefined') {
  //     const saved = localStorage.getItem('bot-signals-accordion')
  //     return saved ? JSON.parse(saved) : { conservative: false, aggressive: false }
  //   }
  //   return { conservative: false, aggressive: false }
  // })

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

  // Use process info hook
  const { data: processInfoData } = useApiProcessInfo()

  // Update process info when data changes
  useEffect(() => {
    if (processInfoData) {
      setBotProcessInfo(processInfoData)
    }
  }, [processInfoData])

  // Actualizar tiempo de ejecución cada segundo (sin forzar re-render)
  useEffect(() => {
    const interval = setInterval(() => {
      // Solo actualizar el tiempo de ejecución sin forzar re-render
      // El componente se actualizará automáticamente cuando cambien los datos
    }, 1000)

    return () => clearInterval(interval)
  }, [])

  // Return condicional después de todos los hooks
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

  const handleBotToggleDirect = async (botType: string) => {
    try {
      const action = botStatus[botType as keyof typeof botStatus] ? 'stop' : 'start'
      const response = await fetch(`/api/bot-control/${botType}/${action}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const result = await response.json()

      if (result.success) {
        setBotStatus((prev) => ({
          ...prev,
          [botType]: !prev[botType as keyof typeof prev]
        }))
        console.log(`✅ ${result.message}`)
      } else {
        console.error('❌ Error:', result.error)
        alert(`Error: ${result.error}`)
      }
    } catch (error) {
      console.error('❌ Error toggling bot:', error)
      alert(`Error de conexión: ${error}`)
    }
  }

  // Función toggleAccordion ahora manejada por InfoBox
  // const toggleAccordion = (botType: 'conservative' | 'aggressive') => {
  //   setAccordionOpen((prev: Record<string, boolean>) => {
  //     const newState = {
  //       ...prev,
  //       [botType]: !prev[botType]
  //     }
  //     // Save to localStorage
  //     if (typeof window !== 'undefined') {
  //       localStorage.setItem('bot-signals-accordion', JSON.stringify(newState))
  //     }
  //     return newState
  //   })
  // }

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

  const formatDateTime = (dateString: string | null) => {
    if (!dateString) return 'N/A'
    try {
      const date = new Date(dateString)
      return date.toLocaleString('es-ES', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        timeZone: 'America/Santiago'
      })
    } catch (error) {
      return 'N/A'
    }
  }

  const calculateUptime = (dateString: string | null) => {
    if (!dateString) return 'N/A'
    try {
      const startTime = new Date(dateString).getTime()
      const currentTime = Date.now()
      const uptimeMs = currentTime - startTime

      const hours = Math.floor(uptimeMs / (1000 * 60 * 60))
      const minutes = Math.floor((uptimeMs % (1000 * 60 * 60)) / (1000 * 60))
      const seconds = Math.floor((uptimeMs % (1000 * 60)) / 1000)

      if (hours > 0) {
        return `${hours}h ${minutes}m ${seconds}s`
      } else if (minutes > 0) {
        return `${minutes}m ${seconds}s`
      } else {
        return `${seconds}s`
      }
    } catch (error) {
      return 'N/A'
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

      <div className="bot-status">
        <div className="signals-container">
          {/* Bot Conservative Card */}
          <div className="bot-card conservative">
            <div className="bot-card-header">
              <div className="bot-header-left">
                <span className="signal-icon">🐌</span>
                <span className="signal-title">Conservador</span>
              </div>
              <div className="bot-header-right">
                <button
                  id={`${uniqueId}-conservative-toggle`}
                  className={`bot-toggle-button ${botStatus.conservative ? 'active' : 'inactive'}`}
                  onClick={() => handleBotToggleDirect('conservative')}
                  title={botStatus.conservative ? 'Desactivar bot' : 'Activar bot'}>
                  {botStatus.conservative ? 'OFF' : 'ON'}
                </button>
              </div>
            </div>

            <div className="bot-card-content">
              <div className="signal-value" style={{ color: getSignalColor(signals.conservative) }}>
                {getSignalIcon(signals.conservative)} {signals.conservative}
              </div>
              <div className="signal-description">SMA 8 vs 21, Threshold 0.0005</div>
              {getPositionInfo('conservative')}

              {/* Info Box - Usar componente reutilizable */}
              <InfoBox
                title="ℹ️ Info"
                isActive={botProcessInfo.conservative.active}
                storageKey="bot-signals-conservative-accordion"
                items={[
                  {
                    label: 'Proceso',
                    value: botProcessInfo.conservative.active
                      ? `activo (PID: ${botProcessInfo.conservative.pid})`
                      : 'inactivo'
                  },
                  {
                    label: 'Memoria',
                    value: `${botProcessInfo.conservative.memory_mb} MB`
                  },
                  {
                    label: 'CPU',
                    value: `${botProcessInfo.conservative.cpu_percent}%`
                  },
                  {
                    label: 'Inicio',
                    value: formatDateTime(botProcessInfo.conservative.create_time)
                  },
                  {
                    label: 'Tiempo ejecución',
                    value: calculateUptime(botProcessInfo.conservative.create_time)
                  }
                ]}
              />
            </div>
          </div>

          {/* Bot Aggressive Card */}
          <div className="bot-card aggressive">
            <div className="bot-card-header">
              <div className="bot-header-left">
                <span className="signal-icon">⚡</span>
                <span className="signal-title">Agresivo</span>
              </div>
              <div className="bot-header-right">
                <button
                  id={`${uniqueId}-aggressive-toggle`}
                  className={`bot-toggle-button ${botStatus.aggressive ? 'active' : 'inactive'}`}
                  onClick={() => handleBotToggleDirect('aggressive')}
                  title={botStatus.aggressive ? 'Desactivar bot' : 'Activar bot'}>
                  {botStatus.aggressive ? 'OFF' : 'ON'}
                </button>
              </div>
            </div>

            <div className="bot-card-content">
              <div className="signal-value" style={{ color: getSignalColor(signals.aggressive) }}>
                {getSignalIcon(signals.aggressive)} {signals.aggressive}
              </div>
              <div className="signal-description">SMA 5 vs 13, Threshold 0.0008</div>
              {getPositionInfo('aggressive')}

              {/* Info Box - Usar componente reutilizable */}
              <InfoBox
                title="ℹ️ Info"
                isActive={botProcessInfo.aggressive.active}
                storageKey="bot-signals-aggressive-accordion"
                items={[
                  {
                    label: 'Proceso',
                    value: botProcessInfo.aggressive.active
                      ? `activo (PID: ${botProcessInfo.aggressive.pid})`
                      : 'inactivo'
                  },
                  {
                    label: 'Memoria',
                    value: `${botProcessInfo.aggressive.memory_mb} MB`
                  },
                  {
                    label: 'CPU',
                    value: `${botProcessInfo.aggressive.cpu_percent}%`
                  },
                  {
                    label: 'Inicio',
                    value: formatDateTime(botProcessInfo.aggressive.create_time)
                  },
                  {
                    label: 'Tiempo ejecución',
                    value: calculateUptime(botProcessInfo.aggressive.create_time)
                  }
                ]}
              />
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
