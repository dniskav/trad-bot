import React from 'react'
import { Dashboard } from './components/Dashboard'
import { TradeLog } from './components/TradeLog'
import './App.css'

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>SMA Cross Trading Bot</h1>
        <p>Real-time trading dashboard and analytics</p>
      </header>

      <main className="App-main">
        <Dashboard />
        <TradeLog />
      </main>

      <footer className="App-footer">
        <p>&copy; 2025 Trading Bot Dashboard - Educational Purposes Only</p>
      </footer>
    </div>
  )
}

export default App
