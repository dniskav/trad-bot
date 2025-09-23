import React from 'react'

interface AccountBalanceProps {
  balance: {
    initial_balance: number
    current_balance: number
    total_pnl: number
    balance_change_pct: number
    is_profitable: boolean
    usdt_balance: number
    doge_balance: number
    total_balance_usdt: number
  }
  currentPrice?: number
  symbol?: string
}

const AccountBalance: React.FC<AccountBalanceProps> = ({
  balance,
  currentPrice,
  symbol = 'DOGEUSDT'
}) => {
  const formatCurrency = (amount: number | undefined | null) => {
    if (amount === undefined || amount === null || isNaN(amount)) {
      return '$0.00'
    }
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount)
  }

  const formatDoge = (amount: number | undefined | null) => {
    if (amount === undefined || amount === null || isNaN(amount)) {
      return '0.00'
    }
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount)
  }

  const formatPercentage = (percentage: number | undefined | null) => {
    if (percentage === undefined || percentage === null || isNaN(percentage)) {
      return '0.00%'
    }
    const sign = percentage >= 0 ? '+' : ''
    return `${sign}${percentage.toFixed(2)}%`
  }

  const getBalanceColor = () => {
    if (!balance) return '#ffa726' // Naranja por defecto
    if (balance.is_profitable) return '#26a69a' // Verde para ganancias
    if (balance.current_balance < balance.initial_balance) return '#ef5350' // Rojo para pérdidas
    return '#ffa726' // Naranja para neutral
  }

  const getBalanceIcon = () => {
    if (!balance) return '📊' // Icono por defecto
    if (balance.is_profitable) return '📈'
    if (balance.current_balance < balance.initial_balance) return '📉'
    return '📊'
  }

  // Si no hay balance, mostrar loading
  if (!balance) {
    return (
      <div className="account-balance">
        <div className="balance-header">
          <span className="balance-icon">📊</span>
          <span className="balance-title">Saldo de Cuenta</span>
        </div>
        <div className="balance-content">
          <div className="balance-row">
            <span className="balance-label">Cargando...</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="account-balance">
      <div className="balance-header">
        <span className="balance-icon">{getBalanceIcon()}</span>
        <span className="balance-title">Saldo de Cuenta</span>
      </div>

      <div className="balance-cards-container">
        {/* Card 1: Balance Principal */}
        <div className="balance-card">
          <div className="card-header">
            <span className="card-icon">💰</span>
            <span className="card-title">Balance</span>
          </div>
          <div className="card-content">
            <div className="balance-row">
              <span className="balance-label">Saldo Inicial:</span>
              <span className="balance-value initial">
                {formatCurrency(balance.initial_balance)}
              </span>
            </div>

            <div className="balance-row">
              <span className="balance-label">Saldo Actual:</span>
              <span className="balance-value current" style={{ color: getBalanceColor() }}>
                {formatCurrency(balance.current_balance)}
              </span>
            </div>

            <div className="balance-row">
              <span className="balance-label">USDT Disponible:</span>
              <span className="balance-value usdt">{formatCurrency(balance.usdt_balance)}</span>
            </div>

            <div className="balance-row">
              <span className="balance-label">DOGE Disponible:</span>
              <span className="balance-value doge">{formatDoge(balance.doge_balance)} DOGE</span>
            </div>

            <div className="balance-row">
              <span className="balance-label">Total en USDT:</span>
              <span className="balance-value total-usdt">
                {formatCurrency(balance.total_balance_usdt)}
              </span>
            </div>
          </div>
        </div>

        {/* Card 2: Precios y PnL */}
        <div className="balance-card">
          <div className="card-header">
            <span className="card-icon">📊</span>
            <span className="card-title">Precios & PnL</span>
          </div>
          <div className="card-content">
            <div className="balance-row">
              <span className="balance-label">Precio Actual ({symbol}):</span>
              <span className="balance-value current-price">
                {currentPrice ? `$${currentPrice.toFixed(5)}` : 'Calculando...'}
              </span>
            </div>

            <div className="balance-row">
              <span className="balance-label">1 USD = DOGE:</span>
              <span className="balance-value doge-rate">
                {currentPrice ? `${formatDoge(1 / currentPrice)} DOGE` : 'Calculando...'}
              </span>
            </div>

            <div className="balance-row">
              <span className="balance-label">PnL Total:</span>
              <span className="balance-value pnl" style={{ color: getBalanceColor() }}>
                {formatCurrency(balance.total_pnl)}
              </span>
            </div>

            <div className="balance-row">
              <span className="balance-label">Cambio:</span>
              <span className="balance-value change" style={{ color: getBalanceColor() }}>
                {formatPercentage(balance.balance_change_pct)}
              </span>
            </div>

            <div className="balance-row">
              <span className="balance-label">Estado:</span>
              <span className="balance-value status" style={{ color: getBalanceColor() }}>
                {balance.is_profitable ? '🟢 Rentable' : '🔴 En Pérdida'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AccountBalance
