import React, { useCallback, useState } from 'react'
import { useApiKlines } from '../hooks/useApiKlines'
import CandlestickChart from './CandlestickChart'

interface ChartWrapperProps {
  symbol?: string
  live?: boolean
  binanceSymbol?: string
  binanceInterval?: string
}

const ChartWrapper: React.FC<ChartWrapperProps> = ({
  symbol = 'DOGEUSDT',
  live = true,
  binanceSymbol = 'DOGEUSDT',
  binanceInterval
}) => {
  // Estado para el timeframe con inicialización desde localStorage
  const [timeframe, setTimeframe] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('candlestick-timeframe') || '1m'
    }
    return '1m'
  })

  // Hook para obtener datos históricos de Binance
  const { candlesData, isLoading, error } = useApiKlines(symbol, timeframe, 1000)

  // Estado para forzar re-montado del chart
  const [chartRemountKey, setChartRemountKey] = useState(0)

  // Función para manejar cambios de timeframe con localStorage
  const handleTimeframeChange = useCallback((newTimeframe: string) => {
    setTimeframe(newTimeframe)
    // Guardar en localStorage
    if (typeof window !== 'undefined') {
      localStorage.setItem('candlestick-timeframe', newTimeframe)
    }
    // Forzar re-montado cuando cambia el timeframe
    setChartRemountKey((prev) => prev + 1)
  }, [])

  // Mostrar loading mientras se cargan los datos históricos
  if (isLoading && candlesData.length === 0) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <p>Cargando datos históricos...</p>
      </div>
    )
  }

  // Mostrar error si hay problemas cargando los datos
  if (error && candlesData.length === 0) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: 'red' }}>
        <p>Error al cargar datos históricos: {error}</p>
      </div>
    )
  }

  return (
    <CandlestickChart
      key={chartRemountKey}
      symbol={symbol}
      timeframe={timeframe}
      signals={undefined}
      candlesData={candlesData}
      indicatorsData={null}
      onTimeframeChange={handleTimeframeChange}
      live={live}
      binanceSymbol={binanceSymbol}
      binanceInterval={binanceInterval || timeframe}
    />
  )
}

export default ChartWrapper
