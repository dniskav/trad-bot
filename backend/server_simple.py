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
from aggressive_scalping_bot import generate_signal as generate_aggressive_signal
from trading_tracker import trading_tracker
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_data_for_json(data):
    """Convierte objetos datetime a string para serialización JSON"""
    if isinstance(data, dict):
        return {key: clean_data_for_json(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [clean_data_for_json(item) for item in data]
    elif isinstance(data, datetime):
        return data.isoformat()
    elif hasattr(data, 'isoformat'):  # Para otros objetos con isoformat
        return data.isoformat()
    else:
        return data

# Initialize FastAPI app
app = FastAPI(title="SMA Cross Trading Bot API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"],
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
            if websocket in self.active_connections:
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

# Función para generar señales de demostración
def generate_demo_signals():
    """Genera señales de demostración cuando no hay señales reales"""
    signals = ['BUY', 'SELL', 'HOLD']
    weights = [0.3, 0.3, 0.4]  # 30% BUY, 30% SELL, 40% HOLD
    
    conservative = random.choices(signals, weights=weights)[0]
    aggressive = random.choices(signals, weights=weights)[0]
    
    return conservative, aggressive

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
        # Validate interval parameter
        valid_intervals = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']
        if interval not in valid_intervals:
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid interval. Must be one of: {valid_intervals}"}
            )
        
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
async def websocket_endpoint(websocket: WebSocket, interval: str = Query(default=INTERVAL)):
    await manager.connect(websocket)
    
    # Validate interval parameter
    valid_intervals = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']
    if interval not in valid_intervals:
        await manager.send_personal_message(
            json.dumps({
                "type": "error",
                "data": {"error": f"Invalid interval. Must be one of: {valid_intervals}"}
            }),
            websocket
        )
        await manager.disconnect(websocket)
        return
    
    try:
        # Send initial connection message
        await manager.send_personal_message(
            json.dumps({
                "type": "connection",
                "data": {"status": "connected", "timestamp": datetime.now().isoformat()}
            }),
            websocket
        )
        
        # Send initial data immediately
        try:
            # Get price data
            closes = get_closes(SYMBOL, interval, limit=100)
            current_price = closes[-1] if len(closes) > 0 else None
            
            # Get bot signals
            conservative_signal = generate_signal(closes) if len(closes) > 0 else "HOLD"
            aggressive_signal = generate_aggressive_signal(closes) if len(closes) > 0 else "HOLD"
            
            # Si ambas señales están en HOLD, usar señales de demostración
            if conservative_signal == "HOLD" and aggressive_signal == "HOLD":
                demo_conservative, demo_aggressive = generate_demo_signals()
                # Solo usar demo si al menos una es diferente a HOLD
                if demo_conservative != "HOLD" or demo_aggressive != "HOLD":
                    conservative_signal = demo_conservative
                    aggressive_signal = demo_aggressive
                    logger.info(f"🎭 Usando señales de demostración: {conservative_signal} / {aggressive_signal}")
            
            # Update trading tracker
            trading_tracker.update_position('conservative', conservative_signal, current_price)
            trading_tracker.update_position('aggressive', aggressive_signal, current_price)
            
            # Get position info and clean for JSON serialization
            position_info = trading_tracker.get_all_positions()
            position_info = clean_data_for_json(position_info)
            
            # Get candlestick data
            raw_klines = get_klines(SYMBOL, interval, limit=50)
            formatted_klines = []
            for kline in raw_klines:
                if len(kline) >= 6:
                    formatted_kline = {
                        "time": int(kline[0]),
                        "open": float(kline[1]),
                        "high": float(kline[2]),
                        "low": float(kline[3]),
                        "close": float(kline[4]),
                        "volume": float(kline[5])
                    }
                    formatted_klines.append(formatted_kline)
            
            # Send initial price and candlestick data
            await manager.send_personal_message(
                json.dumps({
                    "type": "price",
                    "data": {
                        "price": current_price,
                        "signal": conservative_signal,
                        "timestamp": datetime.now().isoformat()
                    }
                }),
                websocket
            )
            
            # Send initial candlestick data
            await manager.send_personal_message(
                json.dumps({
                    "type": "candles",
                    "data": {
                        "candles": formatted_klines,
                        "symbol": SYMBOL,
                        "interval": interval,
                        "timestamp": datetime.now().isoformat(),
                        "bot_signals": {
                            "conservative": conservative_signal,
                            "aggressive": aggressive_signal,
                            "current_price": current_price,
                            "positions": position_info
                        }
                    }
                }),
                websocket
            )
        except Exception as e:
            logger.warning(f"Error sending initial data: {e}")
        
        # Send periodic updates every 10 seconds
        while True:
            try:
                await asyncio.sleep(10)  # Wait 10 seconds
                
                # Check if connection is still active
                if websocket not in manager.active_connections:
                    logger.info("WebSocket connection no longer active, breaking loop")
                    break
                
                # Get updated price data
                closes = get_closes(SYMBOL, interval, limit=100)
                current_price = closes[-1] if len(closes) > 0 else None
                
                # Get updated bot signals
                conservative_signal = generate_signal(closes) if len(closes) > 0 else "HOLD"
                aggressive_signal = generate_aggressive_signal(closes) if len(closes) > 0 else "HOLD"
                
                # Si ambas señales están en HOLD, usar señales de demostración
                if conservative_signal == "HOLD" and aggressive_signal == "HOLD":
                    demo_conservative, demo_aggressive = generate_demo_signals()
                    # Solo usar demo si al menos una es diferente a HOLD
                    if demo_conservative != "HOLD" or demo_aggressive != "HOLD":
                        conservative_signal = demo_conservative
                        aggressive_signal = demo_aggressive
                        logger.info(f"🎭 Usando señales de demostración: {conservative_signal} / {aggressive_signal}")
                
                # Update trading tracker
                trading_tracker.update_position('conservative', conservative_signal, current_price)
                trading_tracker.update_position('aggressive', aggressive_signal, current_price)
                
                # Get position info and clean for JSON serialization
                position_info = trading_tracker.get_all_positions()
                position_info = clean_data_for_json(position_info)
                
                # Get updated candlestick data
                raw_klines = get_klines(SYMBOL, interval, limit=50)
                formatted_klines = []
                for kline in raw_klines:
                    if len(kline) >= 6:
                        formatted_kline = {
                            "time": int(kline[0]),
                            "open": float(kline[1]),
                            "high": float(kline[2]),
                            "low": float(kline[3]),
                            "close": float(kline[4]),
                            "volume": float(kline[5])
                        }
                        formatted_klines.append(formatted_kline)
                
                # Send updated price data
                await manager.send_personal_message(
                    json.dumps({
                        "type": "price",
                        "data": {
                            "price": current_price,
                            "signal": conservative_signal,
                            "timestamp": datetime.now().isoformat()
                        }
                    }),
                    websocket
                )
                
                # Send updated candlestick data
                await manager.send_personal_message(
                    json.dumps({
                        "type": "candles",
                        "data": {
                            "candles": formatted_klines,
                            "symbol": SYMBOL,
                            "interval": interval,
                            "timestamp": datetime.now().isoformat(),
                            "bot_signals": {
                                "conservative": conservative_signal,
                                "aggressive": aggressive_signal,
                                "current_price": current_price,
                                "positions": position_info
                            }
                        }
                    }),
                    websocket
                )
                
            except Exception as e:
                logger.error(f"Error in WebSocket loop: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client")
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.get("/position")
async def get_position():
    """Get current trading position"""
    return {
        "position": "None",
        "quantity": 0,
        "entry_price": None,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    logger.info("Starting FastAPI server (simplified version)...")
    uvicorn.run(
        "server_simple:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 