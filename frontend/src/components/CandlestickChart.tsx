import type { CandlestickData } from 'lightweight-charts'
import { CandlestickSeries, ColorType, createChart } from 'lightweight-charts'
import React, { useEffect, useRef, useState } from 'react'
import { useWebSocketContext } from '../contexts/WebSocketContext'

interface CandlestickChartProps {
  symbol?: string
  interval?: string
}

// Ultra-simple test data to avoid assertion errors
const generateSimpleData = (): CandlestickData[] => {
  const data: CandlestickData[] = []
  const baseTime = Math.floor(Date.now() / 1000)

  for (let i = 0; i < 20; i++) {
    const time = baseTime - (20 - i) * 60 // 1 minute intervals
    const basePrice = 50000 + i * 10 // Simple ascending trend

    data.push({
      time: time as any, // Type assertion for compatibility
      open: basePrice,
      high: basePrice + 50,
      low: basePrice - 50,
      close: basePrice + (Math.random() - 0.5) * 100
    })
  }

  return data
}

const CandlestickChart: React.FC<CandlestickChartProps> = ({
  symbol = 'BTCUSDT',
  interval = '1m'
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<any>(null)
  const seriesRef = useRef<any>(null)
  const [candleData, setCandleData] = useState<CandlestickData[]>([])
  const { lastMessage } = useWebSocketContext()

  // Process WebSocket messages for candle data
  useEffect(() => {
    console.log('WebSocket message received:', lastMessage)
    if (lastMessage) {
      try {
        // Check if lastMessage is already an object or a string
        let message
        if (typeof lastMessage === 'string') {
          message = JSON.parse(lastMessage)
        } else {
          message = lastMessage
        }

        console.log('Parsed message:', message)
        console.log('Message type:', message.type)
        console.log('Message data:', message.data)
        console.log('Data type:', typeof message.data)
        console.log('Is data array?', Array.isArray(message.data))

        if (message.type === 'candles' && message.data) {
          console.log('Received candle data:', message.data)

          // Check if data has candles array
          const candlesArray = message.data.candles || message.data

          if (Array.isArray(candlesArray)) {
            // Convert server data to chart format
            const formattedData: CandlestickData[] = candlesArray.map((candle: any) => ({
              time: candle.time as any,
              open: candle.open,
              high: candle.high,
              low: candle.low,
              close: candle.close
            }))

            console.log('Formatted data:', formattedData)
            setCandleData(formattedData)
          } else {
            console.log('Data is not an array, cannot map:', candlesArray)
          }
        } else {
          console.log('Message type not candles or no data:', message.type, message.data)
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }
  }, [lastMessage])

  useEffect(() => {
    if (!chartContainerRef.current) return

    console.log('Creating ultra-simple chart...')

    try {
      // Get container width for responsive design
      const containerWidth = chartContainerRef.current.clientWidth

      // Create chart with ABSOLUTE minimal options
      const chart = createChart(chartContainerRef.current, {
        width: containerWidth,
        height: 300,
        layout: {
          background: { type: ColorType.Solid, color: '#1e1e1e' },
          textColor: '#d1d4dc'
        }
      })

      console.log('Chart created, adding candlestick series...')

      // Use the CORRECT v5 API method
      const series = chart.addSeries(CandlestickSeries, {
        upColor: '#26a69a',
        downColor: '#ef5350'
      })

      console.log('Series added, generating data...')

      // Use real data if available, otherwise use mock data
      const data = candleData.length > 0 ? candleData : generateSimpleData()

      console.log('Data generated, setting data...')

      // Set data
      series.setData(data)

      // Store references
      chartRef.current = chart
      seriesRef.current = series

      console.log('Chart setup completed successfully')

      // Handle resize
      const handleResize = () => {
        if (chartContainerRef.current && chartRef.current) {
          const newWidth = chartContainerRef.current.clientWidth
          chartRef.current.applyOptions({ width: newWidth })
        }
      }

      window.addEventListener('resize', handleResize)

      // Cleanup
      return () => {
        window.removeEventListener('resize', handleResize)
        if (chartRef.current) {
          chartRef.current.remove()
          chartRef.current = null
        }
      }
    } catch (error) {
      console.error('Error creating chart:', error)
    }
  }, [])

  // Update chart when new data arrives
  useEffect(() => {
    if (seriesRef.current && candleData.length > 0) {
      console.log('Updating chart with new data:', candleData.length, 'candles')
      seriesRef.current.setData(candleData)
    }
  }, [candleData])

  return (
    <div className="candlestick-chart">
      <div className="chart-header">
        <h3>
          {symbol} - {interval}
        </h3>
        <div className="chart-info">
          <span>{candleData.length > 0 ? 'Real Data' : 'Test Data'}</span>
          <span>•</span>
          <span>{candleData.length > 0 ? `${candleData.length} candles` : '20 candles'}</span>
        </div>
      </div>
      <div ref={chartContainerRef} className="chart-canvas-container" />
      <div className="chart-footer">
        <small>Lightweight Charts - {candleData.length > 0 ? 'Real-time Data' : 'Test Data'}</small>
      </div>
    </div>
  )
}

export default CandlestickChart
