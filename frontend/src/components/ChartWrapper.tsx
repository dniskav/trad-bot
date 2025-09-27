import React, { useCallback, useState } from 'react'
import CandlestickChart from './CandlestickChart'

interface ChartWrapperProps {
  symbol?: string
  timeframe: string
  onTimeframeChange: (timeframe: string) => void
  live?: boolean
  binanceSymbol?: string
  binanceInterval?: string
}

const ChartWrapper: React.FC<ChartWrapperProps> = ({
  symbol = 'DOGEUSDT',
  timeframe,
  onTimeframeChange,
  live = true,
  binanceSymbol = 'DOGEUSDT',
  binanceInterval
}) => {
  // Estado para forzar re-montado del chart
  const [chartRemountKey, setChartRemountKey] = useState(0)

  // Función para manejar cambios de timeframe con localStorage
  const handleTimeframeChange = useCallback(
    (newTimeframe: string) => {
      onTimeframeChange(newTimeframe)
      // Guardar en localStorage
      if (typeof window !== 'undefined') {
        localStorage.setItem('candlestick-timeframe', newTimeframe)
      }
      // Forzar re-montado cuando cambia el timeframe
      setChartRemountKey((prev) => prev + 1)
    },
    [onTimeframeChange]
  )

  return (
    <CandlestickChart
      key={chartRemountKey}
      symbol={symbol}
      timeframe={timeframe}
      signals={undefined}
      candlesData={[]}
      indicatorsData={null}
      onTimeframeChange={handleTimeframeChange}
      live={live}
      binanceSymbol={binanceSymbol}
      binanceInterval={binanceInterval || timeframe}
    />
  )
}

export default ChartWrapper
