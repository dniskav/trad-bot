import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Import our existing modules
from metrics_logger import MetricsLogger, Trade
from sma_cross_bot import get_klines, get_closes, generate_signal, SYMBOL, INTERVAL

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="SMA Cross Trading Bot API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
metrics_logger = MetricsLogger(filepath="logs/trades.csv")
connected_clients: List[WebSocket] = []

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()

@app.get("/")
async def root():
    return {"message": "SMA Cross Trading Bot API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/klines")
async def get_klines_endpoint(
    symbol: str = Query(default=SYMBOL, description="Trading symbol"),
    interval: str = Query(default=INTERVAL, description="Candle interval"),
    limit: int = Query(default=100, description="Number of candles to return")
):
    """Get candlestick data for charting"""
    try:
        # Get raw klines data from Binance
        raw_klines = get_klines(symbol, interval, limit=limit)
        
        # Transform to proper candlestick format
        formatted_klines = []
        for kline in raw_klines:
            if len(kline) >= 6:  # Ensure we have enough data
                formatted_kline = {
                    "time": int(kline[0]),  # Open time
                    "open": float(kline[1]),
                    "high": float(kline[2]),
                    "low": float(kline[3]),
                    "close": float(kline[4]),
                    "volume": float(kline[5])
                }
                formatted_klines.append(formatted_kline)
        
        return formatted_klines
    except Exception as e:
        logger.error(f"Error getting klines: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to get candlestick data", "details": str(e)}
        )

@app.get("/metrics")
async def get_metrics():
    """Get trading metrics and history"""
    try:
        # Read trades from CSV
        trades = []
        try:
            with open("logs/trades.csv", "r") as f:
                lines = f.readlines()
                if len(lines) > 1:  # Skip header
                    for line in lines[1:]:
                        parts = line.strip().split(",")
                        if len(parts) >= 8:
                            trade = {
                                "entry_time": parts[0],
                                "exit_time": parts[1] if parts[1] else None,
                                "entry_price": float(parts[2]),
                                "exit_price": float(parts[3]) if parts[3] else None,
                                "position": parts[4],
                                "quantity": float(parts[5]),
                                "pnl": float(parts[6]) if parts[6] else None,
                                "return_pct": float(parts[7]) if parts[7] else None,
                                "version": parts[8] if len(parts) > 8 else "v1"
                            }
                            trades.append(trade)
        except FileNotFoundError:
            logger.warning("No trades.csv file found")
        
        # Get current market data
        try:
            closes = get_closes(SYMBOL, INTERVAL, limit=100)
            current_price = closes[-1] if len(closes) > 0 else None
            signal = generate_signal(closes) if len(closes) > 0 else "HOLD"
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            current_price = None
            signal = "ERROR"
        
        return {
            "trades": trades,
            "current_price": current_price,
            "signal": signal,
            "symbol": SYMBOL,
            "interval": INTERVAL,
            "total_trades": len(trades),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in metrics endpoint: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "details": str(e)}
        )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial connection message
        await manager.send_personal_message(
            json.dumps({
                "type": "connection",
                "data": {"status": "connected", "timestamp": datetime.now().isoformat()}
            }),
            websocket
        )
        
        # Keep connection alive and handle messages
        while True:
            try:
                # Send periodic updates
                await asyncio.sleep(5)
                
                # Get current market data with error handling
                try:
                closes = get_closes(SYMBOL, INTERVAL, limit=100)
                current_price = closes[-1] if len(closes) > 0 else None
                signal = generate_signal(closes) if len(closes) > 0 else "HOLD"
                except Exception as e:
                    logger.warning(f"Error getting market data: {e}")
                    current_price = None
                    signal = "HOLD"
                
                # Get candlestick data with error handling
                try:
                    raw_klines = get_klines(SYMBOL, INTERVAL, limit=100)
                    formatted_klines = []
                    for kline in raw_klines:
                        if len(kline) >= 6:  # Ensure we have enough data
                            formatted_kline = {
                                "time": int(kline[0]),  # Open time
                                "open": float(kline[1]),
                                "high": float(kline[2]),
                                "low": float(kline[3]),
                                "close": float(kline[4]),
                                "volume": float(kline[5])
                            }
                            formatted_klines.append(formatted_kline)
                except Exception as e:
                    logger.warning(f"Error getting klines data: {e}")
                    formatted_klines = []
                
                # Send price and candle data update
                await manager.send_personal_message(
                    json.dumps({
                        "type": "price",
                        "data": {
                            "price": current_price,
                            "signal": signal,
                            "candles": formatted_klines,
                            "timestamp": datetime.now().isoformat()
                        }
                    }),
                    websocket
                )
                
            except Exception as e:
                logger.error(f"Error in WebSocket loop: {e}")
                # Don't break the connection for temporary errors
                # Only break if it's a critical error
                if "Cannot call 'send' once a close message has been sent" in str(e):
                    logger.info("WebSocket connection closed by client")
                break
                # For other errors, continue the loop
                continue
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client")
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.get("/position")
async def get_position():
    """Get current trading position"""
    # This would normally come from the actual bot state
    # For now, return a mock position
    return {
        "position": "None",
        "quantity": 0,
        "entry_price": None,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    logger.info("Starting FastAPI server...")
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 