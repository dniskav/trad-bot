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

  const filteredHistory = history.filter(
    (pos) => selectedBot === 'all' || pos.bot_type === selectedBot
    // Mostrar todas las posiciones, tanto cerradas como abiertas
  )

  const sortedHistory = [...filteredHistory].sort((a, b) => {
    if (sortBy === 'date') {
      // Para posiciones abiertas (sin exit_time), usar entry_time
      const dateA = a.exit_time || a.close_time || a.entry_time
      const dateB = b.exit_time || b.close_time || b.entry_time
      return new Date(dateB).getTime() - new Date(dateA).getTime()
    } else {
      return (b.pnl_net || 0) - (a.pnl_net || 0)
    }
  })

  const StatCard: React.FC<{ title: string; stats: any; icon: string }> = ({
    title,
    stats,
    icon
  }) => {
    // Valores por defecto para evitar errores de undefined
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
            <span className="stat-value">{safeStats.total_trades}</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Win Rate:</span>
            <span
              className="stat-value"
              style={{ color: safeStats.win_rate >= 50 ? '#26a69a' : '#ef5350' }}>
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
            <span className="stat-value" style={{ color: '#26a69a' }}>
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
                  <span className="bot-name">{position.bot_type || 'N/A'}</span>
                  {/* Flags para modo synthetic y plugin bot */}
                  {position.is_synthetic && (
                    <span className="synthetic-flag" title="Posición Synthetic">
                      🧪
                    </span>
                  )}
                  {position.is_plugin_bot && (
                    <span className="plugin-flag" title="Bot Plug-and-Play">
                      🔌
                    </span>
                  )}
                  {/* Indicador de estado */}
                  {(!position.is_closed ||
                    position.status === 'UPDATED' ||
                    position.status === 'OPEN') && (
                    <span className="status-indicator open">🟢 En curso</span>
                  )}
                </div>
                <div className="history-type">
                  <span className={`position-type ${position.type?.toLowerCase() || 'unknown'}`}>
                    {position.type || 'N/A'}
                  </span>
                </div>
                <div className="history-reason">
                  <span className="reason-icon">{getCloseReasonIcon(position.close_reason)}</span>
                  <span className="reason-text">{position.close_reason || 'N/A'}</span>
                </div>
              </div>

              <div className="history-details">
                <div className="price-info">
                  <span className="price-label">Entrada:</span>
                  <span className="price-value">${position.entry_price?.toFixed(5)}</span>
                  <span className="price-label">Salida:</span>
                  <span className="price-value">${position.exit_price?.toFixed(5)}</span>
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
                      <span className="fees-value">${position.total_fees.toFixed(5)}</span>
                    </div>
                  )}
                </div>

                <div className="time-info">
                  <span className="time-label">Cerrado:</span>
                  <span className="time-value">
                    {formatDate(position.close_time || position.exit_time)}
                  </span>
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
