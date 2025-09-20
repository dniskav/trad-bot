#!/usr/bin/env python3
"""
Servidor de demostración simple para mostrar el sistema de trading
"""

import asyncio
import json
# Import our existing modules
from metrics_logger import MetricsLogger, Trade
from sma_cross_bot import get_klines, get_closes, generate_signal, SYMBOL, INTERVAL
from aggressive_scalping_bot import generate_signal as generate_aggressive_signal
import random
import logging
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Trading Bot Demo API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
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

# Trading tracker simple
class SimpleTradingTracker:
    def __init__(self):
        self.positions = {
            'conservative': None,
            'aggressive': None
        }
        self.last_signals = {
            'conservative': 'HOLD',
            'aggressive': 'HOLD'
        }
    
    def update_position(self, bot_type: str, signal: str, current_price: float, quantity: float = 1.0):
        # Si el bot cambió de señal y no tenemos posición abierta
        if (signal in ['BUY', 'SELL'] and 
            self.last_signals[bot_type] == 'HOLD' and 
            self.positions[bot_type] is None):
            
            # Abrir nueva posición
            self.positions[bot_type] = {
                'type': signal,
                'entry_price': current_price,
                'quantity': quantity,
                'entry_time': datetime.now().isoformat(),  # Convertir a string
                'current_price': current_price,
                'pnl': 0.0,
                'pnl_pct': 0.0
            }
            
            logger.info(f"🚀 {bot_type.upper()} - Nueva posición {signal} a ${current_price:.4f}")
            
        # Si el bot cambió a HOLD y tenemos posición abierta
        elif (signal == 'HOLD' and 
              self.last_signals[bot_type] in ['BUY', 'SELL'] and 
              self.positions[bot_type] is not None):
            
            # Cerrar posición
            position = self.positions[bot_type]
            position['exit_price'] = current_price
            position['exit_time'] = datetime.now().isoformat()  # Convertir a string
            position['current_price'] = current_price
            
            # Calcular PnL
            if position['type'] == 'BUY':
                position['pnl'] = (current_price - position['entry_price']) * position['quantity']
                position['pnl_pct'] = ((current_price - position['entry_price']) / position['entry_price']) * 100
            else:  # SELL
                position['pnl'] = (position['entry_price'] - current_price) * position['quantity']
                position['pnl_pct'] = ((position['entry_price'] - current_price) / position['entry_price']) * 100
            
            logger.info(f"🔒 {bot_type.upper()} - Cerrando posición: PnL ${position['pnl']:.4f} ({position['pnl_pct']:.2f}%)")
            
            # Resetear posición
            self.positions[bot_type] = None
            
        # Si tenemos posición abierta, actualizar precio actual y PnL
        elif self.positions[bot_type] is not None:
            position = self.positions[bot_type]
            position['current_price'] = current_price
            
            # Calcular PnL actual
            if position['type'] == 'BUY':
                position['pnl'] = (current_price - position['entry_price']) * position['quantity']
                position['pnl_pct'] = ((current_price - position['entry_price']) / position['entry_price']) * 100
            else:  # SELL
                position['pnl'] = (position['entry_price'] - current_price) * position['quantity']
                position['pnl_pct'] = ((position['entry_price'] - current_price) / position['entry_price']) * 100
        
        # Actualizar última señal
        self.last_signals[bot_type] = signal
    
    def get_position_info(self, bot_type: str):
        return self.positions[bot_type]
    
    def get_all_positions(self):
        return {
            'conservative': self.positions['conservative'],
            'aggressive': self.positions['aggressive'],
            'last_signals': self.last_signals
        }

# Instancia global del tracker
trading_tracker = SimpleTradingTracker()

