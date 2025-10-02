import React from 'react'
import './styles.css'
import type { ProgressBarProps } from './types'

const ProgressBar: React.FC<ProgressBarProps> = ({
  isConnected,
  isConnecting,
  error,
  setupComplete
}) => {
  const getProgressWidth = () => {
    if (isConnected && setupComplete) return '100%'
    if (isConnected && !setupComplete) return '75%'
    if (isConnecting) return '50%'
    return '0%'
  }

  const getProgressColor = () => {
    if (error) return '#ef4444'
    if (isConnected && setupComplete) return '#10b981'
    if (isConnected && !setupComplete) return '#fbbf24'
    if (isConnecting) return '#fbbf24'
    return '#6b7280'
  }

  return (
    <div className="progress-bar-container">
      <div
        className="progress-bar"
        style={{
          width: getProgressWidth(),
          backgroundColor: getProgressColor(),
          transition: 'width 0.5s ease, background-color 0.5s ease'
        }}
      />
    </div>
  )
}

export default ProgressBar
