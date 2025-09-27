import './App.css'
import AppContent from './components/AppContent'
import { AppSetup } from './components/AppSetup'
import WebSocketManager from './components/WebSocketManager'
import { WebSocketConnectionProvider } from './contexts/WebSocketConnectionContext'
import { WebSocketProvider } from './contexts/WebSocketContext'

function App() {
  return (
    <WebSocketConnectionProvider>
      <WebSocketProvider>
        <WebSocketManager />
        <AppSetup>
          <AppContent />
        </AppSetup>
      </WebSocketProvider>
    </WebSocketConnectionProvider>
  )
}

export default App
