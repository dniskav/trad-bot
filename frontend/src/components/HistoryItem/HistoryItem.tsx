import React from 'react'
import type { HistoryItemProps } from './types'

const HistoryItem: React.FC<HistoryItemProps> = ({
  position,
  getCloseReasonIcon,
  formatPnL,
  formatDate
}) => {
  const isOpen = !position.is_closed || position.status === 'UPDATED' || position.status === 'OPEN'
  const idStr = `${(position as any).order_id || ''} ${(position as any).position_id || ''}`
    .toString()
    .toLowerCase()
  const isSynthetic = Boolean((position as any).is_synthetic) || idStr.includes('synth')
  const reason = position.close_reason || ''
  const isTP = !isOpen && reason === 'Take Profit'
  const isSL = !isOpen && reason === 'Stop Loss'
  const rowClass = `history-row ${isOpen ? 'open' : isTP ? 'tp' : isSL ? 'sl' : 'open'}`

  return (
    <div className={rowClass}>
      <span className="row-col bot">
        <span className="mode-flag" title={isSynthetic ? 'Synthetic' : 'Real'}>
          {isSynthetic ? '🧪' : '💼'}
        </span>
        <span className="bot-name">{position.bot_type || 'N/A'}</span>
      </span>
      <span className="row-col prices">
        <span className="label">e</span>
        <span className="value">${position.entry_price?.toFixed(5)}</span>
        <span className="sep">·</span>
        <span className="label">s</span>
        <span className="value">
          {isOpen ? 'pendiente…' : `$${position.exit_price?.toFixed(5) ?? '-'}`}
        </span>
      </span>
      <span className="row-col status">
        <span className="value">
          {isOpen ? 'En curso' : isTP ? 'TP' : isSL ? 'SL' : getCloseReasonIcon(reason)}
        </span>
      </span>
      <span className="row-col pnl">
        <span className="label">PnL</span>
        <span className="value">{formatPnL(position.pnl_net || 0, position.pnl_net_pct || 0)}</span>
      </span>
      <span className="row-col side">
        <span className={`position-type ${position.type?.toLowerCase() || 'unknown'}`}>
          {(position.type || 'N/A').toUpperCase()}
        </span>
      </span>
      <span className="row-col dates">
        <span className="label">Inicio</span>
        <span className="value">{formatDate((position as any).entry_time || null)}</span>
        <span className="sep">·</span>
        <span className="label">Cierre</span>
        <span className="value">
          {formatDate(position.close_time ?? position.exit_time ?? null)}
        </span>
      </span>
    </div>
  )
}

export default HistoryItem
