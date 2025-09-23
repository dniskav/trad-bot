import React from 'react'
import type { HistoryItemProps } from './types'

const HistoryItem: React.FC<HistoryItemProps> = ({
  position,
  getBotIcon,
  getCloseReasonIcon,
  formatPnL,
  formatDate
}) => {
  return (
    <div className="history-item">
      <div className="history-header">
        <div className="history-bot">
          <span className="bot-icon">{getBotIcon(position.bot_type)}</span>
          <span className="bot-name">{position.bot_type || 'N/A'}</span>
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
          {(!position.is_closed || position.status === 'UPDATED' || position.status === 'OPEN') && (
            <span className="status-indicator open">🟢 En curso</span>
          )}
        </div>
        <div className="history-type">
          <span className={`position-type ${position.type?.toLowerCase() || 'unknown'}`}>
            {position.type || 'N/A'}
          </span>
        </div>
        <div className="history-reason">
          <span className="reason-icon">{getCloseReasonIcon(position.close_reason || '')}</span>
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
            {formatDate(position.close_time ?? position.exit_time ?? null)}
          </span>
        </div>
      </div>
    </div>
  )
}

export default HistoryItem
