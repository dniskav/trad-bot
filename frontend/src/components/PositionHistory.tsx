import React, { useState } from 'react'

interface PositionHistoryProps {
  history: any[]
  statistics: {
    conservative: any
    aggressive: any
    overall: any
  }
}

const PositionHistory: React.FC<PositionHistoryProps> = ({ history, statistics }) => {
  const [selectedBot, setSelectedBot] = useState<'all' | 'conservative' | 'aggressive'>('all')
  const [sortBy, setSortBy] = useState<'date' | 'pnl'>('date')

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
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
        {sign}${pnl.toFixed(4)} ({sign}
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
      default:
        return '🤖'
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

  const filteredHistory = history.filter(
    (pos) => selectedBot === 'all' || pos.bot_type === selectedBot
  )

  const sortedHistory = [...filteredHistory].sort((a, b) => {
    if (sortBy === 'date') {
      return new Date(b.exit_time).getTime() - new Date(a.exit_time).getTime()
    } else {
      return b.pnl_net - a.pnl_net
    }
  })

  const StatCard: React.FC<{ title: string; stats: any; icon: string }> = ({
    title,
    stats,
    icon
  }) => (
    <div className="stat-card">
      <div className="stat-header">
        <span className="stat-icon">{icon}</span>
        <span className="stat-title">{title}</span>
      </div>
      <div className="stat-content">
        <div className="stat-row">
          <span className="stat-label">Trades:</span>
          <span className="stat-value">{stats.total_trades}</span>
        </div>
        <div className="stat-row">
          <span className="stat-label">Win Rate:</span>
          <span
            className="stat-value"
            style={{ color: stats.win_rate >= 50 ? '#26a69a' : '#ef5350' }}>
            {stats.win_rate.toFixed(1)}%
          </span>
        </div>
        <div className="stat-row">
          <span className="stat-label">PnL Total:</span>
          <span
            className="stat-value"
            style={{ color: stats.total_pnl_net >= 0 ? '#26a69a' : '#ef5350' }}>
            ${stats.total_pnl_net.toFixed(4)}
          </span>
        </div>
        <div className="stat-row">
          <span className="stat-label">Mejor Trade:</span>
          <span className="stat-value" style={{ color: '#26a69a' }}>
            ${stats.best_trade.toFixed(4)}
          </span>
        </div>
      </div>
    </div>
  )

  return (
    <div className="position-history">
      <h3>📊 Historial de Posiciones</h3>

      {/* Estadísticas */}
      <div className="statistics-grid">
        <StatCard title="Conservador" stats={statistics.conservative} icon="🐌" />
        <StatCard title="Agresivo" stats={statistics.aggressive} icon="⚡" />
        <StatCard title="General" stats={statistics.overall} icon="📈" />
      </div>

      {/* Filtros */}
      <div className="history-filters">
        <div className="filter-group">
          <label>Bot:</label>
          <select value={selectedBot} onChange={(e) => setSelectedBot(e.target.value as any)}>
            <option value="all">Todos</option>
            <option value="conservative">Conservador</option>
            <option value="aggressive">Agresivo</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Ordenar por:</label>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value as any)}>
            <option value="date">Fecha</option>
            <option value="pnl">PnL</option>
          </select>
        </div>
      </div>

      {/* Lista de posiciones */}
      <div className="history-list">
        {sortedHistory.length === 0 ? (
          <div className="no-history">
            <p>No hay posiciones en el historial</p>
          </div>
        ) : (
          sortedHistory.map((position, index) => (
            <div key={index} className="history-item">
              <div className="history-header">
                <div className="history-bot">
                  <span className="bot-icon">{getBotIcon(position.bot_type)}</span>
                  <span className="bot-name">{position.bot_type}</span>
                </div>
                <div className="history-type">
                  <span className={`position-type ${position.type.toLowerCase()}`}>
                    {position.type}
                  </span>
                </div>
                <div className="history-reason">
                  <span className="reason-icon">{getCloseReasonIcon(position.close_reason)}</span>
                  <span className="reason-text">{position.close_reason}</span>
                </div>
              </div>

              <div className="history-details">
                <div className="price-info">
                  <span className="price-label">Entrada:</span>
                  <span className="price-value">${position.entry_price?.toFixed(4)}</span>
                  <span className="price-label">Salida:</span>
                  <span className="price-value">${position.exit_price?.toFixed(4)}</span>
                </div>

                <div className="pnl-info">
                  <div className="pnl-item">
                    <span className="pnl-label">PnL Bruto:</span>
                    {formatPnL(position.pnl || 0, position.pnl_pct || 0)}
                  </div>
                  <div className="pnl-item">
                    <span className="pnl-label">PnL Neto:</span>
                    {formatPnL(position.pnl_net || 0, position.pnl_net_pct || 0)}
                  </div>
                  {position.total_fees && (
                    <div className="fees-item">
                      <span className="fees-label">Comisiones:</span>
                      <span className="fees-value">${position.total_fees.toFixed(4)}</span>
                    </div>
                  )}
                </div>

                <div className="time-info">
                  <span className="time-label">Cerrado:</span>
                  <span className="time-value">{formatDate(position.exit_time)}</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default PositionHistory
