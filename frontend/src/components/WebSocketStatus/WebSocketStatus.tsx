import React, { useEffect, useState } from 'react'
import { useWebSocketDetector } from './hooks'
import { StatusBadge } from './StatusBadge'
import type { WebSocketStatusProps } from './types'
import './WebSocketStatus.css'

export const WebSocketStatus: React.FC<WebSocketStatusProps> = ({
  label,
  socketId: _socketId, // Renamed to avoid unused warning
  urlContains = [],
  checkInterval = 2000,
  enablePulse = true,
  pulseThrottle = 500
}) => {
  // Usar detector de WebSockets genérico
  const { isConnected, isConnecting, error, lastMessage } = useWebSocketDetector({
    urlContains,
    checkInterval,
    enablePulse,
    pulseThrottle,
    label
  })

  const [pulse, setPulse] = useState(false)

  // Pulse cuando llega mensaje real interceptado
  useEffect(() => {
    if (!lastMessage) return
    setPulse(true)
    const t = setTimeout(() => setPulse(false), 250)
    return () => clearTimeout(t)
  }, [lastMessage])

  return (
    <StatusBadge
      label={label}
      connected={isConnected}
      connecting={isConnecting}
      error={error}
      pulsing={pulse}
    />
  )
}

export default WebSocketStatus
