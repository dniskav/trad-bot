import React from 'react'

interface BotSignalProps {
  signal: {
    // back compatible: sometimes comes as action
    signal_type?: 'BUY' | 'SELL' | 'HOLD' | string
    action?: 'BUY' | 'SELL' | 'HOLD' | string
    reasoning?: string
    confidence?: number
    metadata?: {
      conditions_met?: number
      total_conditions?: number
      [key: string]: any
    }
  }
}

const BotSignal: React.FC<BotSignalProps> = ({ signal }) => {
  if (!signal) return null

  const rawType = String(signal.signal_type || signal.action || 'HOLD').toUpperCase()
  const type = rawType.includes('.') ? rawType.split('.').pop()! : rawType

  const color = type === 'BUY' ? '#26a69a' : type === 'SELL' ? '#ef5350' : '#ffa726'

  return (
    <div className="bot-signal">
      <div className="signal-header">
        <span className="signal-label">Última Señal:</span>
        <span className="signal-value" style={{ color }}>
          {type}
        </span>
      </div>
      <div className="signal-reasoning">
        {signal.reasoning ||
          (type === 'HOLD' ? 'No se cumplen las condiciones de entrada de la estrategia' : '')}
      </div>
      <div className="signal-confidence">
        Confianza: {Number((signal.confidence || 0) * 100).toFixed(1)}%
        {signal.metadata?.total_conditions !== undefined && (
          <span>
            {`  (Condiciones: ${signal.metadata?.conditions_met ?? 0}/${
              signal.metadata?.total_conditions
            })`}
          </span>
        )}
      </div>
    </div>
  )
}

export default BotSignal
