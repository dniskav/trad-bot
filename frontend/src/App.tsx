import './App.css'
import AppContent from './components/AppContent'
import { AppSetup } from './components/AppSetup'
import './components/WebSocketStatus/utils/wsInterceptor'

function App() {
  return (
    <AppSetup>
      <AppContent />
    </AppSetup>
  )
}

export default App
