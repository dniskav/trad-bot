import React, { useEffect, useState } from 'react'
import { useWebSocketContext } from '../../contexts/WebSocketContext'
import { useWebSocketDetector } from './hooks'
import type { StatusBadgeProps } from './types'

const StatusBadge: React.FC<StatusBadgeProps> = ({
  label,
  connected,
  connecting,
  error,
  pulsing
}) => {
  const getBorderColor = () => {
    if (connected) {
      // Verde más claro cuando está pulsando
      return pulsing ? '#34d399' : '#10b981'
    }
    if (connecting) return '#f59e0b'
    if (error) return '#ef4444'
    return '#6b7280'
  }
  const getGlowColor = () => `${getBorderColor()}80`

  const icon = connected ? '🟢' : connecting ? '🟡' : error ? '🔴' : '⚪'

  return (
    <div
      style={{
        backgroundColor: 'transparent',
        backdropFilter: 'none',
        border: `2px solid ${getBorderColor()}`,
        borderRadius: '4px',
        padding: '0 0.5rem',
        fontSize: '0.5rem',
        color: 'white',
        zIndex: 1000,
        minWidth: 'auto',
        boxShadow: pulsing ? `0 0 5px 1px ${getGlowColor()}` : 'none',
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '3px'
      }}>
      <span style={{ fontSize: '0.5rem' }}>{icon}</span>
      <span style={{ fontSize: '0.4rem', fontWeight: 'bold' }}>{label}</span>
    </div>
  )
}

export const WebSocketStatus: React.FC = () => {
  const { isConnected, isConnecting, error, lastMessage } = useWebSocketContext()

  // Usar detector de WebSockets para BookTick con configuración específica
  const {
    isConnected: binanceConnected,
    isConnecting: binanceConnecting,
    error: binanceError,
    lastMessage: binanceLastMessage,
    label: binanceLabel,
    detectTargetConnections
  } = useWebSocketDetector({
    urlContains: ['binance', 'stream', 'dogeusdt'],
    checkInterval: 2000,
    enableLogs: false,
    enablePulse: true,
    pulseThrottle: 500,
    label: 'BookTick'
  })

  const [serverPulse, setServerPulse] = useState(false)
  const [binancePulse, setBinancePulse] = useState(false)

  // Detectar conexiones específicas
  const { hasTargetConnection } = detectTargetConnections()

  useEffect(() => {
    if (!lastMessage || (lastMessage as any).message?.__source !== 'server') return
    setServerPulse(true)
    const t = setTimeout(() => setServerPulse(false), 250)
    return () => clearTimeout(t)
  }, [lastMessage?.id])

  // Pulse para BookTick cuando llega mensaje real interceptado
  useEffect(() => {
    if (!binanceLastMessage) return
    setBinancePulse(true)
    const t = setTimeout(() => setBinancePulse(false), 250)
    return () => clearTimeout(t)
  }, [binanceLastMessage])

  return (
    <div style={{ display: 'flex', gap: '6px' }}>
      <StatusBadge
        label="Server"
        connected={isConnected}
        connecting={isConnecting}
        error={error}
        pulsing={serverPulse}
      />
      <StatusBadge
        label={binanceLabel}
        connected={binanceConnected || hasTargetConnection}
        connecting={binanceConnecting}
        error={binanceError}
        pulsing={binancePulse}
      />
    </div>
  )
}

export default WebSocketStatus
