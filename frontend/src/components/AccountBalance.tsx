import { useAccountBalance } from '@hooks/useAccountBalance'
import React from 'react'
import { BalanceRow } from './BalanceRow'
import { BalanceStatus } from './BalanceStatus'

// Removed unused interface

interface AccountBalanceProps {
  symbol?: string
  secondaryTitle?: string
}

const AccountBalance: React.FC<AccountBalanceProps> = ({
  symbol = 'DOGEUSDT',
  secondaryTitle = 'Synthetic'
}) => {
  // Usar el hook para obtener los datos de la cuenta (fallback)
  const { balance, loading, error, isOnline } = useAccountBalance()

  // Usar datos de la API
  const currentPrice = balance?.doge_price
  const isConnected = isOnline
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
    if (!balance) return '#ffa726'
    if (balance.current_balance > balance.initial_balance) return '#26a69a'
    if (balance.current_balance < balance.initial_balance) return '#ef5350'
    return '#ffa726'
  }

  const getBalanceIcon = () => {
    if (!balance) return '📊'
    if (balance.current_balance > balance.initial_balance) return '📈'
    if (balance.current_balance < balance.initial_balance) return '📉'
    return '📊'
  }

  const displayBalance = balance

  // Calcular campos faltantes si no están en el balance
  const balanceWithCalculatedFields = displayBalance
    ? {
        ...displayBalance,
        balance_change_pct:
          ((displayBalance.current_balance - displayBalance.initial_balance) /
            displayBalance.initial_balance) *
          100,
        is_profitable: displayBalance.current_balance > displayBalance.initial_balance
      }
    : null

  // Si está cargando, mostrar loading
  if (loading) {
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

  // Si hay error, mostrar error
  if (error) {
    return (
      <div className="account-balance">
        <div className="balance-header">
          <span className="balance-icon">❌</span>
          <span className="balance-title">Saldo de Cuenta</span>
        </div>
        <div className="balance-content">
          <div className="balance-row">
            <span className="balance-label" style={{ color: '#ef5350' }}>
              Error: {error}
            </span>
          </div>
        </div>
      </div>
    )
  }

  // Si no hay balance, mostrar mensaje
  if (!displayBalance) {
    return (
      <div className="account-balance">
        <div className="balance-header">
          <span className="balance-icon">📊</span>
          <span className="balance-title">Saldo de Cuenta</span>
        </div>
        <div className="balance-content">
          <div className="balance-row">
            <span className="balance-label">No hay datos disponibles</span>
          </div>
        </div>
      </div>
    )
  }

  const handleResetSynth = async () => {
    try {
      await fetch('/api/account/synth/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      // WS periodic update will refresh values shortly
    } catch (e) {
      console.error('Failed to reset synthetic account', e)
    }
  }

  return (
    <div className="account-balance">
      <div className="balance-header">
        <span className="balance-icon">{getBalanceIcon()}</span>
        <span className="balance-title">
          Saldo de Cuenta{secondaryTitle ? ` · ${secondaryTitle}` : ''}
        </span>
        <span
          className="connection-status"
          style={{
            fontSize: '0.75rem',
            fontWeight: 'normal',
            color: isConnected || isOnline ? '#26a69a' : '#ef5350',
            marginLeft: '8px'
          }}>
          {isConnected || isOnline ? 'online' : 'offline'}
        </span>
      </div>

      <div className="balance-cards-container">
        {/* Card 1: Balance Principal */}
        <div className="balance-card">
          <div
            className="card-header"
            style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="card-icon">🧪</span>
            <span className="card-title">Balance</span>
            {secondaryTitle === 'Synthetic' && (
              <button
                title="Resetear balance synthetic"
                onClick={handleResetSynth}
                style={{
                  marginLeft: 'auto',
                  background: '#374151',
                  color: '#f3f4f6',
                  border: '1px solid #4b5563',
                  borderRadius: 6,
                  padding: '4px 8px',
                  cursor: 'pointer'
                }}>
                Reset
              </button>
            )}
          </div>
          <div className="card-content">
            <BalanceRow
              label="Saldo Inicial:"
              value={formatCurrency(displayBalance.initial_balance)}
              valueType="default"
            />

            <BalanceRow
              label="Saldo Actual:"
              value={formatCurrency(displayBalance.current_balance)}
              valueType="current"
              color={getBalanceColor()}
            />

            <BalanceRow
              label="USDT Disponible:"
              value={formatCurrency(displayBalance.usdt_balance)}
              valueType="default"
            />

            <BalanceRow
              label="DOGE Disponible:"
              value={`${formatDoge(displayBalance.doge_balance)} DOGE`}
              valueType="default"
            />

            {displayBalance.invested !== undefined && (
              <BalanceRow
                label="Invertido:"
                value={formatCurrency(displayBalance.invested)}
                valueType="default"
                color="#3b82f6"
              />
            )}

            <BalanceRow
              label="Total en USDT:"
              value={formatCurrency(displayBalance.total_balance_usdt)}
              valueType="default"
            />
          </div>
        </div>

        {/* Card 2: Balance Disponible para Trading */}
        <div className="balance-card">
          <div className="card-header">
            <span className="card-icon">💰</span>
            <span className="card-title">Disponible para Trading</span>
          </div>
          <div className="card-content">
            <BalanceRow
              label="USDT Disponible:"
              value={formatCurrency(displayBalance.usdt_balance)}
              valueType="default"
              color="#26a69a"
            />

            <BalanceRow
              label="DOGE Disponible:"
              value={`${formatDoge(displayBalance.doge_balance)} DOGE`}
              valueType="default"
              color="#26a69a"
            />

            <BalanceRow
              label="Balance Total Disponible:"
              value={formatCurrency(displayBalance.total_balance_usdt)}
              valueType="default"
              color="#26a69a"
            />

            <BalanceRow
              label="Poder de Trading:"
              value={formatCurrency(displayBalance.total_balance_usdt)}
              valueType="default"
              color="#3b82f6"
            />

            <BalanceRow
              label="Max Posición (USDT):"
              value={formatCurrency(displayBalance.total_balance_usdt * 0.95)}
              valueType="default"
              color="#ffa726"
            />
          </div>
        </div>

        {/* Card 3: Precios y PnL */}
        <div className="balance-card">
          <div className="card-header">
            <span className="card-icon">📊</span>
            <span className="card-title">Precios & PnL</span>
          </div>
          <div className="card-content">
            <BalanceRow
              label={`Precio Actual (${symbol}):`}
              value={currentPrice ? `$${currentPrice.toFixed(5)}` : 'Calculando...'}
              valueType="default"
            />

            <BalanceRow
              label="1 USD = DOGE:"
              value={currentPrice ? `${formatDoge(1 / currentPrice)} DOGE` : 'Calculando...'}
              valueType="doge-rate"
            />

            <BalanceRow
              label="PnL Total:"
              value={formatCurrency(displayBalance.total_pnl || 0)}
              valueType="pnl"
              color={getBalanceColor()}
            />

            <BalanceRow
              label="Cambio:"
              value={formatPercentage(balanceWithCalculatedFields?.balance_change_pct || 0)}
              valueType="change"
              color={getBalanceColor()}
            />

            <BalanceRow
              label="Estado:"
              value={
                <BalanceStatus
                  totalPnl={displayBalance.total_pnl || 0}
                  balanceChangePct={balanceWithCalculatedFields?.balance_change_pct || 0}
                  isProfitable={balanceWithCalculatedFields?.is_profitable || false}
                />
              }
              valueType="status"
            />
          </div>
        </div>
      </div>
    </div>
  )
}

export default AccountBalance
