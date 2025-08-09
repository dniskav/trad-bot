import React, { useEffect, useRef, useState } from 'react'
import { createChart, ColorType, type Time, type SeriesType } from 'lightweight-charts'

interface CandlestickChartProps {
  symbol?: string
  interval?: string
}

// Dummy data following the official documentation format
const dummyData = [
  { time: 1640995200 as Time, open: 46200, high: 46800, low: 46000, close: 46500 },
  { time: 1640995260 as Time, open: 46500, high: 47000, low: 46300, close: 46800 },
  { time: 1640995320 as Time, open: 46800, high: 47200, low: 46600, close: 47000 },
  { time: 1640995380 as Time, open: 47000, high: 47500, low: 46800, close: 47300 },
  { time: 1640995440 as Time, open: 47300, high: 47800, low: 47100, close: 47600 },
  { time: 1640995500 as Time, open: 47600, high: 48000, low: 47400, close: 47800 },
  { time: 1640995560 as Time, open: 47800, high: 48200, low: 47600, close: 48000 },
  { time: 1640995620 as Time, open: 48000, high: 48500, low: 47800, close: 48300 },
  { time: 1640995680 as Time, open: 48300, high: 48700, low: 48100, close: 48500 },
  { time: 1640995740 as Time, open: 48500, high: 49000, low: 48300, close: 48800 },
  { time: 1640995800 as Time, open: 48800, high: 49200, low: 48600, close: 49000 },
  { time: 1640995860 as Time, open: 49000, high: 49500, low: 48800, close: 49300 },
  { time: 1640995920 as Time, open: 49300, high: 49700, low: 49100, close: 49500 },
  { time: 1640995980 as Time, open: 49500, high: 50000, low: 49300, close: 49800 },
  { time: 1640996040 as Time, open: 49800, high: 50200, low: 49600, close: 50000 },
  { time: 1640996100 as Time, open: 50000, high: 50500, low: 49800, close: 50300 },
  { time: 1640996160 as Time, open: 50300, high: 50700, low: 50100, close: 50500 },
  { time: 1640996220 as Time, open: 50500, high: 51000, low: 50300, close: 50800 },
  { time: 1640996280 as Time, open: 50800, high: 51200, low: 50600, close: 51000 },
  { time: 1640996340 as Time, open: 51000, high: 51500, low: 50800, close: 51300 },
  { time: 1640996400 as Time, open: 51300, high: 51700, low: 51100, close: 51500 },
  { time: 1640996460 as Time, open: 51500, high: 52000, low: 51300, close: 51800 },
  { time: 1640996520 as Time, open: 51800, high: 52200, low: 51600, close: 52000 },
  { time: 1640996580 as Time, open: 52000, high: 52500, low: 51800, close: 52300 },
  { time: 1640996640 as Time, open: 52300, high: 52700, low: 52100, close: 52500 },
  { time: 1640996700 as Time, open: 52500, high: 53000, low: 52300, close: 52800 },
  { time: 1640996760 as Time, open: 52800, high: 53200, low: 52600, close: 53000 },
  { time: 1640996820 as Time, open: 53000, high: 53500, low: 52800, close: 53300 },
  { time: 1640996880 as Time, open: 53300, high: 53700, low: 53100, close: 53500 },
  { time: 1640996940 as Time, open: 53500, high: 54000, low: 53300, close: 53800 },
  { time: 1640997000 as Time, open: 53800, high: 54200, low: 53600, close: 54000 },
  { time: 1640997060 as Time, open: 54000, high: 54500, low: 53800, close: 54300 },
  { time: 1640997120 as Time, open: 54300, high: 54700, low: 54100, close: 54500 },
  { time: 1640997180 as Time, open: 54500, high: 55000, low: 54300, close: 54800 },
  { time: 1640997240 as Time, open: 54800, high: 55200, low: 54600, close: 55000 },
  { time: 1640997300 as Time, open: 55000, high: 55500, low: 54800, close: 55300 },
  { time: 1640997360 as Time, open: 55300, high: 55700, low: 55100, close: 55500 },
  { time: 1640997420 as Time, open: 55500, high: 56000, low: 55300, close: 55800 },
  { time: 1640997480 as Time, open: 55800, high: 56200, low: 55600, close: 56000 },
  { time: 1640997540 as Time, open: 56000, high: 56500, low: 55800, close: 56300 },
  { time: 1640997600 as Time, open: 56300, high: 56700, low: 56100, close: 56500 },
  { time: 1640997660 as Time, open: 56500, high: 57000, low: 56300, close: 56800 },
  { time: 1640997720 as Time, open: 56800, high: 57200, low: 56600, close: 57000 },
  { time: 1640997780 as Time, open: 57000, high: 57500, low: 56800, close: 57300 },
  { time: 1640997840 as Time, open: 57300, high: 57700, low: 57100, close: 57500 },
  { time: 1640997900 as Time, open: 57500, high: 58000, low: 57300, close: 57800 },
  { time: 1640997960 as Time, open: 57800, high: 58200, low: 57600, close: 58000 },
  { time: 1640998020 as Time, open: 58000, high: 58500, low: 57800, close: 58300 },
  { time: 1640998080 as Time, open: 58300, high: 58700, low: 58100, close: 58500 },
  { time: 1640998140 as Time, open: 58500, high: 59000, low: 58300, close: 58800 },
  { time: 1640998200 as Time, open: 58800, high: 59200, low: 58600, close: 59000 },
  { time: 1640998260 as Time, open: 59000, high: 59500, low: 58800, close: 59300 },
  { time: 1640998320 as Time, open: 59300, high: 59700, low: 59100, close: 59500 },
  { time: 1640998380 as Time, open: 59500, high: 60000, low: 59300, close: 59800 },
  { time: 1640998440 as Time, open: 59800, high: 60200, low: 59600, close: 60000 },
  { time: 1640998500 as Time, open: 60000, high: 60500, low: 59800, close: 60300 },
  { time: 1640998560 as Time, open: 60300, high: 60700, low: 60100, close: 60500 },
  { time: 1640998620 as Time, open: 60500, high: 61000, low: 60300, close: 60800 },
  { time: 1640998680 as Time, open: 60800, high: 61200, low: 60600, close: 61000 },
  { time: 1640998740 as Time, open: 61000, high: 61500, low: 60800, close: 61300 },
  { time: 1640998800 as Time, open: 61300, high: 61700, low: 61100, close: 61500 },
  { time: 1640998860 as Time, open: 61500, high: 62000, low: 61300, close: 61800 },
  { time: 1640998920 as Time, open: 61800, high: 62200, low: 61600, close: 62000 },
  { time: 1640998980 as Time, open: 62000, high: 62500, low: 61800, close: 62300 },
  { time: 1640999040 as Time, open: 62300, high: 62700, low: 62100, close: 62500 },
  { time: 1640999100 as Time, open: 62500, high: 63000, low: 62300, close: 62800 },
  { time: 1640999160 as Time, open: 62800, high: 63200, low: 62600, close: 63000 },
  { time: 1640999220 as Time, open: 63000, high: 63500, low: 62800, close: 63300 },
  { time: 1640999280 as Time, open: 63300, high: 63700, low: 63100, close: 63500 },
  { time: 1640999340 as Time, open: 63500, high: 64000, low: 63300, close: 63800 },
  { time: 1640999400 as Time, open: 63800, high: 64200, low: 63600, close: 64000 },
  { time: 1640999460 as Time, open: 64000, high: 64500, low: 63800, close: 64300 },
  { time: 1640999520 as Time, open: 64300, high: 64700, low: 64100, close: 64500 },
  { time: 1640999580 as Time, open: 64500, high: 65000, low: 64300, close: 64800 },
  { time: 1640999640 as Time, open: 64800, high: 65200, low: 64600, close: 65000 },
  { time: 1640999700 as Time, open: 65000, high: 65500, low: 64800, close: 65300 },
  { time: 1640999760 as Time, open: 65300, high: 65700, low: 65100, close: 65500 },
  { time: 1640999820 as Time, open: 65500, high: 66000, low: 65300, close: 65800 },
  { time: 1640999880 as Time, open: 65800, high: 66200, low: 65600, close: 66000 },
  { time: 1640999940 as Time, open: 66000, high: 66500, low: 65800, close: 66300 },
  { time: 1641000000 as Time, open: 66300, high: 66700, low: 66100, close: 66500 }
]

