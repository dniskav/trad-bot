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
  enableLogs = false,
  enablePulse = true,
  pulseThrottle = 500
}) => {
  // Usar detector de WebSockets genérico
  const { isConnected, isConnecting, error, lastMessage, detectTargetConnections } =
    useWebSocketDetector({
      urlContains,
      checkInterval,
      enableLogs,
      enablePulse,
      pulseThrottle,
      label
    })

  const [pulse, setPulse] = useState(false)

  // Detectar conexiones específicas
  const { hasTargetConnection } = detectTargetConnections()

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
      connected={isConnected || hasTargetConnection}
      connecting={isConnecting}
      error={error}
      pulsing={pulse}
    />
  )
}

export default WebSocketStatus
