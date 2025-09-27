import { useState } from 'react'
import './App.css'
import AppContent from './components/AppContent'
import { AppSetup } from './components/AppSetup'
import WebSocketManager from './components/WebSocketManager'
import { WebSocketConnectionProvider } from './contexts/WebSocketConnectionContext'
import { WebSocketProvider } from './contexts/WebSocketContext'

function App() {
  const [timeframe, setTimeframe] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('candlestick-timeframe') || '1m'
    }
    return '1m'
  })

  const handleTimeframeChange = (newTimeframe: string) => {
    setTimeframe(newTimeframe)
  }

  return (
    <WebSocketConnectionProvider>
      <WebSocketProvider>
        <WebSocketManager />
        <AppSetup>
          <AppContent timeframe={timeframe} onTimeframeChange={handleTimeframeChange} />
        </AppSetup>
      </WebSocketProvider>
    </WebSocketConnectionProvider>
  )
}

export default App
