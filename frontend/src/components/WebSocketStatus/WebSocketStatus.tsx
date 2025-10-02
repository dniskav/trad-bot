import React from 'react'
import { StatusBadge } from './components/StatusBadge/StatusBadge'
import { useWsObserver } from './hooks'
import type { WebSocketStatusProps } from './types'
import './WebSocketStatus.css'

export const WebSocketStatus: React.FC<WebSocketStatusProps> = ({
  label,
  socketId,
  urlContains = [],
  pulseThrottle = 500
}) => {
  // Usar el nuevo hook useWsObserver
  const { isConnected, isConnecting, pulsing } = useWsObserver({
    id: socketId || 'default',
    urlContains,
    pulseThrottle
  })

  return (
    <StatusBadge
      label={label}
      connected={isConnected}
      connecting={isConnecting}
      error={null}
      pulsing={pulsing}
    />
  )
}

export default WebSocketStatus