const CandlestickChart: React.FC<CandlestickChartProps> = ({
  symbol = 'BTCUSDT',
  interval = '1m'
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<any>(null)
  const seriesRef = useRef<any>(null)

  useEffect(() => {
    if (!chartContainerRef.current) return

    console.log('Creating chart with dummy data...')

    // Create chart following official documentation
    const chart = createChart(chartContainerRef.current, {
      width: 600,
      height: 400,
      layout: {
        background: { type: ColorType.Solid, color: '#1e1e1e' },
        textColor: '#d1d4dc'
      },
      grid: {
        vertLines: { color: '#2B2B43' },
        horzLines: { color: '#2B2B43' }
      },
      crosshair: {
        mode: 1
      },
      rightPriceScale: {
        borderColor: '#2B2B43'
      },
      timeScale: {
        borderColor: '#2B2B43',
        timeVisible: true,
        secondsVisible: false
      }
    })

    console.log('Chart created:', chart)

    // Add candlestick series following official documentation
    const candlestickSeries = (chart as any).addSeries('Candlestick', {
      upColor: '#26a69a',
      downColor: '#ef5350'
    })

    console.log('Candlestick series created:', candlestickSeries)

    // Set data
    candlestickSeries.setData(dummyData)
    console.log('Data set:', dummyData.length, 'candles')

    // Store references
    chartRef.current = chart
    seriesRef.current = candlestickSeries

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth
        })
      }
    }

    window.addEventListener('resize', handleResize)

    // Cleanup
    return () => {
      console.log('Cleaning up chart...')
      window.removeEventListener('resize', handleResize)
      if (chartRef.current) {
        chartRef.current.remove()
        chartRef.current = null
      }
      seriesRef.current = null
    }
  }, [])

  return (
    <div
      style={{
        backgroundColor: '#1e1e1e',
        borderRadius: '8px',
        padding: '16px',
        margin: '16px 0'
      }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px',
          color: '#d1d4dc'
        }}>
        <h3 style={{ margin: 0 }}>
          {symbol} - {interval} (Dummy Data)
        </h3>
        <div style={{ fontSize: '14px' }}>Last: $66,500.00</div>
      </div>
      <div
        ref={chartContainerRef}
        style={{
          height: '400px',
          border: '1px solid #333',
          backgroundColor: '#1e1e1e'
        }}
      />
      <div style={{ fontSize: '12px', color: '#888', marginTop: '8px' }}>
        Data points: {dummyData.length} | Chart ready: {!!seriesRef.current ? 'Yes' : 'No'}
      </div>
    </div>
  )
}

export default CandlestickChart
