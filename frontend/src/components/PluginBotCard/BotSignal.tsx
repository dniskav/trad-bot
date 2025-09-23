import React from 'react'

interface BotSignalProps {
  signal: {
    signal_type: 'BUY' | 'SELL' | 'HOLD' | string
    reasoning?: string
    confidence?: number
  }
}

const BotSignal: React.FC<BotSignalProps> = ({ signal }) => {
  if (!signal) return null

  const rawType = String(signal.signal_type || '').toUpperCase()
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
      {signal.reasoning && <div className="signal-reasoning">{signal.reasoning}</div>}
      <div className="signal-confidence">
        Confianza: {Number((signal.confidence || 0) * 100).toFixed(1)}%
      </div>
    </div>
  )
}

export default BotSignal
