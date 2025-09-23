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

  const color =
    signal.signal_type === 'BUY' ? '#26a69a' : signal.signal_type === 'SELL' ? '#ef5350' : '#ffa726'

  return (
    <div className="bot-signal">
      <div className="signal-header">
        <span className="signal-label">Última Señal:</span>
        <span className="signal-value" style={{ color }}>
          {signal.signal_type}
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
