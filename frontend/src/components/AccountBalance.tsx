import React from 'react'
import { useAccountBalance } from '../hooks/useAccountBalance'
import { usePriceData } from '../hooks/usePriceData'
import { BalanceRow } from './BalanceRow'
import { BalanceStatus } from './BalanceStatus'

interface AccountBalanceViewModel {
  initial_balance: number
  current_balance: number
  total_pnl: number
  balance_change_pct?: number
  is_profitable?: boolean
  usdt_balance: number
  doge_balance: number
  total_balance_usdt: number
  invested?: number
}

interface AccountBalanceProps {
  symbol?: string
  secondaryTitle?: string
}

const AccountBalance: React.FC<AccountBalanceProps> = ({
  symbol = 'DOGEUSDT',
  secondaryTitle = 'Synthetic'
}) => {
  // Usar el hook para obtener los datos de la cuenta
  const { balance, loading, error, isOnline } = useAccountBalance()

  // Usar el hook para obtener precios en tiempo real
  const priceData = usePriceData('DOGEUSDT')

  // Usar precio en tiempo real si está disponible, sino el del balance
  const currentPrice = priceData.price || balance?.doge_price
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

  // Calcular campos faltantes si no están en el balance
  const balanceWithCalculatedFields = balance
    ? {
        ...balance,
        balance_change_pct:
          balance.balance_change_pct ??
          ((balance.current_balance - balance.initial_balance) / balance.initial_balance) * 100,
        is_profitable: balance.is_profitable ?? balance.total_pnl > 0
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
  if (!balance) {
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
            color: isOnline ? '#26a69a' : '#ef5350',
            marginLeft: '8px'
          }}>
          {isOnline ? 'online' : 'offline'}
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
              value={formatCurrency(balance.initial_balance)}
              valueType="default"
            />

            <BalanceRow
              label="Saldo Actual:"
              value={formatCurrency(balance.current_balance)}
              valueType="current"
              color={getBalanceColor()}
            />

            <BalanceRow
              label="USDT Disponible:"
              value={formatCurrency(balance.usdt_balance)}
              valueType="default"
            />

            <BalanceRow
              label="DOGE Disponible:"
              value={`${formatDoge(balance.doge_balance)} DOGE`}
              valueType="default"
            />

            {balance.invested !== undefined && (
              <BalanceRow
                label="Invertido:"
                value={formatCurrency(balance.invested)}
                valueType="default"
                color="#3b82f6"
              />
            )}

            <BalanceRow
              label="Total en USDT:"
              value={formatCurrency(balance.total_balance_usdt)}
              valueType="default"
            />
          </div>
        </div>

        {/* Card 2: Precios y PnL */}
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
              value={formatCurrency(balance.total_pnl)}
              valueType="pnl"
              color={getBalanceColor()}
            />

            <BalanceRow
              label="Cambio:"
              value={formatPercentage(balanceWithCalculatedFields.balance_change_pct)}
              valueType="change"
              color={getBalanceColor()}
            />

            <BalanceRow
              label="Estado:"
              value={
                <BalanceStatus
                  totalPnl={balance.total_pnl}
                  balanceChangePct={balanceWithCalculatedFields.balance_change_pct}
                  isProfitable={balanceWithCalculatedFields.is_profitable}
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
