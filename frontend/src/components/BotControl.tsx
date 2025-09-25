import React, { useState } from 'react'
import { useUniqueId } from '../../hooks/useUniqueId'

interface BotControlProps {
  botType: 'conservative' | 'aggressive'
  isActive: boolean
  onToggle: (botType: string, newStatus: boolean) => void
}

const BotControl: React.FC<BotControlProps> = ({ botType, isActive, onToggle }) => {
  const uniqueId = useUniqueId(`bot-${botType}`)
  const [loading, setLoading] = useState(false)

  const handleToggle = async () => {
    setLoading(true)
    try {
      const action = isActive ? 'stop' : 'start'
      const response = await fetch(`/api/bot-control/${botType}/${action}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const result = await response.json()

      if (result.success) {
        onToggle(botType, !isActive)
        console.log(`✅ ${result.message}`)
      } else {
        console.error('❌ Error:', result.error)
        alert(`Error: ${result.error}`)
      }
    } catch (error) {
      console.error('❌ Error toggling bot:', error)
      alert(`Error de conexión: ${error}`)
    } finally {
      setLoading(false)
    }
  }

  const getBotIcon = () => {
    return botType === 'conservative' ? '🐌' : '⚡'
  }

  const getBotName = () => {
    return botType === 'conservative' ? 'Conservador' : 'Agresivo'
  }

  const getButtonText = () => {
    if (loading) return '...'
    return isActive ? 'Desactivar' : 'Activar'
  }

  const getButtonClass = () => {
    const baseClass = 'bot-control-button'
    if (loading) return `${baseClass} loading`
    return isActive ? `${baseClass} active` : `${baseClass} inactive`
  }

  return (
    <div className="bot-control">
      <div className="bot-info">
        <span className="bot-icon">{getBotIcon()}</span>
        <span className="bot-name">{getBotName()}</span>
      </div>
      <button
        id={`${uniqueId}-toggle`}
        className={getButtonClass()}
        onClick={handleToggle}
        disabled={loading}>
        {getButtonText()}
      </button>
    </div>
  )
}

export default BotControl
