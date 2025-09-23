import React, { useEffect } from 'react'
import './styles.css'
import type { ToastProps } from './types'

const Toast: React.FC<ToastProps> = ({ message, type, duration = 2000, onClose }) => {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose()
    }, duration)
    return () => clearTimeout(timer)
  }, [duration, onClose])

  const getToastStyles = () => {
    switch (type) {
      case 'success':
        return {
          backgroundColor: 'var(--binance-green)',
          borderColor: 'var(--binance-green)',
          color: 'white'
        }
      case 'error':
        return {
          backgroundColor: 'var(--binance-red)',
          borderColor: 'var(--binance-red)',
          color: 'white'
        }
      case 'info':
        return {
          backgroundColor: 'var(--binance-yellow)',
          borderColor: 'var(--binance-yellow)',
          color: 'var(--binance-black)'
        }
      default:
        return {
          backgroundColor: 'var(--binance-gray)',
          borderColor: 'var(--binance-gray)',
          color: 'var(--binance-white)'
        }
    }
  }

  const getIcon = () => {
    switch (type) {
      case 'success':
        return '✅'
      case 'error':
        return '❌'
      case 'info':
        return 'ℹ️'
      default:
        return '📢'
    }
  }

  return (
    <div className="toast" style={getToastStyles()}>
      <div className="toast-content">
        <span className="toast-icon">{getIcon()}</span>
        <span className="toast-message">{message}</span>
        <button className="toast-close" onClick={onClose}>
          ×
        </button>
      </div>
    </div>
  )
}

export default Toast
