import React from 'react'

interface TimeframeSelectorProps {
  selectedTimeframe: string
  onTimeframeChange: (timeframe: string) => void
}

const TIMEFRAMES = [
  // Minutos (intervalo mínimo de Binance)
  { value: '1m', label: '1m', category: 'Minutos' },
  { value: '3m', label: '3m', category: 'Minutos' },
  { value: '5m', label: '5m', category: 'Minutos' },
  { value: '15m', label: '15m', category: 'Minutos' },
  { value: '30m', label: '30m', category: 'Minutos' },

  // Horas
  { value: '1h', label: '1h', category: 'Horas' },
  { value: '2h', label: '2h', category: 'Horas' },
  { value: '4h', label: '4h', category: 'Horas' },
  { value: '6h', label: '6h', category: 'Horas' },
  { value: '8h', label: '8h', category: 'Horas' },
  { value: '12h', label: '12h', category: 'Horas' },

  // Días
  { value: '1d', label: '1d', category: 'Días' },
  { value: '3d', label: '3d', category: 'Días' },

  // Semanas y Meses
  { value: '1w', label: '1w', category: 'Semanas' },
  { value: '1M', label: '1M', category: 'Meses' }
]

const TimeframeSelector: React.FC<TimeframeSelectorProps> = ({
  selectedTimeframe,
  onTimeframeChange
}) => {
  return (
    <div className="timeframe-selector">
      <div className="timeframe-header">
        <h4>Timeframe</h4>
      </div>
      <div className="timeframe-buttons">
        {TIMEFRAMES.map((timeframe) => (
          <button
            key={timeframe.value}
            className={`timeframe-btn ${selectedTimeframe === timeframe.value ? 'active' : ''}`}
            onClick={() => onTimeframeChange(timeframe.value)}
            title={`${timeframe.label} - ${timeframe.category}${
              timeframe.value === '1m' ? ' (Mínimo)' : ''
            }`}>
            {timeframe.label}
          </button>
        ))}
      </div>
    </div>
  )
}

export default TimeframeSelector
