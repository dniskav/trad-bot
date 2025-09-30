import { API_CONFIG } from '@config/api'
import apiClient from '@services/apiClient'
import { useCallback, useEffect, useState } from 'react'
import { eventBus, EventType } from '../eventBus'
import type { PriceUpdateData } from '../eventBus/types'

const log = console

interface AccountBalance {
  initial_balance: number
  current_balance: number
  total_pnl: number
  usdt_balance: number
  doge_balance: number
  usdt_locked: number
  doge_locked: number
  doge_price: number
  total_balance_usdt: number
  invested: number
  last_updated: string
  // Extended fields from server (available balances and trading power)
  available_usdt?: number
  available_doge?: number
  available_balance_usdt?: number
  trading_power_usdt?: number
  max_position_size_usdt?: number
}

interface AccountResponse {
  success?: boolean
  data?: AccountBalance
  // Direct response format (current endpoint)
  initial_balance?: number
  current_balance?: number
  total_pnl?: number
  usdt_balance?: number
  doge_balance?: number
  usdt_locked?: number
  doge_locked?: number
  doge_price?: number
  total_balance_usdt?: number
  invested?: number
  last_updated?: string
  // Extended fields (optional)
  available_usdt?: number
  available_doge?: number
  available_balance_usdt?: number
  trading_power_usdt?: number
  max_position_size_usdt?: number
}

export const useAccountBalance = () => {
  const [balance, setBalance] = useState<AccountBalance | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isOnline, setIsOnline] = useState(true)
  const [currentPrice, setCurrentPrice] = useState<number | null>(null)

  console.log('🔍 useAccountBalance hook initialized')

  const fetchAccountBalance = useCallback(async () => {
    console.log('🔍 fetchAccountBalance called')
    setLoading(true)
    setError(null)

    try {
      console.log('🔍 Making API request to:', API_CONFIG.ENDPOINTS.ACCOUNT_SYNTH)
      const response = await apiClient.get<AccountResponse>(API_CONFIG.ENDPOINTS.ACCOUNT_SYNTH)
      console.log('🔍 API response received:', response.data)

      // Handle both response formats
      if (response.data.success && response.data.data) {
        // Wrapped format: { success: true, data: {...} }
        setBalance(response.data.data)
        setIsOnline(true)
        log.info('✅ Account balance fetched successfully (wrapped format)')
      } else if (response.data.initial_balance !== undefined) {
        // Direct format: { initial_balance: 1000, current_balance: 1000, ... }
        const balanceData: AccountBalance = {
          initial_balance: response.data.initial_balance || 0,
          current_balance: response.data.current_balance || 0,
          total_pnl: response.data.total_pnl || 0,
          usdt_balance: response.data.usdt_balance || 0,
          doge_balance: response.data.doge_balance || 0,
          usdt_locked: response.data.usdt_locked || 0,
          doge_locked: response.data.doge_locked || 0,
          doge_price: response.data.doge_price || 0,
          total_balance_usdt: response.data.total_balance_usdt || 0,
          invested: response.data.invested || 0,
          last_updated: response.data.last_updated || new Date().toISOString(),
          available_usdt: response.data.available_usdt,
          available_doge: response.data.available_doge,
          available_balance_usdt: response.data.available_balance_usdt,
          trading_power_usdt: response.data.trading_power_usdt,
          max_position_size_usdt: response.data.max_position_size_usdt
        }
        setBalance(balanceData)
        setIsOnline(true)
        log.info('✅ Account balance fetched successfully (direct format)')
      } else {
        setError('Error al cargar saldo de cuenta')
        setIsOnline(false)
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Error de conexión'
      setError(errorMessage)
      setIsOnline(false)
      console.error('Error fetching account balance:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  // Cargar balance inicial al montar el componente
  useEffect(() => {
    try {
      console.log('🔍 useEffect for fetchAccountBalance triggered (inside effect)')
      console.log('🔍 About to call fetchAccountBalance')
      fetchAccountBalance()
      console.log('🔍 fetchAccountBalance called successfully')
    } catch (error) {
      console.error('🔍 Error in useEffect:', error)
    }
  }, []) // Empty dependency array to run only once on mount

  // Escuchar actualizaciones de precio en tiempo real
  useEffect(() => {
    const handlePriceUpdate = (data: PriceUpdateData) => {
      console.log('💰 Price update received in useAccountBalance:', data)
      setCurrentPrice(data.price)

      // Actualizar el balance con el nuevo precio si existe
      if (balance) {
        setBalance((prev) =>
          prev
            ? {
                ...prev,
                doge_price: data.price,
                last_updated: data.timestamp
              }
            : null
        )
      }
    }

    eventBus.on(EventType.PRICE_UPDATE, handlePriceUpdate)

    return () => {
      eventBus.off(EventType.PRICE_UPDATE, handlePriceUpdate)
    }
  }, [balance])

  // Función para actualizar balance manualmente
  const refreshBalance = useCallback(() => {
    fetchAccountBalance()
  }, [fetchAccountBalance])

  // Usar precio en tiempo real si está disponible, sino el del balance
  const effectivePrice = currentPrice || balance?.doge_price || 0

  return {
    balance: balance ? { ...balance, doge_price: effectivePrice } : null,
    loading,
    error,
    isOnline,
    refreshBalance,
    currentPrice: effectivePrice
  }
}
