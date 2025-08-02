import React, { useState, useEffect } from 'react'

interface Trade {
  entry_time: string
  exit_time: string
  entry_price: number
  exit_price: number
  position: string
  quantity: number
  pnl: number
  return_pct: number
  version: string
}

interface TradeLogProps {
  className?: string
}

export const TradeLog: React.FC<TradeLogProps> = ({ className = '' }) => {
  const [trades, setTrades] = useState<Trade[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchTrades = async () => {
    try {
      setLoading(true)
      const response = await fetch('http://localhost:8000/metrics')
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data = await response.json()
      setTrades(data.trades || [])
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch trades')
      console.error('Error fetching trades:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTrades()
    const interval = setInterval(fetchTrades, 5000) // Refresh every 5 seconds
    return () => clearInterval(interval)
  }, [])

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount)
  }

  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(2)}%`
  }

  return (
    <div className={`trade-log ${className}`}>
      <div className="trade-log-header">
        <h3>Trade History</h3>
        <button onClick={fetchTrades} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {error && <div className="error-message">Error: {error}</div>}

      {loading ? (
        <div className="loading">Loading trades...</div>
      ) : trades.length === 0 ? (
        <div className="no-trades">No trades found</div>
      ) : (
        <div className="trades-table">
          <table>
            <thead>
              <tr>
                <th>Entry Time</th>
                <th>Exit Time</th>
                <th>Position</th>
                <th>Entry Price</th>
                <th>Exit Price</th>
                <th>Quantity</th>
                <th>P&L</th>
                <th>Return %</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade, index) => (
                <tr key={index} className={trade.pnl >= 0 ? 'profit' : 'loss'}>
                  <td>{formatDate(trade.entry_time)}</td>
                  <td>{trade.exit_time ? formatDate(trade.exit_time) : 'Active'}</td>
                  <td>{trade.position}</td>
                  <td>{formatCurrency(trade.entry_price)}</td>
                  <td>{trade.exit_price ? formatCurrency(trade.exit_price) : '-'}</td>
                  <td>{trade.quantity.toFixed(4)}</td>
                  <td className={trade.pnl >= 0 ? 'positive' : 'negative'}>
                    {trade.pnl ? formatCurrency(trade.pnl) : '-'}
                  </td>
                  <td className={trade.return_pct >= 0 ? 'positive' : 'negative'}>
                    {trade.return_pct ? formatPercentage(trade.return_pct) : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <style jsx>{`
        .trade-log {
          background: white;
          border-radius: 8px;
          padding: 20px;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .trade-log-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }

        .trade-log-header h3 {
          margin: 0;
          color: #333;
        }

        .trade-log-header button {
          padding: 8px 16px;
          background: #007bff;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
        }

        .trade-log-header button:disabled {
          background: #6c757d;
          cursor: not-allowed;
        }

        .error-message {
          background: #f8d7da;
          color: #721c24;
          padding: 10px;
          border-radius: 4px;
          margin-bottom: 20px;
        }

        .loading,
        .no-trades {
          text-align: center;
          padding: 40px;
          color: #6c757d;
        }

        .trades-table {
          overflow-x: auto;
        }

        table {
          width: 100%;
          border-collapse: collapse;
          font-size: 14px;
        }

        th,
        td {
          padding: 12px;
          text-align: left;
          border-bottom: 1px solid #dee2e6;
        }

        th {
          background: #f8f9fa;
          font-weight: bold;
          color: #495057;
        }

        tr:hover {
          background: #f8f9fa;
        }

        .positive {
          color: #28a745;
          font-weight: bold;
        }

        .negative {
          color: #dc3545;
          font-weight: bold;
        }

        .profit {
          background: rgba(40, 167, 69, 0.05);
        }

        .loss {
          background: rgba(220, 53, 69, 0.05);
        }
      `}</style>
    </div>
  )
}
