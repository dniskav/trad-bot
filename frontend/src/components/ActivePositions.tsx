import React, { useState } from 'react'

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
  const [confirming, setConfirming] = useState<null | {
    positionId: string
    botType: string
    entryPrice: number
    currentPrice: number
    quantity: number
    side: 'BUY' | 'SELL'
  }>(null)
  const [submitting, setSubmitting] = useState(false)
  if (!positions) {
    return (
      <div className="active-positions">
        <div className="positions-status">
          <p>No hay posiciones activas</p>
        </div>
      </div>
    )
  }

  const getAllPositions = () => {
    const allPositions: (ActivePosition & { botType: string })[] = []

    Object.entries(positions).forEach(([botType, botPositions]) => {
      Object.entries(botPositions).forEach(([key, anyPos]) => {
        const pos: any = anyPos || {}

        // Incluir también posiciones cerradas para debugging (no filtrar)

        const id = String(pos.id || pos.position_id || key)
        const type = String(pos.type || pos.signal_type || 'BUY').toUpperCase() as 'BUY' | 'SELL'
        const entry_price = Number(pos.entry_price || pos.entry || 0)
        const current_price = Number(pos.current_price || pos.price || entry_price)
        const quantity = Number(pos.quantity || pos.qty || 0)

        // Estimar PnL si no viene del backend
        const feeRate = 0.0015
        const gross =
          type === 'BUY'
            ? (current_price - entry_price) * quantity
            : (entry_price - current_price) * quantity
        const fees = current_price * quantity * feeRate
        const pnl = Number(pos.pnl ?? gross - fees)
        const base = entry_price * quantity || 1
        const pnl_pct = Number(pos.pnl_pct ?? ((gross - fees) / base) * 100)

        allPositions.push({
          id,
          bot_type: String(pos.bot_type || botType),
          type,
          entry_price,
          current_price,
          quantity,
          pnl,
          pnl_pct,
          stop_loss: pos.stop_loss,
          take_profit: pos.take_profit,
          timestamp: String(pos.entry_time || pos.timestamp || ''),
          is_synthetic: Boolean(pos.is_synthetic),
          is_plugin_bot: Boolean(pos.is_plugin_bot),
          bot_on: Boolean(pos.bot_on)
        } as ActivePosition & { botType: string })
      })
    })

    return allPositions
  }

  const activePositions = getAllPositions()

  const feeRate = 0.0015 // 0.15% total (entrada+salida) por defecto; el backend usa 0.0015 total

  const estimateNetPnl = (side: 'BUY' | 'SELL', entry: number, curr: number, qty: number) => {
    const gross = side === 'BUY' ? (curr - entry) * qty : (entry - curr) * qty
    const fees = curr * qty * feeRate // consider exit fee (entrada ya ocurió); conservador: total si se prefiere
    return gross - fees
  }

  const API_BASE =
    typeof window !== 'undefined' && window.location.hostname
      ? `${window.location.protocol}//${window.location.hostname}:8000`
      : 'http://localhost:8000'

  const requestClose = async (botType: string, positionId: string) => {
    setSubmitting(true)
    try {
      const res = await fetch(`${API_BASE}/api/positions/close`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bot_type: botType, position_id: positionId })
      })
      const json = await res.json()
      if (json.status !== 'success') {
        alert(`Error: ${json.message || 'No se pudo cerrar la posición'}`)
      }
    } catch (e) {
      alert('Error de red cerrando la posición')
    } finally {
      setSubmitting(false)
      setConfirming(null)
    }
  }

  if (activePositions.length === 0) {
    return (
      <div className="active-positions">
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

  const getPositionColor = (type: string, status?: string) => {
    if ((status || '').toUpperCase() === 'CLOSED') return '#bdbdbd'
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
      <div className="positions-container">
        {(() => {
          const totals = activePositions.reduce(
            (acc, p) => {
              const base = (p.entry_price || 0) * (p.quantity || 0)
              acc.base += base
              if (p.pnl >= 0) acc.gains += p.pnl
              else acc.losses += -p.pnl
              return acc
            },
            { gains: 0, losses: 0, base: 0 }
          )
          const net = totals.gains - totals.losses
          const pct = totals.base > 0 ? (net / totals.base) * 100 : 0
          const gainsPct = totals.base > 0 ? (totals.gains / totals.base) * 100 : 0
          const lossesPct = totals.base > 0 ? (totals.losses / totals.base) * 100 : 0
          const totalCount = activePositions.length
          const gainCount = activePositions.filter((p) => p.pnl >= 0).length
          const lossCount = totalCount - gainCount

          return (
            <div className="positions-summary">
              <div className="summary-item">
                <span className="summary-label">Ganancias ({gainCount}):</span>
                <span className="summary-value" style={{ color: '#26a69a', fontWeight: 700 }}>
                  +${totals.gains.toFixed(4)} ({gainsPct.toFixed(2)}%)
                </span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Pérdidas ({lossCount}):</span>
                <span className="summary-value" style={{ color: '#ef5350', fontWeight: 700 }}>
                  -${totals.losses.toFixed(4)} (-{lossesPct.toFixed(2)}%)
                </span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Neto ({totalCount}):</span>
                <span
                  className="summary-value"
                  style={{ color: net >= 0 ? '#26a69a' : '#ef5350', fontWeight: 800 }}>
                  {net >= 0 ? '+' : ''}${net.toFixed(4)} ({pct >= 0 ? '+' : ''}
                  {pct.toFixed(2)}%)
                </span>
              </div>
            </div>
          )
        })()}

        <div
          className="positions-table"
          style={{ width: '100%', overflowX: 'auto', maxHeight: 420, overflowY: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left' }}>Bot</th>
                <th style={{ textAlign: 'left' }}>Status</th>
                <th style={{ textAlign: 'left' }}>Entrada</th>
                <th style={{ textAlign: 'left' }}>Actual</th>
                <th style={{ textAlign: 'left' }}>PnL Neto</th>
                <th style={{ textAlign: 'left' }}>Estado</th>
              </tr>
            </thead>
            <tbody>
              {activePositions.map((p) => (
                <tr
                  key={`${p.botType || p.bot_type}:${p.id}`}
                  style={{ borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                  <td>{getBotName((p as any).botType || p.bot_type)}</td>
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
                        fontSize: 12
                      }}
                      title={p.bot_on ? 'Encendido' : 'Apagado'}>
                      {getBotIcon(p.botType)}
                    </span>
                  </td>
                  <td>${p.entry_price.toFixed(5)}</td>
                  <td>${p.current_price.toFixed(5)}</td>
                  <td>{formatPnL(p.pnl, p.pnl_pct)}</td>
                  <td style={{ color: getPositionColor(p.type, (p as any).status) }}>{p.type}</td>
                  <td>
                    <button
                      disabled={submitting}
                      onClick={() =>
                        setConfirming({
                          positionId: p.id,
                          botType: ((p as any).botType || p.bot_type) as string,
                          entryPrice: p.entry_price,
                          currentPrice: p.current_price,
                          quantity: p.quantity,
                          side: p.type
                        })
                      }>
                      Cerrar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {confirming && (
          <div
            className="modal-overlay"
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)' }}>
            <div
              className="modal"
              style={{
                background: '#1e1e1e',
                color: '#fff',
                maxWidth: 420,
                margin: '10% auto',
                padding: 16,
                borderRadius: 8,
                boxShadow: '0 10px 30px rgba(0,0,0,0.4)'
              }}>
              <h4>Confirmar cierre</h4>
              <p>
                Vas a cerrar la posición <strong>{confirming.positionId}</strong> de{' '}
                <strong>{getBotName(confirming.botType)}</strong>.
              </p>
              <p>
                Entrada ${confirming.entryPrice.toFixed(5)} · Actual $
                {confirming.currentPrice.toFixed(5)} · Cantidad {confirming.quantity.toFixed(4)}
              </p>
              <p>
                PnL estimado neto (incluye comisión):{' '}
                <strong>
                  $
                  {estimateNetPnl(
                    confirming.side,
                    confirming.entryPrice,
                    confirming.currentPrice,
                    confirming.quantity
                  ).toFixed(5)}
                </strong>
              </p>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                <button disabled={submitting} onClick={() => setConfirming(null)}>
                  Cancelar
                </button>
                <button
                  disabled={submitting}
                  onClick={() => requestClose(confirming.botType, confirming.positionId)}
                  style={{ background: '#b71c1c', color: '#fff' }}>
                  Sí, cerrar ahora
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default ActivePositions
