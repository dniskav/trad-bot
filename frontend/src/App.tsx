import { useState } from 'react'
import './App.css'
import AppContent from './components/AppContent'
import AppSetup from './components/AppSetup'
import { WebSocketProvider } from './contexts/WebSocketContext'

function App() {
  const [timeframe, setTimeframe] = useState('1m')

  const handleTimeframeChange = (newTimeframe: string) => {
    setTimeframe(newTimeframe)
  }

  return (
    <WebSocketProvider>
      <AppSetup>
        <AppContent timeframe={timeframe} onTimeframeChange={handleTimeframeChange} />
      </AppSetup>
    </WebSocketProvider>
  )
}

export default App
