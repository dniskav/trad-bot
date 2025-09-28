export interface StatusBadgeProps {
  label: string
  connected: boolean
  connecting: boolean
  error: string | null
  pulsing: boolean
}

export interface WebSocketStatusProps {
  label: string
  socketId: string
  urlContains?: string[]
  checkInterval?: number
  enablePulse?: boolean
  pulseThrottle?: number
}
