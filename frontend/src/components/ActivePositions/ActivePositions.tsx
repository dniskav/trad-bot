import { API_CONFIG } from '@config/api'
import { useActivePositions } from '@hooks'
import apiClient from '@services/apiClient'
import React, { useState } from 'react'
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
      const { data } = await apiClient.post(API_CONFIG.ENDPOINTS.POSITIONS_CLOSE, {
        positionId,
        reason: 'manual'
      })

      if (data?.success) {
        refreshPositions()
      } else {
        // Forzar refetch en caso de error por posible desincronización
        refreshPositions()
        const msg = data?.message || data?.detail || 'No se pudo cerrar la posición'
        alert(`Error: ${msg}`)
      }
    } catch (err) {
      const msg = (err as any)?.response?.data?.message || (err as Error).message
      alert(`Error al cerrar posición: ${msg}`)
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

  const formatValue = (position: Position) => {
    const quantity = parseFloat(position.positionAmt)
    const entryPrice = parseFloat(position.entryPrice)
    const value = Math.abs(quantity) * entryPrice
    const pnl = parseFloat(position.unrealizedProfit)
    const color = pnl >= 0 ? '#26a69a' : '#ef5350'

    return (
      <span className="value-amount" style={{ color }}>
        ${value.toFixed(2)}
      </span>
    )
  }

  const getPositionColor = (side: string) => {
    return side === 'BUY' ? '#26a69a' : '#ef5350'
  }

  const getOperationSide = (position: Position) => {
    const amt = parseFloat(position.positionAmt)
    return amt >= 0 ? 'BUY' : 'SELL'
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
      const pnl = parseFloat(position.unrealizedProfit)
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
              <th>SYMBOL</th>
              <th>SIDE</th>
              <th>ENTRY PRICE</th>
              <th>QUANTITY</th>
              <th>VALUE</th>
              <th>X</th>
              <th>P&L</th>
              <th>STATUS</th>
              <th>ACTION</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((position) => {
              const pnl = parseFloat(position.unrealizedProfit)
              const rowClass = pnl > 0 ? 'row-profit' : pnl < 0 ? 'row-loss' : ''
              return (
                <tr key={position.positionId} className={rowClass}>
                  <td className="position-id">{position.positionId.slice(0, 8)}...</td>
                  <td>{position.symbol}</td>
                  <td>
                    {(() => {
                      const opSide = getOperationSide(position)
                      const sideLabel = `${position.positionSide} / ${opSide}`
                      return (
                        <span
                          className="side-badge"
                          style={{ color: getPositionColor(opSide), fontWeight: 'bold' }}>
                          {sideLabel}
                        </span>
                      )
                    })()}
                  </td>
                  <td>${parseFloat(position.entryPrice).toFixed(5)}</td>
                  <td>{parseFloat(position.positionAmt).toFixed(4)}</td>
                  <td>{formatValue(position)}</td>
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
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default ActivePositions
