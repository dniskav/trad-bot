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
from trading_tracker import initialize_tracker
from real_trading_manager import real_trading_manager
from trading_capacity import filter_signal_by_capacity
import random

# Inicializar el trading tracker con el cliente de Binance
trading_tracker = initialize_tracker(real_trading_manager.client)

# Inicializar el estado de los bots desde el archivo de historial
real_trading_manager.initialize_bot_status_from_tracker(trading_tracker)

# Inicializar las posiciones activas desde el archivo de historial
real_trading_manager.initialize_active_positions_from_tracker(trading_tracker)

# Sincronizar posiciones activas con el estado real de Binance
real_trading_manager.sync_with_binance_orders(trading_tracker)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_data_for_json(data):
    """Convierte objetos datetime y otros tipos problemáticos a tipos JSON serializables"""
    try:
        if isinstance(data, dict):
            return {key: clean_data_for_json(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [clean_data_for_json(item) for item in data]
        elif isinstance(data, datetime):
            return data.isoformat()
        elif hasattr(data, 'isoformat'):  # Para otros objetos con isoformat
            return data.isoformat()
        elif isinstance(data, (bool, int, float, str, type(None))):
            return data  # Los tipos básicos de Python son JSON serializables
        elif str(type(data)).startswith('<class \'numpy.'):
            # Manejar tipos numpy específicos
            if 'bool' in str(type(data)):
                return bool(data)
            elif 'int' in str(type(data)):
                return int(data)
            elif 'float' in str(type(data)):
                return float(data)
            else:
                return str(data)
        elif hasattr(data, '__dict__'):  # Para objetos personalizados
            logger.warning(f"⚠️ Objeto personalizado encontrado: {type(data)} - {data}")
            return str(data)
        else:
            # Intentar convertir a string si no es serializable
            logger.warning(f"⚠️ Tipo no reconocido: {type(data)} - {data}")
            return str(data)
    except Exception as e:
        logger.error(f"❌ Error limpiando datos: {e} - Tipo: {type(data)} - Valor: {data}")
        return str(data)

def map_order_to_history_format(order_record):
    """Convierte un registro de orden al formato esperado por el frontend"""
    status = order_record.get('status', 'OPEN')
    
    # Para órdenes abiertas, usar precio actual como precio de salida
    exit_price = order_record.get('close_price')
    if exit_price is None and status in ['OPEN', 'UPDATED']:
        exit_price = order_record.get('current_price')
    
    # Para órdenes abiertas, mostrar "En curso" en lugar de fecha inválida
    close_time = order_record.get('close_time')
    if close_time is None and status in ['OPEN', 'UPDATED']:
        close_time = "En curso"  # Texto claro en lugar de fecha inválida
    
    # Calcular comisiones estimadas para órdenes abiertas
    fees_paid = order_record.get('fees_paid', 0.0)
    pnl_net = order_record.get('net_pnl', 0.0)
    
    # Si es una orden abierta, estimar comisiones y PnL neto
    if status in ['OPEN', 'UPDATED'] and fees_paid == 0.0:
        entry_price = order_record.get('entry_price', 0.0)
        current_price = order_record.get('current_price', entry_price)
        quantity = order_record.get('quantity', 0.0)
        
        # Calcular comisiones estimadas (0.1% entrada + 0.1% salida)
        trade_value_entry = entry_price * quantity
        trade_value_exit = current_price * quantity
        estimated_fees = (trade_value_entry + trade_value_exit) * 0.001
        
        # Calcular PnL neto estimado
        pnl_gross = order_record.get('pnl', 0.0)
        pnl_net = pnl_gross - estimated_fees
        
        fees_paid = estimated_fees
    
    return {
        'bot_type': order_record.get('bot_type', 'unknown'),
        'type': order_record.get('side', 'N/A'),
        'entry_price': order_record.get('entry_price', 0.0),
        'exit_price': exit_price,
        'quantity': order_record.get('quantity', 0.0),
        'entry_time': order_record.get('entry_time'),
        'close_time': close_time,
        'pnl': order_record.get('pnl', 0.0),
        'pnl_pct': order_record.get('pnl_percentage', 0.0),
        'pnl_net': pnl_net,
        'pnl_net_pct': (pnl_net / (order_record.get('entry_price', 0.0) * order_record.get('quantity', 0.0))) * 100 if order_record.get('entry_price', 0.0) > 0 and order_record.get('quantity', 0.0) > 0 else 0.0,
        'total_fees': fees_paid,
        'close_reason': 'Take Profit' if pnl_net > 0 else 'Stop Loss' if status == 'CLOSED' else 'En curso',
        'status': status,
        'duration_minutes': order_record.get('duration_minutes', 0)
    }

def get_position_info_for_frontend(current_price=None):
    """
    Obtiene información de posiciones del RealTradingManager y la formatea para el frontend
    """
    # Obtener posiciones del RealTradingManager
    real_positions = real_trading_manager.active_positions
    
    # Obtener datos del TradingTracker para historial y estadísticas
    tracker_data = trading_tracker.get_all_positions()
    
    # Formatear posiciones para el frontend - formato compatible con ActivePositions
    formatted_positions = {}
    
    for bot_type in ['conservative', 'aggressive']:
        bot_positions = real_positions.get(bot_type, {})
        
        if not bot_positions:
            # No hay posiciones activas
            formatted_positions[bot_type] = {}
        else:
            # Formatear cada posición individualmente
            formatted_bot_positions = {}
            for position_id, position in bot_positions.items():
                entry_price = position['entry_price']
                quantity = position['quantity']
                
                # Calcular PnL si tenemos precio actual
                pnl = 0.0
                pnl_pct = 0.0
                if current_price and entry_price > 0:
                    if position['side'] == 'BUY':
                        pnl = (current_price - entry_price) * quantity
                        pnl_pct = ((current_price - entry_price) / entry_price) * 100
                    else:  # SELL
                        pnl = (entry_price - current_price) * quantity
                        pnl_pct = ((entry_price - current_price) / entry_price) * 100
                
                formatted_bot_positions[position_id] = {
                    'id': position_id,
                    'bot_type': bot_type,
                    'type': position['side'],
                    'entry_price': entry_price,
                    'quantity': quantity,
                    'entry_time': position['entry_time'],
                    'current_price': current_price or entry_price,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'pnl_net': pnl,
                    'pnl_net_pct': pnl_pct,
                    'timestamp': position['entry_time']
                }
            
            formatted_positions[bot_type] = formatted_bot_positions
    
    # Convertir historial de órdenes al formato esperado por el frontend
    formatted_history = []
    if tracker_data.get('history'):
        for order_record in tracker_data['history']:
            mapped_record = map_order_to_history_format(order_record)
            formatted_history.append(mapped_record)
    
    # Combinar con datos del tracker
    return {
        'active_positions': {
            'conservative': formatted_positions.get('conservative', {}),
            'aggressive': formatted_positions.get('aggressive', {})
        },
        'last_signals': tracker_data.get('last_signals', {}),
        'history': formatted_history,
        'statistics': tracker_data.get('statistics', {}),
        'account_balance': tracker_data.get('account_balance', {}),
        'margin_info': real_trading_manager.get_margin_level() if real_trading_manager.leverage > 1 else None
    }

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

@app.get("/trading-status")
async def get_trading_status():
    """Obtiene el estado del sistema de trading real"""
    try:
        status = real_trading_manager.get_trading_status()
        return {
            "status": "success",
            "data": clean_data_for_json(status),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Error obteniendo estado de trading: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

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
            # Generar señales solo para bots activos
            conservative_signal_raw = "HOLD"
            aggressive_signal_raw = "HOLD"
            
            if real_trading_manager.is_bot_active('conservative'):
                conservative_signal_raw = generate_signal(closes) if len(closes) > 0 else "HOLD"
            
            if real_trading_manager.is_bot_active('aggressive'):
                aggressive_signal_raw = generate_aggressive_signal(closes) if len(closes) > 0 else "HOLD"
            
            # Filtrar señales según capacidad de trading
            conservative_signal = filter_signal_by_capacity(conservative_signal_raw, 'conservative')
            aggressive_signal = filter_signal_by_capacity(aggressive_signal_raw, 'aggressive')
            
            # Log si se filtró alguna señal
            if conservative_signal != conservative_signal_raw:
                logger.info(f"🛡️ CONSERVATIVE - Señal filtrada: {conservative_signal_raw} → {conservative_signal} (sin balance suficiente)")
            if aggressive_signal != aggressive_signal_raw:
                logger.info(f"🛡️ AGGRESSIVE - Señal filtrada: {aggressive_signal_raw} → {aggressive_signal} (sin balance suficiente)")
            
            # Ejecutar órdenes reales si el trading está habilitado
            if real_trading_manager.is_trading_enabled():
                try:
                    # Ejecutar órdenes reales para el bot conservador
                    if conservative_signal != "HOLD":
                        result = real_trading_manager.place_order('conservative', conservative_signal, current_price, trading_tracker)
                        if result.get('success', False):
                            logger.info(f"🚀 CONSERVATIVE - Orden real ejecutada: {conservative_signal} a ${current_price}")
                            # Actualizar trading tracker con la cantidad real ejecutada
                            order_info = result.get('order', {})
                            quantity = float(order_info.get('executedQty', 0))
                            if quantity > 0:
                                trading_tracker.update_position('conservative', conservative_signal, current_price, quantity)
                        else:
                            logger.error(f"❌ CONSERVATIVE - Error en trade: {result.get('error', 'Error desconocido')}")
                    
                    # Ejecutar órdenes reales para el bot agresivo
                    if aggressive_signal != "HOLD":
                        result = real_trading_manager.place_order('aggressive', aggressive_signal, current_price, trading_tracker)
                        if result.get('success', False):
                            logger.info(f"🚀 AGGRESSIVE - Orden real ejecutada: {aggressive_signal} a ${current_price}")
                            # Actualizar trading tracker con la cantidad real ejecutada
                            order_info = result.get('order', {})
                            quantity = float(order_info.get('executedQty', 0))
                            if quantity > 0:
                                trading_tracker.update_position('aggressive', aggressive_signal, current_price, quantity)
                        else:
                            logger.error(f"❌ AGGRESSIVE - Error en trade: {result.get('error', 'Error desconocido')}")
                        
                except Exception as e:
                    logger.error(f"❌ Error ejecutando órdenes reales: {e}")
                    # Fallback a señales de demostración si hay error
                    if conservative_signal == "HOLD" and aggressive_signal == "HOLD":
                        demo_conservative, demo_aggressive = generate_demo_signals()
                        if demo_conservative != "HOLD" or demo_aggressive != "HOLD":
                            conservative_signal = demo_conservative
                            aggressive_signal = demo_aggressive
                            logger.info(f"🎭 Usando señales de demostración (fallback): {conservative_signal} / {aggressive_signal}")
            else:
                # Si el trading no está habilitado, usar señales de demostración
                if conservative_signal == "HOLD" and aggressive_signal == "HOLD":
                    demo_conservative, demo_aggressive = generate_demo_signals()
                    if demo_conservative != "HOLD" or demo_aggressive != "HOLD":
                        conservative_signal = demo_conservative
                        aggressive_signal = demo_aggressive
                        logger.info(f"🎭 Usando señales de demostración (trading deshabilitado): {conservative_signal} / {aggressive_signal}")
            
            # Update trading tracker (solo para trades de demo)
            if not real_trading_manager.is_trading_enabled():
                trading_tracker.update_position('conservative', conservative_signal, current_price)
                trading_tracker.update_position('aggressive', aggressive_signal, current_price)
            
            # Actualizar estado de todas las órdenes abiertas
            real_trading_manager.update_all_orders_status(trading_tracker)
            
            # Verificar y cerrar posiciones por take profit/stop loss
            real_trading_manager.check_and_close_positions(trading_tracker, current_price)
            
            # Actualizar balance actual desde Binance
            if trading_tracker and hasattr(trading_tracker, 'update_current_balance_from_binance'):
                trading_tracker.update_current_balance_from_binance()
                trading_tracker.save_history()
            
            # Get position info from RealTradingManager and sync with TradingTracker format
            position_info = get_position_info_for_frontend(current_price)
            
            # Log active positions for debugging
            active_positions = position_info.get('active_positions', {})
            conservative_count = len(active_positions.get('conservative', {}))
            aggressive_count = len(active_positions.get('aggressive', {}))
            logger.info(f"📊 Posiciones activas - Conservative: {conservative_count}, Aggressive: {aggressive_count}")
            
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
                
                # Get updated bot signals (solo para bots activos)
                conservative_signal_raw = "HOLD"
                aggressive_signal_raw = "HOLD"
                
                if real_trading_manager.is_bot_active('conservative'):
                    conservative_signal_raw = generate_signal(closes) if len(closes) > 0 else "HOLD"
                
                if real_trading_manager.is_bot_active('aggressive'):
                    aggressive_signal_raw = generate_aggressive_signal(closes) if len(closes) > 0 else "HOLD"
                
                # Filtrar señales según capacidad de trading
                conservative_signal = filter_signal_by_capacity(conservative_signal_raw, 'conservative')
                aggressive_signal = filter_signal_by_capacity(aggressive_signal_raw, 'aggressive')
                
                # Log si se filtró alguna señal
                if conservative_signal != conservative_signal_raw:
                    logger.info(f"🛡️ CONSERVATIVE - Señal filtrada: {conservative_signal_raw} → {conservative_signal} (sin balance suficiente)")
                if aggressive_signal != aggressive_signal_raw:
                    logger.info(f"🛡️ AGGRESSIVE - Señal filtrada: {aggressive_signal_raw} → {aggressive_signal} (sin balance suficiente)")
                
                # Actualizar estado de todas las órdenes abiertas
                real_trading_manager.update_all_orders_status(trading_tracker)
                
                # Verificar y cerrar posiciones por take profit/stop loss
                real_trading_manager.check_and_close_positions(trading_tracker, current_price)
                
                # Actualizar balance actual desde Binance
                if trading_tracker and hasattr(trading_tracker, 'update_current_balance_from_binance'):
                    trading_tracker.update_current_balance_from_binance()
                    trading_tracker.save_history()
                
                # Ejecutar órdenes reales si el trading está habilitado
                if real_trading_manager.is_trading_enabled():
                    try:
                        # Ejecutar órdenes reales para el bot conservador
                        if conservative_signal != "HOLD":
                            result = real_trading_manager.place_order('conservative', conservative_signal, current_price, trading_tracker)
                            if result.get('success', False):
                                logger.info(f"🚀 CONSERVATIVE - Orden real ejecutada: {conservative_signal} a ${current_price}")
                                # Actualizar trading tracker con la cantidad real ejecutada
                                order_info = result.get('order', {})
                                quantity = float(order_info.get('executedQty', 0))
                                if quantity > 0:
                                    trading_tracker.update_position('conservative', conservative_signal, current_price, quantity)
                            else:
                                logger.error(f"❌ CONSERVATIVE - Error en trade: {result.get('error', 'Error desconocido')}")
                        
                        # Ejecutar órdenes reales para el bot agresivo
                        if aggressive_signal != "HOLD":
                            result = real_trading_manager.place_order('aggressive', aggressive_signal, current_price, trading_tracker)
                            if result.get('success', False):
                                logger.info(f"🚀 AGGRESSIVE - Orden real ejecutada: {aggressive_signal} a ${current_price}")
                                # Actualizar trading tracker con la cantidad real ejecutada
                                order_info = result.get('order', {})
                                quantity = float(order_info.get('executedQty', 0))
                                if quantity > 0:
                                    trading_tracker.update_position('aggressive', aggressive_signal, current_price, quantity)
                            else:
                                logger.error(f"❌ AGGRESSIVE - Error en trade: {result.get('error', 'Error desconocido')}")
                            
                    except Exception as e:
                        logger.error(f"❌ Error ejecutando órdenes reales: {e}")
                        # Fallback a señales de demostración si hay error
                        if conservative_signal == "HOLD" and aggressive_signal == "HOLD":
                            demo_conservative, demo_aggressive = generate_demo_signals()
                            if demo_conservative != "HOLD" or demo_aggressive != "HOLD":
                                conservative_signal = demo_conservative
                                aggressive_signal = demo_aggressive
                                logger.info(f"🎭 Usando señales de demostración (fallback): {conservative_signal} / {aggressive_signal}")
                else:
                    # Si el trading no está habilitado, usar señales de demostración
                    if conservative_signal == "HOLD" and aggressive_signal == "HOLD":
                        demo_conservative, demo_aggressive = generate_demo_signals()
                        if demo_conservative != "HOLD" or demo_aggressive != "HOLD":
                            conservative_signal = demo_conservative
                            aggressive_signal = demo_aggressive
                            logger.info(f"🎭 Usando señales de demostración (trading deshabilitado): {conservative_signal} / {aggressive_signal}")
                
                # Update trading tracker (solo para trades de demo)
                if not real_trading_manager.is_trading_enabled():
                    trading_tracker.update_position('conservative', conservative_signal, current_price)
                    trading_tracker.update_position('aggressive', aggressive_signal, current_price)
                
                # Get position info from RealTradingManager and sync with TradingTracker format
                position_info = get_position_info_for_frontend(current_price)
                
                # Log active positions for debugging
                active_positions = position_info.get('active_positions', {})
                conservative_count = len(active_positions.get('conservative', {}))
                aggressive_count = len(active_positions.get('aggressive', {}))
                logger.info(f"📊 Posiciones activas - Conservative: {conservative_count}, Aggressive: {aggressive_count}")
                
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

@app.post("/bot/{bot_type}/activate")
async def activate_bot(bot_type: str):
    """Activa un bot específico"""
    try:
        if bot_type not in ['conservative', 'aggressive']:
            return {"status": "error", "message": "Tipo de bot inválido"}
        
        success = real_trading_manager.activate_bot(bot_type, trading_tracker)
        if success:
            return {"status": "success", "message": f"Bot {bot_type} activado"}
        else:
            return {"status": "error", "message": f"Error activando bot {bot_type}"}
    except Exception as e:
        logger.error(f"Error activating bot {bot_type}: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/bot/{bot_type}/deactivate")
async def deactivate_bot(bot_type: str):
    """Desactiva un bot específico y cierra sus posiciones"""
    try:
        if bot_type not in ['conservative', 'aggressive']:
            return {"status": "error", "message": "Tipo de bot inválido"}
        
        success = real_trading_manager.deactivate_bot(bot_type, trading_tracker)
        if success:
            return {"status": "success", "message": f"Bot {bot_type} desactivado"}
        else:
            return {"status": "error", "message": f"Error desactivando bot {bot_type}"}
    except Exception as e:
        logger.error(f"Error deactivating bot {bot_type}: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/orders/status")
async def get_orders_status():
    """Obtiene el estado detallado de todas las órdenes"""
    try:
        if not trading_tracker:
            return JSONResponse({"error": "Trading tracker no inicializado"}, status_code=500)
        
        open_orders = trading_tracker.get_open_orders()
        closed_orders = trading_tracker.get_closed_orders()
        
        # Formatear órdenes para el frontend
        def format_order(order):
            return {
                'order_id': order['order_id'],
                'position_id': order['position_id'],
                'bot_type': order['bot_type'],
                'symbol': order['symbol'],
                'side': order['side'],
                'quantity': order['quantity'],
                'entry_price': order['entry_price'],
                'entry_time': order['entry_time'].isoformat() if order['entry_time'] else None,
                'status': order['status'],
                'current_price': order['current_price'],
                'pnl': order['pnl'],
                'pnl_percentage': order['pnl_percentage'],
                'close_price': order['close_price'],
                'close_time': order['close_time'].isoformat() if order['close_time'] else None,
                'duration_minutes': order['duration_minutes'],
                'fees_paid': order['fees_paid'],
                'net_pnl': order['net_pnl']
            }
        
        return JSONResponse({
            'open_orders': [format_order(order) for order in open_orders],
            'closed_orders': [format_order(order) for order in closed_orders[-10:]],  # Últimas 10 cerradas
            'summary': {
                'total_open': len(open_orders),
                'total_closed': len(closed_orders),
                'total_pnl': trading_tracker.total_pnl,
                'current_balance': trading_tracker.current_balance
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estado de órdenes: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/orders/{order_id}/status")
async def get_order_status(order_id: str):
    """Obtiene el estado detallado de una orden específica"""
    try:
        if not trading_tracker:
            return JSONResponse({"error": "Trading tracker no inicializado"}, status_code=500)
        
        order = trading_tracker.get_order_status(order_id)
        if not order:
            return JSONResponse({"error": "Orden no encontrada"}, status_code=404)
        
        return JSONResponse({
            'order_id': order['order_id'],
            'position_id': order['position_id'],
            'bot_type': order['bot_type'],
            'symbol': order['symbol'],
            'side': order['side'],
            'quantity': order['quantity'],
            'entry_price': order['entry_price'],
            'entry_time': order['entry_time'].isoformat() if order['entry_time'] else None,
            'status': order['status'],
            'current_price': order['current_price'],
            'pnl': order['pnl'],
            'pnl_percentage': order['pnl_percentage'],
            'close_price': order['close_price'],
            'close_time': order['close_time'].isoformat() if order['close_time'] else None,
            'duration_minutes': order['duration_minutes'],
            'fees_paid': order['fees_paid'],
            'net_pnl': order['net_pnl']
        })
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estado de orden {order_id}: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/bot/status")
async def get_bot_status():
    """Obtiene el estado de todos los bots"""
    try:
        status = real_trading_manager.get_trading_status()
        return {
            "status": "success", 
            "data": {
                "bot_status": status.get("bot_status", {}),
                "active_positions": status.get("active_positions", {}),
                "dynamic_limits": status.get("dynamic_limits", {})
            }
        }
    except Exception as e:
        logger.error(f"Error getting bot status: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/bot/limits")
async def get_dynamic_limits():
    """Obtiene información sobre los límites dinámicos de posiciones"""
    try:
        limits = real_trading_manager.get_dynamic_position_limits()
        return {
            "status": "success",
            "data": limits
        }
    except Exception as e:
        logger.error(f"Error getting dynamic limits: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    logger.info("Starting FastAPI server (simplified version)...")
    uvicorn.run(
        "server_simple:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 