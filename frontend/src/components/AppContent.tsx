import React, { useCallback, useState } from 'react'
import { Accordion } from './Accordion'
import ActivePositions from './ActivePositions/ActivePositions'
import ChartWrapper from './ChartWrapper'
import ErrorBoundary from './ErrorBoundary'
import PlugAndPlayBots from './PlugAndPlayBots'
import { Toast } from './Toast'
import WebSocketStatus from './WebSocketStatus'

interface AppContentProps {
  timeframe: string
  onTimeframeChange: (timeframe: string) => void
}

const AppContent: React.FC<AppContentProps> = ({ timeframe, onTimeframeChange }) => {
  // Debug: Contador de montajes
  const mountCount = React.useRef(0)
  mountCount.current += 1
  console.log(`🚀 AppContent: Montaje #${mountCount.current}`)

  // Estados locales
  const [showToast, setShowToast] = useState(false)
  const [toastMessage, setToastMessage] = useState('')

  // Función estable para cerrar el toast
  const handleToastClose = useCallback(() => {
    setShowToast(false)
  }, [])

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <div className="header-left">
            <WebSocketStatus />
          </div>

          <div className="header-center">
            <h1 className="app-title">Trading Bot</h1>
          </div>

          <div className="header-right">
            <button
              className="status-button"
              onClick={() => {
                // Aquí podrías implementar la verificación de salud
                setToastMessage('Verificación de salud completada')
                setShowToast(true)
              }}>
              Status
            </button>
          </div>
        </div>
      </header>

      {/* Contenido principal */}
      <main className="app-main">
        <div className="health-container">
          {/* Saldo de Cuenta */}
          <Accordion title="Saldo de Cuenta" defaultExpanded={true} storageKey="account-balance">
            {/* <AccountBalance
              symbol="DOGEUSDT"
            /> */}
            Saldo de Cuenta
          </Accordion>

          {/* Posiciones Concurrentes Activas */}
          <Accordion
            title="Posiciones Concurrentes Activas"
            defaultExpanded={true}
            storageKey="active-positions">
            <ActivePositions />
          </Accordion>

          {/* Información de Margen */}
          <Accordion title="Información de Margen" defaultExpanded={false} storageKey="margin-info">
            {/* <MarginInfo marginInfo={marginInfo} /> */}
            Información de Margen
          </Accordion>

          {/* Gráfico de Velas */}
          <Accordion
            title="Gráfico de Velas"
            defaultExpanded={true}
            storageKey="candlestick-chart"
            onExpand={() => {
              // Forzar re-montado del chart cuando se expande
              // setChartRemountKey((prev) => prev + 1)
            }}
            onCollapse={() => {
              // Opcional: limpiar recursos cuando se colapsa
              console.log('Chart collapsed')
            }}>
            <ErrorBoundary>
              <ChartWrapper
                symbol="DOGEUSDT"
                timeframe={timeframe}
                onTimeframeChange={onTimeframeChange}
                live
                binanceSymbol="DOGEUSDT"
                binanceInterval={timeframe}
              />
            </ErrorBoundary>
          </Accordion>

          {/* Plugin Bots */}
          <Accordion title="Plugin Bots" defaultExpanded={true} storageKey="plugin-bots">
            <PlugAndPlayBots />
          </Accordion>

          {/* Historial de Posiciones */}
          <Accordion
            title="Historial de Posiciones"
            defaultExpanded={true}
            storageKey="position-history">
            {/* <PositionHistory history={positionHistory} statistics={historyStats} /> */}
            Historial de Posiciones
          </Accordion>
        </div>
      </main>

      {/* Toast para notificaciones */}
      {showToast && (
        <Toast message={toastMessage} type="info" duration={2000} onClose={handleToastClose} />
      )}
    </div>
  )
}

export default AppContent
