import React from 'react'
import './styles.css'
import type { BalanceStatusProps } from './types'

const BalanceStatus: React.FC<BalanceStatusProps> = ({
  totalPnl,
  balanceChangePct,
  isProfitable
}) => {
  const getStatusColor = () => {
    const pnl = Number(totalPnl || 0)
    const change = Number(balanceChangePct || 0)
    const isNeutral = Math.abs(pnl) < 0.01 && Math.abs(change) < 0.01

    if (isNeutral) return '#9ca3af' // Gris para neutral
    if (isProfitable) return '#26a69a' // Verde para ganancias
    return '#ef5350' // Rojo para pérdidas
  }

  const getStatusText = () => {
    const pnl = Number(totalPnl || 0)
    const change = Number(balanceChangePct || 0)
    const isNeutral = Math.abs(pnl) < 0.01 && Math.abs(change) < 0.01

    if (isNeutral) return '⚪ Neutral'
    if (isProfitable) return '🟢 Rentable'
    return '🔴 En Pérdida'
  }

  return (
    <span className="balance-status" style={{ color: getStatusColor() }}>
      {getStatusText()}
    </span>
  )
}

export default BalanceStatus
