import type { JSX } from 'react'

export interface Position {
  bot_type: string
  is_synthetic?: boolean
  is_plugin_bot?: boolean
  is_closed?: boolean
  status?: string
  type?: string
  close_reason?: string
  entry_price?: number
  current_price?: number
  exit_price?: number
  pnl?: number
  pnl_pct?: number
  pnl_net?: number
  pnl_net_pct?: number
  total_fees?: number
  close_time?: string | null
  exit_time?: string | null
}

export interface HistoryItemProps {
  position: Position
  formatPnL: (pnl: number, pnlPct: number) => JSX.Element
  formatDate: (dateString: string | null) => string
}
