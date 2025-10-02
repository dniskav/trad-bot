import { useApiTradingHistory } from '@hooks'
import React, { useEffect, useMemo, useState } from 'react'
import { HistoryItem } from '../HistoryItem'
import type { PositionHistoryProps } from './types'

const PositionHistory: React.FC<PositionHistoryProps> = ({ history, statistics }) => {
  // Generar un ID único para este componente para evitar duplicados
  const componentId = useMemo(() => `ph-${Math.random().toString(36).substr(2, 9)}`, [])

  const [selectedBot, setSelectedBot] = useState<string>(() => {
    if (typeof window === 'undefined') return 'all'
    return window.localStorage.getItem('ph_filter_bot') || 'all'
  })
  const [sortBy, setSortBy] = useState<'date' | 'pnl'>(() => {
    if (typeof window === 'undefined') return 'date'
    const saved = window.localStorage.getItem('ph_sort_by') as 'date' | 'pnl' | null
    return saved || 'date'
  })
  const [page, setPage] = useState<number>(1)
  const [pageSize, setPageSize] = useState<number>(() => {
    const saved = typeof window !== 'undefined' ? window.localStorage.getItem('ph_page_size') : null
    return saved ? parseInt(saved) : 50
  })
  const [fullHistory, setFullHistory] = useState<any[] | null>(null)

  const { fetchTradingHistory, isLoading } = useApiTradingHistory()
  const [showResetConfirm, setShowResetConfirm] = useState(false)
  const [isResetting, setIsResetting] = useState(false)

  // Filtros avanzados
  const [filterEstado, setFilterEstado] = useState<'all' | 'open' | 'closed'>(() => {
    if (typeof window === 'undefined') return 'all'
    const v = window.localStorage.getItem('ph_filter_estado') as any
    return v || 'all'
  })
  const [filterTipo, setFilterTipo] = useState<'all' | 'buy' | 'sell'>(() => {
    if (typeof window === 'undefined') return 'all'
    const v = window.localStorage.getItem('ph_filter_tipo') as any
    return v || 'all'
  })
  const [filterCierre, setFilterCierre] = useState<'all' | 'tp' | 'sl'>(() => {
    if (typeof window === 'undefined') return 'all'
    const v = window.localStorage.getItem('ph_filter_cierre') as any
    return v || 'all'
  })
  const [filterResultado, setFilterResultado] = useState<'all' | 'ganancia' | 'perdida'>(() => {
    if (typeof window === 'undefined') return 'all'
    const v = window.localStorage.getItem('ph_filter_resultado') as any
    return v || 'all'
  })
  const [filterModo, setFilterModo] = useState<'all' | 'synthetic' | 'real'>(() => {
    if (typeof window === 'undefined') return 'all'
    const v = window.localStorage.getItem('ph_filter_modo') as any
    return v || 'all'
  })

  // Persist settings
  useEffect(() => {
    try {
      window.localStorage.setItem('ph_filter_bot', selectedBot)
    } catch {}
  }, [selectedBot])
  useEffect(() => {
    try {
      window.localStorage.setItem('ph_sort_by', sortBy)
    } catch {}
  }, [sortBy])
  useEffect(() => {
    try {
      window.localStorage.setItem('ph_filter_estado', filterEstado)
    } catch {}
  }, [filterEstado])
  useEffect(() => {
    try {
      window.localStorage.setItem('ph_filter_tipo', filterTipo)
    } catch {}
  }, [filterTipo])
  useEffect(() => {
    try {
      window.localStorage.setItem('ph_filter_cierre', filterCierre)
    } catch {}
  }, [filterCierre])
  useEffect(() => {
    try {
      window.localStorage.setItem('ph_filter_resultado', filterResultado)
    } catch {}
  }, [filterResultado])
  useEffect(() => {
    try {
      window.localStorage.setItem('ph_filter_modo', filterModo)
    } catch {}
  }, [filterModo])

  // Cargar historial inicial desde el endpoint
  useEffect(() => {
    const load = async () => {
      const items = await fetchTradingHistory(1, 10000)
      if (Array.isArray(items)) {
        setFullHistory(items)
      }
    }
    load()
  }, [])

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
    let color = '#f1c40f' // cero plu=> amarillo
    if (pnl > 0) color = '#26a69a'
    if (pnl < 0) color = '#ef5350'

    const sign = pnl > 0 ? '+' : pnl === 0 ? '' : ''
    const signPct = pnlPct > 0 ? '+' : pnlPct === 0 ? '' : ''

    return (
      <span style={{ color, fontWeight: 'bold' }}>
        {sign}${pnl.toFixed(5)} ({signPct}
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

  // (Iconos de motivo ya no se usan en la fila; la razón se muestra como texto al final)

  // Preferir SIEMPRE el historial del endpoint si está disponible (siempre devolver array)
  const sourceHistory: any[] = Array.isArray(fullHistory)
    ? (fullHistory as any[])
    : Array.isArray(history)
    ? history
    : []

  const filteredHistory = sourceHistory.filter((pos) => {
    if (selectedBot !== 'all' && pos.bot_type !== selectedBot) return false
    // Modo synthetic/real
    const isSynthetic = !!pos.is_synthetic
    if (filterModo === 'synthetic' && !isSynthetic) return false
    if (filterModo === 'real' && isSynthetic) return false
    // Estado
    const isOpen =
      !pos.is_closed || pos.status === 'OPEN' || pos.status === 'UPDATED' || !pos.close_time
    if (filterEstado === 'open' && !isOpen) return false
    if (filterEstado === 'closed' && isOpen) return false
    // Tipo de operación
    const side = (pos.type || pos.side || '').toString().toLowerCase()
    if (filterTipo !== 'all' && side !== filterTipo) return false
    // Motivo de cierre (tp/sl)
    const reason = (pos.close_reason || '').toString().toLowerCase()
    if (filterCierre === 'tp' && reason !== 'take profit') return false
    if (filterCierre === 'sl' && reason !== 'stop loss') return false
    // Resultado (ganancia/perdida) basado en pnl_net
    const pnlNet = Number(pos.pnl_net || pos.pnl || 0)
    if (filterResultado === 'ganancia' && !(pnlNet > 0)) return false
    if (filterResultado === 'perdida' && !(pnlNet < 0)) return false
    return true
  })

  // Auto-reset de filtros si el endpoint trae datos pero los filtros dejan 0 resultados
  const [didAutoReset, setDidAutoReset] = useState(false)
  useEffect(() => {
    if (
      !didAutoReset &&
      Array.isArray(sourceHistory) &&
      sourceHistory.length > 0 &&
      filteredHistory.length === 0
    ) {
      setSelectedBot('all')
      setFilterEstado('all')
      setFilterTipo('all')
      setFilterCierre('all')
      setFilterResultado('all')
      try {
        window.localStorage.removeItem('ph_filter_bot')
        window.localStorage.removeItem('ph_filter_estado')
        window.localStorage.removeItem('ph_filter_tipo')
        window.localStorage.removeItem('ph_filter_cierre')
        window.localStorage.removeItem('ph_filter_resultado')
      } catch {}
      setDidAutoReset(true)
    }
  }, [sourceHistory, filteredHistory.length, didAutoReset])

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
        <div className="filter-group">
          <label htmlFor={`${componentId}-filter-modo`}>Modo:</label>
          <select
            id={`${componentId}-filter-modo`}
            value={filterModo}
            onChange={(e) => {
              setFilterModo(e.target.value as any)
              setPage(1)
            }}>
            <option value="all">Todos</option>
            <option value="synthetic">Synthetic</option>
            <option value="real">Reales</option>
          </select>
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

      {/* Estadísticas */}
      <div className="statistics-grid">
        {/* Render dinámico de tarjetas por bot presente en statistics (excluye overall al final) */}
        {Object.keys(statistics)
          .filter((k) => k !== 'overall')
          .map((botKey) => (
            <StatCard
              key={botKey}
              title={botKey}
              stats={statistics[botKey]}
              icon={getBotIcon(botKey)}
            />
          ))}
        {/* Resumen general */}
        <StatCard title="General" stats={statistics.overall} icon="📈" />
      </div>

      {/* Filtros */}
      <div className="history-filters">
        <div className="filter-group">
          <label htmlFor={`${componentId}-filter-bot`}>Bot:</label>
          <select
            id={`${componentId}-filter-bot`}
            value={selectedBot}
            onChange={(e) => setSelectedBot(e.target.value as any)}>
            <option value="all">Todos</option>
            {Object.keys(statistics)
              .filter((k) => k !== 'overall')
              .map((botKey) => (
                <option key={botKey} value={botKey}>
                  {botKey}
                </option>
              ))}
          </select>
        </div>
        <div className="filter-group">
          <label htmlFor={`${componentId}-filter-estado`}>Estado:</label>
          <select
            id={`${componentId}-filter-estado`}
            value={filterEstado}
            onChange={(e) => {
              setFilterEstado(e.target.value as any)
              setPage(1)
            }}>
            <option value="all">Todos</option>
            <option value="open">Abiertas</option>
            <option value="closed">Cerradas</option>
          </select>
        </div>
        <div className="filter-group">
          <label htmlFor={`${componentId}-filter-tipo`}>Tipo:</label>
          <select
            id={`${componentId}-filter-tipo`}
            value={filterTipo}
            onChange={(e) => {
              setFilterTipo(e.target.value as any)
              setPage(1)
            }}>
            <option value="all">Todos</option>
            <option value="buy">Buy</option>
            <option value="sell">Sell</option>
          </select>
        </div>
        <div className="filter-group">
          <label htmlFor={`${componentId}-filter-cierre`}>Cierre:</label>
          <select
            id={`${componentId}-filter-cierre`}
            value={filterCierre}
            onChange={(e) => {
              setFilterCierre(e.target.value as any)
              setPage(1)
            }}>
            <option value="all">Todos</option>
            <option value="tp">TP</option>
            <option value="sl">SL</option>
          </select>
        </div>
        <div className="filter-group">
          <label htmlFor={`${componentId}-filter-resultado`}>Resultado:</label>
          <select
            id={`${componentId}-filter-resultado`}
            value={filterResultado}
            onChange={(e) => {
              setFilterResultado(e.target.value as any)
              setPage(1)
            }}>
            <option value="all">Todos</option>
            <option value="ganancia">Ganancias</option>
            <option value="perdida">Pérdidas</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Acciones:</label>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={async () => {
                const items = await fetchTradingHistory(1, 10000)
                if (Array.isArray(items)) setFullHistory(items)
              }}
              disabled={isLoading}>
              {isLoading ? 'Cargando…' : 'Refrescar'}
            </button>
            <button
              onClick={() => setShowResetConfirm(true)}
              style={{ background: '#b91c1c', color: '#fff' }}>
              Reset
            </button>
          </div>
        </div>
        <div className="filter-group">
          <label htmlFor={`${componentId}-filter-sort`}>Ordenar por:</label>
          <select
            id={`${componentId}-filter-sort`}
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}>
            <option value="date">Fecha</option>
            <option value="pnl">PnL</option>
          </select>
        </div>
        <div className="filter-group" style={{ minWidth: 260 }}>
          <label style={{ visibility: 'hidden' }}>Contadores:</label>
          <div style={{ fontSize: 12, opacity: 0.9 }}>
            Abiertas: <strong>{openCount}</strong> · Cerradas: <strong>{closedCount}</strong> ·
            Total: <strong>{totalCount}</strong>
          </div>
        </div>
        <div className="filter-group">
          <label>Página:</label>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={safePage <= 1}>
              ◀
            </button>
            <span style={{ minWidth: 60, textAlign: 'center' }}>
              {safePage} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={safePage >= totalPages}>
              ▶
            </button>
          </div>
        </div>
        <div className="filter-group">
          <label htmlFor={`${componentId}-filter-page-size`}>Tamaño:</label>
          <select
            id={`${componentId}-filter-page-size`}
            value={pageSize}
            onChange={(e) => {
              const next = parseInt(e.target.value)
              setPageSize(next)
              try {
                window.localStorage.setItem('ph_page_size', String(next))
              } catch {}
              setPage(1)
            }}>
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
            <option value={500}>500</option>
            <option value={1000}>1000</option>
          </select>
        </div>
      </div>

      {/* Lista de posiciones */}
      <div className="history-list">
        {/* Encabezados de columnas */}
        {sortedHistory.length > 0 && (
          <div
            className="history-header"
            style={{
              display: 'grid',
              gridTemplateColumns: '1.2fr 1.2fr 0.8fr 1fr 0.8fr 2fr 1fr',
              gap: 8,
              padding: '6px 10px',
              fontSize: 12,
              opacity: 0.8
            }}>
            <span>Bot</span>
            <span>e · s</span>
            <span>Estado</span>
            <span>PnL</span>
            <span>Tipo</span>
            <span>Fechas</span>
            <span>Motivo</span>
          </div>
        )}
        {sortedHistory.length === 0 ? (
          <div className="no-history">
            <p>No hay posiciones en el historial</p>
          </div>
        ) : (
          paginated.map((position, index) => (
            <HistoryItem
              key={index}
              position={position}
              formatPnL={formatPnL}
              formatDate={formatDate}
            />
          ))
        )}
      </div>

      {showResetConfirm && (
        <div
          className="modal-overlay"
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowResetConfirm(false)
          }}
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 9999 }}>
          <div
            className="modal"
            onClick={(e) => e.stopPropagation()}
            style={{
              background: '#1e1e1e',
              color: '#fff',
              maxWidth: 420,
              margin: '10% auto',
              padding: 16,
              borderRadius: 8,
              boxShadow: '0 10px 30px rgba(0,0,0,0.4)'
            }}>
            <h4>Confirmar reset</h4>
            <p>Vas a resetear por completo el historial. Esta acción no se puede deshacer.</p>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button disabled={isResetting} onClick={() => setShowResetConfirm(false)}>
                Cancelar
              </button>
              <button
                disabled={isResetting}
                onClick={async () => {
                  setIsResetting(true)
                  try {
                    await fetch('/api/test/reset-history', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' }
                    })
                    const items = await fetchTradingHistory(1, 10000)
                    if (Array.isArray(items)) setFullHistory(items)
                    setShowResetConfirm(false)
                  } catch (e) {
                    console.error('Reset history failed', e)
                  } finally {
                    setIsResetting(false)
                  }
                }}
                style={{ background: '#b71c1c', color: '#fff' }}>
                Sí, resetear
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default PositionHistory
