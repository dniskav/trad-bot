import React from 'react'
import { useWsObserver } from '../../hooks/useWsObserver'
import { StatusBadge } from '../StatusBadge/StatusBadge'

export interface DetectorBadgeProps {
  label: string
  id: string
  url?: string | string[]
  urlContains?: string | string[]
  pulseThrottle?: number
}

export const DetectorBadge: React.FC<DetectorBadgeProps> = ({
  label,
  id,
  url,
  urlContains,
  pulseThrottle = 500
}) => {
  const { isConnected, isConnecting, pulsing } = useWsObserver({
    id,
    url,
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

export default DetectorBadge
