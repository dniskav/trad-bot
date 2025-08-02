import React from 'react'
import { useWebSocket } from '../hooks/useWebSocket'

interface DashboardProps {
  className?: string
}

export const Dashboard: React.FC<DashboardProps> = ({ className = '' }) => {
  const { isConnected, lastMessage, error } = useWebSocket()

  const getPositionData = () => {
    if (lastMessage?.type === 'position') {
      return lastMessage.data
    }
    return null
  }

  const getPriceData = () => {
    if (lastMessage?.type === 'price') {
      return lastMessage.data
    }
    return null
  }

  const position = getPositionData()
  const priceData = getPriceData()

  return (
    <div className={`dashboard ${className}`}>
      <div className="dashboard-header">
        <h2>Trading Bot Dashboard</h2>
        <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
        </div>
      </div>

      {error && <div className="error-message">Error: {error}</div>}

      <div className="dashboard-grid">
        <div className="dashboard-card">
          <h3>Current Position</h3>
          <div className="position-info">
            {position ? (
              <>
                <div className="position-type">{position.type || 'None'}</div>
                {position.quantity && (
                  <div className="position-quantity">Quantity: {position.quantity}</div>
                )}
                {position.entryPrice && (
                  <div className="position-entry">Entry: ${position.entryPrice}</div>
                )}
              </>
            ) : (
              <div className="no-position">No active position</div>
            )}
          </div>
        </div>

        <div className="dashboard-card">
          <h3>Last Price</h3>
          <div className="price-info">
            {priceData ? (
              <>
                <div className="current-price">${priceData.price?.toFixed(2) || 'N/A'}</div>
                <div className="price-change">
                  {priceData.change && (
                    <span className={priceData.change >= 0 ? 'positive' : 'negative'}>
                      {priceData.change >= 0 ? '+' : ''}
                      {priceData.change.toFixed(2)}%
                    </span>
                  )}
                </div>
              </>
            ) : (
              <div className="no-price">No price data</div>
            )}
          </div>
        </div>

        <div className="dashboard-card">
          <h3>Connection Status</h3>
          <div className="status-info">
            <div className="status-item">
              <span>WebSocket:</span>
              <span className={isConnected ? 'status-ok' : 'status-error'}>
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            <div className="status-item">
              <span>Last Update:</span>
              <span>{lastMessage ? new Date().toLocaleTimeString() : 'Never'}</span>
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        .dashboard {
          padding: 20px;
          background: #f5f5f5;
          border-radius: 8px;
        }

        .dashboard-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }

        .connection-status {
          padding: 8px 16px;
          border-radius: 20px;
          font-weight: bold;
        }

        .connection-status.connected {
          background: #d4edda;
          color: #155724;
        }

        .connection-status.disconnected {
          background: #f8d7da;
          color: #721c24;
        }

        .error-message {
          background: #f8d7da;
          color: #721c24;
          padding: 10px;
          border-radius: 4px;
          margin-bottom: 20px;
        }

        .dashboard-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 20px;
        }

        .dashboard-card {
          background: white;
          padding: 20px;
          border-radius: 8px;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .dashboard-card h3 {
          margin: 0 0 15px 0;
          color: #333;
        }

        .position-info,
        .price-info,
        .status-info {
          font-size: 14px;
        }

        .position-type {
          font-size: 18px;
          font-weight: bold;
          color: #007bff;
        }

        .current-price {
          font-size: 24px;
          font-weight: bold;
          color: #28a745;
        }

        .price-change.positive {
          color: #28a745;
        }

        .price-change.negative {
          color: #dc3545;
        }

        .status-item {
          display: flex;
          justify-content: space-between;
          margin-bottom: 8px;
        }

        .status-ok {
          color: #28a745;
        }

        .status-error {
          color: #dc3545;
        }

        .no-position,
        .no-price {
          color: #6c757d;
          font-style: italic;
        }
      `}</style>
    </div>
  )
}
