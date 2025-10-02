import React from 'react'
import type { StatusBadgeProps } from '../../types'
import '../../WebSocketStatus.css'

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  label,
  connected,
  connecting,
  error,
  pulsing
}) => {
  const getStatusClass = () => {
    if (connected) {
      return pulsing ? 'ws-status-badge connected pulsing' : 'ws-status-badge connected'
    }
    if (connecting) return 'ws-status-badge connecting'
    if (error) return 'ws-status-badge error'
    return 'ws-status-badge disconnected'
  }

  const icon = connected ? '🟢' : connecting ? '🟡' : error ? '🔴' : '⚪'

  return (
    <div className={getStatusClass()}>
      <span className="status-icon">{icon}</span>
      <span className="status-label">{label}</span>
    </div>
  )
}

export default StatusBadge
