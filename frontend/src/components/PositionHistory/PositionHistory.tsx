import React, { useEffect, useState } from 'react'
import { useApiTradingHistory } from '../../hooks'
import type { PositionHistoryProps } from './types'

const PositionHistory: React.FC<PositionHistoryProps> = ({ history, statistics }) => {
  const [selectedBot, setSelectedBot] = useState<string>('all')
  const [sortBy, setSortBy] = useState<'date' | 'pnl'>('date')
  const [page, setPage] = useState<number>(1)
  const [pageSize, setPageSize] = useState<number>(50)
  const [fullHistory, setFullHistory] = useState<any[] | null>(null)

  const { data: tradingHistoryData } = useApiTradingHistory()

  useEffect(() => {
    if (tradingHistoryData && Array.isArray(tradingHistoryData) && tradingHistoryData.length > 0) {
      setFullHistory(tradingHistoryData)
    }
  }, [tradingHistoryData])

  const formatDate = (dateString: string | null) => {
    if (!dateString || dateString === 'En curso') {
      return 'En curso'
    }
    const date = new Date(dateString)
    if (isNaN(date.getTime())) {
      return 'Fecha inválida'
    }
    return date.toLocaleString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatPnL = (pnl: number, pnlPct: number) => {
    const isPositive = pnl >= 0
    const color = isPositive ? '#26a69a' : '#ef5350'
    const sign = isPositive ? '+' : ''

    return (
      <span style={{ color, fontWeight: 'bold' }}>
        {sign}${pnl.toFixed(5)} ({sign}
        {pnlPct.toFixed(2)}%)
      </span>
    )
  }

  const getBotIcon = (botType: string) => {
    switch (botType) {
      case 'conservative':
        return '🐌'
      case 'aggressive':
        return '⚡'
      case 'rsibot':
        return '📊'
      case 'macdbot':
        return '📈'
      case 'simplebot':
        return '🤖'
      default:
        return '🔧'
    }
  }

  const getCloseReasonIcon = (reason: string) => {
    switch (reason) {
      case 'Stop Loss':
        return '🛑'
      case 'Take Profit':
        return '🎯'
      case 'Señal Contraria':
        return '🔄'
      default:
        return '📊'
    }
  }

  const sourceHistory = fullHistory && fullHistory.length >= history.length ? fullHistory : history

  const filteredHistory = sourceHistory.filter(
    (pos) => selectedBot === 'all' || pos.bot_type === selectedBot
  )

  const sortedHistory = [...filteredHistory].sort((a, b) => {
    if (sortBy === 'date') {
      const dateA = a.exit_time || a.close_time || a.entry_time
      const dateB = b.exit_time || b.close_time || b.entry_time
      return new Date(dateB).getTime() - new Date(dateA).getTime()
    } else {
      return (b.pnl_net || 0) - (a.pnl_net || 0)
    }
  })

  const totalPages = Math.max(1, Math.ceil(sortedHistory.length / pageSize))
  const safePage = Math.min(page, totalPages)
  const paginated = sortedHistory.slice((safePage - 1) * pageSize, safePage * pageSize)

  const openCount = filteredHistory.filter(
    (p: any) => !p.is_closed || p.status === 'OPEN' || p.status === 'UPDATED' || !p.close_time
  ).length
  const closedCount = filteredHistory.length - openCount
  const totalCount = filteredHistory.length

  const StatCard: React.FC<{ title: string; stats: any; icon: string }> = ({
    title,
    stats,
    icon
  }) => {
    const safeStats = {
      total_trades: stats?.total_trades || 0,
      win_rate: stats?.win_rate || 0,
      total_pnl_net: stats?.total_pnl_net || 0,
      best_trade: stats?.best_trade || 0
    }

    return (
      <div className="stat-card">
        <div className="stat-header">
          <span className="stat-icon">{icon}</span>
          <span className="stat-title">{title}</span>
        </div>
        <div className="stat-content">
          <div className="stat-row">
            <span className="stat-label">Trades:</span>
            <span className="stat-value" style={{ color: '#f1c40f', fontWeight: 'bold' }}>
              {safeStats.total_trades}
            </span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Win Rate:</span>
            <span
              className="stat-value"
              style={{
                color: safeStats.win_rate > 0 ? '#26a69a' : '#ef5350',
                fontWeight: 'bold'
              }}>
              {safeStats.win_rate.toFixed(1)}%
            </span>
          </div>
          <div className="stat-row">
            <span className="stat-label">PnL Total:</span>
            <span
              className="stat-value"
              style={{ color: safeStats.total_pnl_net >= 0 ? '#26a69a' : '#ef5350' }}>
              ${safeStats.total_pnl_net.toFixed(5)}
            </span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Mejor Trade:</span>
            <span
              className="stat-value"
              style={{ color: safeStats.best_trade >= 0 ? '#26a69a' : '#ef5350' }}>
              ${safeStats.best_trade.toFixed(5)}
            </span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="position-history">
      <h3>📊 Historial de Posiciones</h3>
      {/* ...rest of JSX identical... */}
    </div>
  )
}

export default PositionHistory
