import React, { useState } from 'react'
import { API_CONFIG } from '../../config/api'
import { useActivePositions } from '../../hooks'
import './styles.css'

interface Position {
  positionId: string
  symbol: string
  initialMargin: string
  maintMargin: string
  unrealizedProfit: string
  positionInitialMargin: string
  openOrderInitialMargin: string
  leverage: string
  isolated: boolean
  entryPrice: string
  maxNotional: string
  bidNotional: string
  askNotional: string
  positionSide: string
  positionAmt: string
  updateTime: string
}

const ActivePositions: React.FC = () => {
  const { positions, loading, error, refreshPositions } = useActivePositions()
  const [closingPosition, setClosingPosition] = useState<string | null>(null)

  const handleClosePosition = async (positionId: string) => {
    setClosingPosition(positionId)
    try {
      const response = await fetch(
        `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.POSITIONS_CLOSE}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            positionId: positionId,
            reason: 'manual'
          })
        }
      )

      const data = await response.json()

      if (data.success) {
        // Refrescar posiciones después de cerrar
        refreshPositions()
      } else {
        alert(`Error: ${data.message || 'No se pudo cerrar la posición'}`)
      }
    } catch (err) {
      alert('Error de conexión al cerrar posición')
      console.error('Error closing position:', err)
    } finally {
      setClosingPosition(null)
    }
  }

  const formatPnL = (unrealizedProfit: string) => {
    const pnl = parseFloat(unrealizedProfit)
    const isPositive = pnl >= 0
    const color = isPositive ? '#26a69a' : '#ef5350'
    const sign = isPositive ? '+' : ''

    return (
      <span className="pnl-value" style={{ color }}>
        {sign}${pnl.toFixed(4)}
      </span>
    )
  }

  const getPositionColor = (side: string) => {
    return side === 'BUY' ? '#26a69a' : '#ef5350'
  }

  if (loading) {
    return (
      <div className="active-positions">
        <div className="positions-status">
          <p>Cargando posiciones...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="active-positions">
        <div className="positions-status">
          <p>Error: {error}</p>
          <button onClick={refreshPositions} className="retry-button">
            Reintentar
          </button>
        </div>
      </div>
    )
  }

  if (positions.length === 0) {
    return (
      <div className="active-positions">
        <div className="positions-status">
          <p>No hay posiciones activas</p>
        </div>
      </div>
    )
  }

  // Calcular totales
  const totals = positions.reduce(
    (acc, position) => {
      const pnl = position.pnl
      acc.totalPnl += pnl
      if (pnl >= 0) {
        acc.gains += pnl
        acc.gainCount++
      } else {
        acc.losses += Math.abs(pnl)
        acc.lossCount++
      }
      return acc
    },
    { totalPnl: 0, gains: 0, losses: 0, gainCount: 0, lossCount: 0 }
  )

  return (
    <div className="active-positions">
      {/* Resumen */}
      <div className="positions-summary">
        <div className="summary-item">
          <div className="summary-label">Total P&L:</div>
          <div
            className="summary-value"
            style={{ color: totals.totalPnl >= 0 ? '#26a69a' : '#ef5350' }}>
            {totals.totalPnl >= 0 ? '+' : ''}${totals.totalPnl.toFixed(4)}
          </div>
        </div>
        <div className="summary-item">
          <div className="summary-label">Ganancias ({totals.gainCount}):</div>
          <div className="summary-value" style={{ color: '#26a69a' }}>
            +${totals.gains.toFixed(4)}
          </div>
        </div>
        <div className="summary-item">
          <div className="summary-label">Pérdidas ({totals.lossCount}):</div>
          <div className="summary-value" style={{ color: '#ef5350' }}>
            -${totals.losses.toFixed(4)}
          </div>
        </div>
        <div className="summary-item">
          <button onClick={refreshPositions} className="refresh-button">
            🔄 Actualizar
          </button>
        </div>
      </div>

      {/* Tabla de posiciones */}
      <div className="positions-table-container">
        <table className="positions-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Símbolo</th>
              <th>Lado</th>
              <th>Entrada</th>
              <th>Cantidad</th>
              <th>Leverage</th>
              <th>P&L</th>
              <th>Estado</th>
              <th>Acción</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((position) => (
              <tr key={position.positionId}>
                <td className="position-id">{position.positionId.slice(0, 8)}...</td>
                <td>{position.symbol}</td>
                <td>
                  <span
                    className="side-badge"
                    style={{
                      color: getPositionColor(position.positionSide),
                      fontWeight: 'bold'
                    }}>
                    {position.positionSide}
                  </span>
                </td>
                <td>${parseFloat(position.entryPrice).toFixed(5)}</td>
                <td>{parseFloat(position.positionAmt).toFixed(4)}</td>
                <td>{position.leverage}x</td>
                <td>{formatPnL(position.unrealizedProfit)}</td>
                <td>
                  <span className="status-badge" style={{ color: '#26a69a' }}>
                    OPEN
                  </span>
                </td>
                <td>
                  <button
                    onClick={() => handleClosePosition(position.positionId)}
                    disabled={closingPosition === position.positionId}
                    className="close-button">
                    {closingPosition === position.positionId ? 'Cerrando...' : 'Cerrar'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default ActivePositions