@app.get("/")
async def root():
    return {"message": "Trading Bot Demo API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

def generate_demo_signals():
    """Genera señales de demostración"""
    signals = ['BUY', 'SELL', 'HOLD']
    weights = [0.3, 0.3, 0.4]  # 30% BUY, 30% SELL, 40% HOLD
    
    conservative = random.choices(signals, weights=weights)[0]
    aggressive = random.choices(signals, weights=weights)[0]
    
    return conservative, aggressive

def generate_demo_candles():
    """Genera datos de velas de demostración"""
    candles = []
    base_time = int(datetime.now().timestamp() * 1000)
    base_price = 0.90
    
    for i in range(50):
        time = base_time - (50 - i) * 60000  # 1 minuto entre velas
        price_change = random.uniform(-0.01, 0.01)
        base_price += price_change
        base_price = max(0.85, min(0.95, base_price))
        
        open_price = base_price
        close_price = base_price + random.uniform(-0.005, 0.005)
        high_price = max(open_price, close_price) + random.uniform(0, 0.005)
        low_price = min(open_price, close_price) - random.uniform(0, 0.005)
        
        candles.append({
            "time": time,
            "open": round(open_price, 4),
            "high": round(high_price, 4),
            "low": round(low_price, 4),
            "close": round(close_price, 4),
            "volume": random.uniform(1000, 5000)
        })
    
    return candles

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, interval: str = Query(default="1m")):
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
        
        # Send initial data immediately
        try:
            # Try to get real data from Binance
            try:
                # Get price data
                closes = get_closes(SYMBOL, interval, limit=100)
                current_price = closes[-1] if len(closes) > 0 else None
                
                # Get bot signals
                conservative_signal = generate_signal(closes) if len(closes) > 0 else "HOLD"
                aggressive_signal = generate_aggressive_signal(closes) if len(closes) > 0 else "HOLD"
                
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
                
                logger.info(f"📊 Usando datos reales de Binance: {SYMBOL}")
                
            except Exception as e:
                logger.warning(f"Error getting real data from Binance: {e}")
                logger.info("🔄 Usando datos de demostración...")
                
                # Fallback to demo data
                current_price = round(random.uniform(0.88, 0.92), 4)
                conservative_signal, aggressive_signal = generate_demo_signals()
                
                # Generate demo candles
                formatted_klines = generate_demo_candles()
            
            # Update trading tracker
            trading_tracker.update_position('conservative', conservative_signal, current_price)
            trading_tracker.update_position('aggressive', aggressive_signal, current_price)
            
            # Get position info
            position_info = trading_tracker.get_all_positions()
            
            # Send initial price data
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
            
            logger.info(f"📊 Enviando datos: {conservative_signal} / {aggressive_signal}")
            
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
                
                # Try to get real data from Binance
                try:
                    # Get updated price data
                    closes = get_closes(SYMBOL, interval, limit=100)
                    current_price = closes[-1] if len(closes) > 0 else None
                    
                    # Get updated bot signals
                    conservative_signal = generate_signal(closes) if len(closes) > 0 else "HOLD"
                    aggressive_signal = generate_aggressive_signal(closes) if len(closes) > 0 else "HOLD"
                    
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
                    
                except Exception as e:
                    logger.warning(f"Error getting real data from Binance: {e}")
                    logger.info("🔄 Usando datos de demostración...")
                    
                    # Fallback to demo data
                    current_price = round(random.uniform(0.88, 0.92), 4)
                    conservative_signal, aggressive_signal = generate_demo_signals()
                    formatted_klines = generate_demo_candles()
                
                # Update trading tracker
                trading_tracker.update_position('conservative', conservative_signal, current_price)
                trading_tracker.update_position('aggressive', aggressive_signal, current_price)
                
                # Get position info
                position_info = trading_tracker.get_all_positions()
                
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
                
                logger.info(f"📊 Actualizando datos: {conservative_signal} / {aggressive_signal}")
                
            except Exception as e:
                logger.error(f"Error in WebSocket loop: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client")
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    logger.info("Starting Trading Bot Demo Server...")
    uvicorn.run(
        "demo_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
