import React from 'react'

interface MarginInfoProps {
  marginInfo: {
    success: boolean
    margin_level: number
    leverage: number
    margin_type: string
    usdt_balance: number
    doge_balance: number
    doge_price: number
    total_available_usdt: number
    trading_power_usdt: number
    margin_ratio: number
    is_safe: boolean
  } | null
}

const MarginInfo: React.FC<MarginInfoProps> = ({ marginInfo }) => {
  if (!marginInfo || !marginInfo.success) {
    return (
      <div className="margin-info">
        <h3>📊 Información de Margen</h3>
        <div className="margin-error">
          <span className="error-text">❌ No disponible</span>
        </div>
      </div>
    )
  }

  const {
    margin_level,
    leverage,
    margin_type,
    usdt_balance,
    doge_balance,
    doge_price,
    total_available_usdt,
    trading_power_usdt,
    margin_ratio,
    is_safe
  } = marginInfo

  const marginLevelColor = is_safe ? '#00ff88' : '#ff4444'
  const marginLevelText = is_safe ? 'Seguro' : 'Riesgo'

  return (
    <div className="margin-info">
      <div className="margin-cards-container">
        {/* Card 1: Configuración de Margen */}
        <div className="margin-card">
          <div className="card-header">
            <span className="card-icon">⚙️</span>
            <span className="card-title">Configuración</span>
          </div>
          <div className="card-content">
            <div className="margin-item">
              <div className="margin-label">Apalancamiento</div>
              <div className="margin-value leverage">{leverage}x</div>
            </div>

            <div className="margin-item">
              <div className="margin-label">Tipo</div>
              <div className="margin-value">{margin_type}</div>
            </div>

            <div className="margin-item">
              <div className="margin-label">Nivel de Margen</div>
              <div className="margin-value" style={{ color: marginLevelColor }}>
                {margin_level.toFixed(2)} ({marginLevelText})
              </div>
            </div>

            <div className="margin-item">
              <div className="margin-label">Ratio de Margen</div>
              <div className="margin-value">{(margin_ratio * 100).toFixed(1)}%</div>
            </div>
          </div>
        </div>

        {/* Card 2: Balances y Fondos */}
        <div className="margin-card">
          <div className="card-header">
            <span className="card-icon">💰</span>
            <span className="card-title">Balances</span>
          </div>
          <div className="card-content">
            <div className="margin-item">
              <div className="margin-label">USDT Disponible</div>
              <div className="margin-value">${usdt_balance.toFixed(2)}</div>
            </div>

            <div className="margin-item">
              <div className="margin-label">DOGE Disponible</div>
              <div className="margin-value">{doge_balance.toFixed(2)} DOGE</div>
            </div>

            <div className="margin-item">
              <div className="margin-label">Precio DOGE</div>
              <div className="margin-value">${doge_price.toFixed(4)}</div>
            </div>

            <div className="margin-item">
              <div className="margin-label">Fondos Totales</div>
              <div className="margin-value">${total_available_usdt.toFixed(2)}</div>
            </div>
          </div>
        </div>

        {/* Card 3: Poder de Trading */}
        <div className="margin-card highlight">
          <div className="card-header">
            <span className="card-icon">🚀</span>
            <span className="card-title">Poder de Trading</span>
          </div>
          <div className="card-content">
            <div className="margin-item highlight">
              <div className="margin-label">Poder de Trading</div>
              <div className="margin-value trading-power">${trading_power_usdt.toFixed(2)}</div>
            </div>

            <div className="margin-note">
              💡 Con {leverage}x de apalancamiento, puedes operar hasta $
              {trading_power_usdt.toFixed(2)}
              usando ${total_available_usdt.toFixed(2)} de tus fondos.
            </div>

            <div className="margin-warning" style={{ color: is_safe ? '#00ff88' : '#ff4444' }}>
              {is_safe ? '✅ Cuenta segura' : '⚠️ Riesgo de liquidación'}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default MarginInfo
