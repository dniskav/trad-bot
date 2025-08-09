import { ColorType, createChart } from 'lightweight-charts'
import React, { useEffect, useRef } from 'react'

interface CandlestickChartProps {
  symbol?: string
  interval?: string
}

// Simple test data
const testData = [
  { time: 1640995200, open: 100, high: 105, low: 95, close: 102 },
  { time: 1640995260, open: 102, high: 108, low: 100, close: 106 },
  { time: 1640995320, open: 106, high: 110, low: 104, close: 108 },
  { time: 1640995380, open: 108, high: 112, low: 106, close: 110 },
  { time: 1640995440, open: 110, high: 115, low: 108, close: 113 },
  { time: 1640995500, open: 113, high: 118, low: 111, close: 116 },
  { time: 1640995560, open: 116, high: 120, low: 114, close: 118 },
  { time: 1640995620, open: 118, high: 122, low: 116, close: 120 },
  { time: 1640995680, open: 120, high: 125, low: 118, close: 123 },
  { time: 1640995740, open: 123, high: 128, low: 121, close: 126 }
]

const CandlestickChart: React.FC<CandlestickChartProps> = ({
  symbol = 'BTCUSDT',
  interval = '1m'
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<any>(null)

  useEffect(() => {
    if (!chartContainerRef.current) return

    console.log('Creating simple test chart...')

    try {
      // Get container width for responsive design
      const containerWidth = chartContainerRef.current.clientWidth

      // Create simple chart
      const chart = createChart(chartContainerRef.current, {
        width: containerWidth,
        height: 300,
        layout: {
          background: { type: ColorType.Solid, color: '#1e1e1e' },
          textColor: '#d1d4dc'
        }
      })

      console.log('Chart created, adding series...')

      // Add candlestick series
      const candlestickSeries = (chart as any).addSeries('Candlestick', {
        upColor: '#26a69a',
        downColor: '#ef5350'
      })

      console.log('Series added, setting data...')

      // Set test data
      candlestickSeries.setData(testData)

      console.log('Test data set, chart should be visible')

      // Store chart reference
      chartRef.current = chart

      // Handle resize
      const handleResize = () => {
        if (chartContainerRef.current && chartRef.current) {
          const newWidth = chartContainerRef.current.clientWidth
          chartRef.current.applyOptions({ width: newWidth })
        }
      }

      window.addEventListener('resize', handleResize)

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

  return (
    <div className="candlestick-chart">
      <div className="chart-header">
        <h3>
          {symbol} - {interval}
        </h3>
        <div className="chart-info">
          <span>Test Data</span>
          <span>•</span>
          <span>{testData.length} candles</span>
        </div>
      </div>
      <div ref={chartContainerRef} className="chart-canvas-container" />
      <div className="chart-footer">
        <small>Lightweight Charts - Test Data</small>
      </div>
    </div>
  )
}

export default CandlestickChart
