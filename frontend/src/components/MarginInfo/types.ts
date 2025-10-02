export interface MarginInfoData {
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
}

export interface MarginInfoProps {
  marginInfo: MarginInfoData | null
}
