import React from 'react'

interface ActivePosition {
  id: string
  bot_type: 'conservative' | 'aggressive'
  type: 'BUY' | 'SELL'
  entry_price: number
  current_price: number
  quantity: number
  pnl: number
  pnl_pct: number
  stop_loss?: number
  take_profit?: number
  timestamp: string
}

interface ActivePositionsProps {
  positions: {
    conservative: Record<string, ActivePosition>
    aggressive: Record<string, ActivePosition>
  } | null
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
    const allPositions: (ActivePosition & { botType: 'conservative' | 'aggressive' })[] = []

    Object.entries(positions.conservative || {}).forEach(([, pos]) => {
      allPositions.push({ ...pos, botType: 'conservative' })
    })

    Object.entries(positions.aggressive || {}).forEach(([, pos]) => {
      allPositions.push({ ...pos, botType: 'aggressive' })
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
    return botType === 'conservative' ? '🐌' : '⚡'
  }

  const getBotName = (botType: string) => {
    return botType === 'conservative' ? 'Conservador' : 'Agresivo'
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
            <span className="summary-label">Conservadoras:</span>
            <span className="summary-value">
              {Object.keys(positions.conservative || {}).length}
            </span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Agresivas:</span>
            <span className="summary-value">{Object.keys(positions.aggressive || {}).length}</span>
          </div>
        </div>

        <div className="positions-list">
          {activePositions.map((position) => (
            <div key={position.id} className="position-card">
              <div className="position-header">
                <div className="bot-info">
                  <span className="bot-icon">{getBotIcon(position.botType)}</span>
                  <span className="bot-name">{getBotName(position.botType)}</span>
                </div>
                <div className="position-type" style={{ color: getPositionColor(position.type) }}>
                  {position.type}
                </div>
              </div>

              <div className="position-details">
                <div className="detail-row">
                  <span className="detail-label">Entrada:</span>
                  <span className="detail-value">${position.entry_price.toFixed(5)}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Actual:</span>
                  <span className="detail-value">${position.current_price.toFixed(5)}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Cantidad:</span>
                  <span className="detail-value">{position.quantity.toFixed(5)} DOGE</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">PnL:</span>
                  {formatPnL(position.pnl, position.pnl_pct)}
                </div>
                {position.stop_loss && (
                  <div className="detail-row">
                    <span className="detail-label">Stop Loss:</span>
                    <span className="detail-value">${position.stop_loss.toFixed(4)}</span>
                  </div>
                )}
                {position.take_profit && (
                  <div className="detail-row">
                    <span className="detail-label">Take Profit:</span>
                    <span className="detail-value">${position.take_profit.toFixed(4)}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default ActivePositions
