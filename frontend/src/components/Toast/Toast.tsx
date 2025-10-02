import { useUniqueId } from '@hooks/useUniqueId'
import React, { useEffect, useState } from 'react'
import './styles.css'
import type { ToastProps } from './types'

const Toast: React.FC<ToastProps> = ({ message, type, duration = 2000, onClose }) => {
  const uniqueId = useUniqueId('toast')
  const [isVisible, setIsVisible] = useState(false)
  const [isClosing, setIsClosing] = useState(false)

  // Efecto para mostrar el toast con fade in
  useEffect(() => {
    const showTimer = setTimeout(() => {
      setIsVisible(true)
    }, 10) // Pequeño delay para asegurar que el DOM esté listo

    return () => clearTimeout(showTimer)
  }, [])

  // Efecto para el timer de cierre automático
  useEffect(() => {
    if (!isVisible) return

    const timer = setTimeout(() => {
      handleClose()
    }, duration)

    return () => {
      clearTimeout(timer)
    }
  }, [duration, isVisible])

  // Función para manejar el cierre con animación
  const handleClose = () => {
    if (isClosing) return
    setIsClosing(true)

    // Esperar a que termine la animación de fade out antes de llamar onClose
    setTimeout(() => {
      onClose()
    }, 300) // Duración de la animación CSS
  }

  const getToastStyles = () => {
    switch (type) {
      case 'success':
        return {
          backgroundColor: 'rgba(0, 193, 67, 0.15)',
          borderColor: 'rgba(0, 193, 67, 0.3)',
          color: 'var(--binance-green)'
        }
      case 'error':
        return {
          backgroundColor: 'rgba(234, 57, 67, 0.15)',
          borderColor: 'rgba(234, 57, 67, 0.3)',
          color: 'var(--binance-red)'
        }
      case 'info':
        return {
          backgroundColor: 'rgba(255, 193, 7, 0.15)',
          borderColor: 'rgba(255, 193, 7, 0.3)',
          color: 'var(--binance-yellow)'
        }
      default:
        return {
          backgroundColor: 'rgba(132, 142, 156, 0.15)',
          borderColor: 'rgba(132, 142, 156, 0.3)',
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
    <div
      className={`toast ${isVisible ? 'toast-visible' : 'toast-hidden'} ${
        isClosing ? 'toast-closing' : ''
      }`}
      style={getToastStyles()}>
      <div className="toast-content">
        <span className="toast-icon">{getIcon()}</span>
        <span className="toast-message">{message}</span>
        <button id={`${uniqueId}-close`} className="toast-close" onClick={handleClose}>
          ×
        </button>
      </div>
    </div>
  )
}

export default Toast
