import React from 'react'

interface ActivePosition {
  id: string
  bot_type: string
  type: 'BUY' | 'SELL'
  entry_price: number
  current_price: number
  quantity: number
  pnl: number
  pnl_pct: number
  stop_loss?: number
  take_profit?: number
  timestamp: string
  is_synthetic?: boolean
  is_plugin_bot?: boolean
  bot_on?: boolean
}

interface ActivePositionsProps {
  positions: Record<string, Record<string, ActivePosition>> | null
  currentPrice?: number
}

const ActivePositions: React.FC<ActivePositionsProps> = ({ positions }) => {
  if (!positions) {
    return (
      <div className="active-positions">
        <h3>📊 Posiciones Concurrentes Activas</h3>
        <div className="positions-status">
          <p>No hay posiciones activas</p>
        </div>
      </div>
    )
  }

  const getAllPositions = () => {
    const allPositions: (ActivePosition & { botType: string })[] = []

    Object.entries(positions).forEach(([botType, botPositions]) => {
      Object.entries(botPositions).forEach(([, pos]) => {
        allPositions.push({ ...pos, botType })
      })
    })

    return allPositions
  }

  const activePositions = getAllPositions()

  if (activePositions.length === 0) {
    return (
      <div className="active-positions">
        <h3>📊 Posiciones Concurrentes Activas</h3>
        <div className="positions-status">
          <p>No hay posiciones activas</p>
        </div>
      </div>
    )
  }

  const getBotIcon = (botType: string) => {
    switch (botType) {
      case 'conservative':
        return '🐌'
      case 'aggressive':
        return '⚡'
      case 'simplebot':
        return '🤖'
      case 'rsibot':
        return '📊'
      case 'macdbot':
        return '📈'
      default:
        return '🔌'
    }
  }

  const getBotName = (botType: string) => {
    switch (botType) {
      case 'conservative':
        return 'Conservador'
      case 'aggressive':
        return 'Agresivo'
      case 'simplebot':
        return 'Simple Bot'
      case 'rsibot':
        return 'RSI Bot'
      case 'macdbot':
        return 'MACD Bot'
      default:
        return botType
    }
  }

  const getPositionColor = (type: string) => {
    return type === 'BUY' ? '#26a69a' : '#ef5350'
  }

  const formatPnL = (pnl: number, pnlPct: number) => {
    const isPositive = pnl >= 0
    const color = isPositive ? '#26a69a' : '#ef5350'
    const sign = isPositive ? '+' : ''

    return (
      <span className="pnl-value" style={{ color }}>
        {sign}${pnl.toFixed(4)} ({sign}
        {pnlPct.toFixed(2)}%)
      </span>
    )
  }

  // Vista tabla compacta: Bot | Entrada | Actual | PnL Neto | Estado
  return (
    <div className="active-positions">
      <h3>📊 Posiciones Concurrentes Activas</h3>
      <div className="positions-container">
        <div className="positions-summary">
          <div className="summary-item">
            <span className="summary-label">Total Activas:</span>
            <span className="summary-value">{activePositions.length}</span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Reales:</span>
            <span className="summary-value">
              {activePositions.filter((p) => !p.is_synthetic).length}
            </span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Sintéticas:</span>
            <span className="summary-value">
              {activePositions.filter((p) => p.is_synthetic).length}
            </span>
          </div>
        </div>

        <div className="positions-table" style={{ width: '100%', overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left' }}>Bot</th>
                <th style={{ textAlign: 'left' }}>Entrada</th>
                <th style={{ textAlign: 'left' }}>Actual</th>
                <th style={{ textAlign: 'left' }}>PnL Neto</th>
                <th style={{ textAlign: 'left' }}>Estado</th>
              </tr>
            </thead>
            <tbody>
              {activePositions.map((p) => (
                <tr key={p.id} style={{ borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                  <td>
                    <span
                      className="bot-icon"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: 20,
                        height: 20,
                        borderRadius: 4,
                        background: p.bot_on ? '#1b5e20' : '#b71c1c',
                        color: '#fff',
                        fontSize: 12,
                        marginRight: 6
                      }}
                      title={p.bot_on ? 'Encendido' : 'Apagado'}>
                      {getBotIcon(p.botType)}
                    </span>{' '}
                    {getBotName(p.botType)}{' '}
                    {p.is_synthetic && <span title="Posición Sintética">🧪</span>}
                    {p.is_plugin_bot && <span title="Bot Plug-and-Play">🔌</span>}
                  </td>
                  <td>${p.entry_price.toFixed(5)}</td>
                  <td>${p.current_price.toFixed(5)}</td>
                  <td>{formatPnL(p.pnl, p.pnl_pct)}</td>
                  <td style={{ color: getPositionColor(p.type) }}>{p.type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default ActivePositions
