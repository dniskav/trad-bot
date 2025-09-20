import React from 'react'

interface AccountBalanceProps {
  balance: {
    initial_balance: number
    current_balance: number
    total_pnl: number
    balance_change_pct: number
    is_profitable: boolean
  }
}

const AccountBalance: React.FC<AccountBalanceProps> = ({ balance }) => {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount)
  }

  const formatPercentage = (percentage: number) => {
    const sign = percentage >= 0 ? '+' : ''
    return `${sign}${percentage.toFixed(2)}%`
  }

  const getBalanceColor = () => {
    if (balance.is_profitable) return '#26a69a' // Verde para ganancias
    if (balance.current_balance < balance.initial_balance) return '#ef5350' // Rojo para pérdidas
    return '#ffa726' // Naranja para neutral
  }

  const getBalanceIcon = () => {
    if (balance.is_profitable) return '📈'
    if (balance.current_balance < balance.initial_balance) return '📉'
    return '📊'
  }

  return (
    <div className="account-balance">
      <div className="balance-header">
        <span className="balance-icon">{getBalanceIcon()}</span>
        <span className="balance-title">Saldo de Cuenta</span>
      </div>

      <div className="balance-content">
        <div className="balance-row">
          <span className="balance-label">Saldo Inicial:</span>
          <span className="balance-value initial">{formatCurrency(balance.initial_balance)}</span>
        </div>

        <div className="balance-row">
          <span className="balance-label">Saldo Actual:</span>
          <span className="balance-value current" style={{ color: getBalanceColor() }}>
            {formatCurrency(balance.current_balance)}
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
      </div>

      <div className="balance-summary">
        <div className="summary-item">
          <span className="summary-label">Estado:</span>
          <span className="summary-value" style={{ color: getBalanceColor() }}>
            {balance.is_profitable ? '🟢 Rentable' : '🔴 En Pérdida'}
          </span>
        </div>
      </div>
    </div>
  )
}

export default AccountBalance
