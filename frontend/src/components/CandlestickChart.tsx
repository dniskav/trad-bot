import type { CandlestickData } from 'lightweight-charts'
import { CandlestickSeries, ColorType, createChart } from 'lightweight-charts'
import React, { useEffect, useRef, useState } from 'react'
import { useWebSocketContext } from '../contexts/WebSocketContext'

interface TradingSignal {
  time: number
  type: 'BUY' | 'SELL' | 'HOLD'
  bot: 'conservative' | 'aggressive'
  price: number
  reason?: string
  confidence?: number
}

interface CandlestickChartProps {
  symbol?: string
  interval?: string
  timeframe?: string
  signals?: TradingSignal[]
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
  timeframe = '1m',
  signals = []
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
              time: (candle.time / 1000) as any, // Convert milliseconds to seconds
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

      // Create chart with proper time formatting
      const chart = createChart(chartContainerRef.current, {
        width: containerWidth,
        height: 300,
        layout: {
          background: { type: ColorType.Solid, color: '#1e1e1e' },
          textColor: '#d1d4dc'
        },
        timeScale: {
          timeVisible: true,
          secondsVisible: false,
          borderColor: '#485c7b',
          borderVisible: true,
          tickMarkFormatter: (time: any) => {
            const date = new Date(time * 1000) // Convert seconds to milliseconds

            // Format based on timeframe
            if (timeframe === '1m' || timeframe === '3m' || timeframe === '5m') {
              return date.toLocaleTimeString('es-ES', {
                hour: '2-digit',
                minute: '2-digit'
              })
            } else if (timeframe === '15m' || timeframe === '30m') {
              return date.toLocaleTimeString('es-ES', {
                hour: '2-digit',
                minute: '2-digit'
              })
            } else if (
              timeframe === '1h' ||
              timeframe === '2h' ||
              timeframe === '4h' ||
              timeframe === '6h' ||
              timeframe === '8h' ||
              timeframe === '12h'
            ) {
              return date.toLocaleDateString('es-ES', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit'
              })
            } else if (timeframe === '1d' || timeframe === '3d') {
              return date.toLocaleDateString('es-ES', {
                month: 'short',
                day: 'numeric'
              })
            } else if (timeframe === '1w') {
              return date.toLocaleDateString('es-ES', {
                month: 'short',
                day: 'numeric'
              })
            } else if (timeframe === '1M') {
              return date.toLocaleDateString('es-ES', {
                year: 'numeric',
                month: 'short'
              })
            }

            return date.toLocaleString('es-ES')
          }
        },
        rightPriceScale: {
          borderColor: '#485c7b',
          borderVisible: true,
          scaleMargins: {
            top: 0.1,
            bottom: 0.1
          }
        },
        grid: {
          horzLines: {
            color: '#2a2e39',
            style: 1,
            visible: true
          },
          vertLines: {
            color: '#2a2e39',
            style: 1,
            visible: true
          }
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

      // Add signal markers
      if (signals.length > 0) {
        console.log('Adding signal markers:', signals)
        const markers = signals.map((signal) => ({
          time: signal.time as any,
          position: signal.type === 'BUY' ? 'belowBar' : 'aboveBar',
          color: signal.type === 'BUY' ? '#26a69a' : '#ef5350',
          shape: signal.type === 'BUY' ? 'arrowUp' : 'arrowDown',
          text: `${signal.bot.toUpperCase()} ${signal.type}`,
          size: 1.5,
          id: `${signal.bot}-${signal.type}-${signal.time}`,
          title: `${signal.bot.toUpperCase()} ${signal.type} Signal`,
          description: signal.reason || `${signal.type} signal from ${signal.bot} bot`
        }))

        // TODO: Implement markers when Lightweight Charts API is clarified
        console.log('Markers to be added:', markers)
        // try {
        //   // Add markers one by one
        //   markers.forEach(marker => {
        //     series.setMarkers([marker])
        //   })
        // } catch (error) {
        //   console.error('Error adding markers:', error)
        // }
      }

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
  }, [timeframe])

  // Update chart when new data arrives
  useEffect(() => {
    if (seriesRef.current && candleData.length > 0) {
      console.log('Updating chart with new data:', candleData.length, 'candles')
      seriesRef.current.setData(candleData)
    }
  }, [candleData])

  // Update signals when they change
  useEffect(() => {
    if (seriesRef.current && signals.length > 0) {
      console.log('Updating chart with new signals:', signals.length, 'signals')

      const markers = signals.map((signal) => ({
        time: signal.time as any,
        position: signal.type === 'BUY' ? 'belowBar' : 'aboveBar',
        color: signal.type === 'BUY' ? '#26a69a' : '#ef5350',
        shape: signal.type === 'BUY' ? 'arrowUp' : 'arrowDown',
        text: `${signal.bot.toUpperCase()} ${signal.type}`,
        size: 1.5,
        id: `${signal.bot}-${signal.type}-${signal.time}`,
        // Add more detailed information
        title: `${signal.bot.toUpperCase()} ${signal.type} Signal`,
        description: signal.reason || `${signal.type} signal from ${signal.bot} bot`
      }))

      // TODO: Implement markers when Lightweight Charts API is clarified
      console.log('Markers to be updated:', markers)
      // try {
      //   // Clear existing markers first
      //   seriesRef.current.setMarkers([])
      //   // Add markers one by one
      //   markers.forEach(marker => {
      //     seriesRef.current.setMarkers([marker])
      //   })
      // } catch (error) {
      //   console.error('Error updating markers:', error)
      // }
    }
  }, [signals])

  return (
    <div className="candlestick-chart">
      <div className="chart-header">
        <h3>
          {symbol} - {timeframe}
        </h3>
        <div className="chart-info">
          <span>{candleData.length > 0 ? 'Real Data' : 'Test Data'}</span>
          <span>•</span>
          <span>{candleData.length > 0 ? `${candleData.length} candles` : '20 candles'}</span>
          {signals.length > 0 && (
            <>
              <span>•</span>
              <span>{signals.length} signals</span>
            </>
          )}
        </div>
        {signals.length > 0 && (
          <div className="chart-legend">
            <div className="legend-item">
              <div className="legend-marker buy"></div>
              <span>BUY Signal</span>
            </div>
            <div className="legend-item">
              <div className="legend-marker sell"></div>
              <span>SELL Signal</span>
            </div>
          </div>
        )}
      </div>
      <div className="chart-container">
        <div ref={chartContainerRef} className="chart-canvas-container" />
        {/* Signal Overlay */}
        {signals.length > 0 && (
          <div className="signal-overlay">
            {signals.map((signal, index) => (
              <div
                key={`${signal.bot}-${signal.type}-${signal.time}-${index}`}
                className={`signal-marker ${signal.type.toLowerCase()} ${signal.bot}`}
                title={`${signal.bot.toUpperCase()} ${signal.type} - ${
                  signal.reason || 'Trading Signal'
                }`}>
                <div className="signal-icon">{signal.type === 'BUY' ? '▲' : '▼'}</div>
                <div className="signal-label">{signal.bot === 'conservative' ? 'C' : 'A'}</div>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="chart-footer">
        <small>Lightweight Charts - {candleData.length > 0 ? 'Real-time Data' : 'Test Data'}</small>
        {signals.length > 0 && (
          <div className="signal-info">
            <small>💡 Hover over signals for details</small>
          </div>
        )}
      </div>
    </div>
  )
}

export default CandlestickChart
