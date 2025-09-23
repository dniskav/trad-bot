#!/usr/bin/env python3
"""
Main FastAPI server - simplified and organized
"""

import signal
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import json
import asyncio
import threading
import time

# Core services
from services.real_trading_manager import RealTradingManager
from services.trading_tracker import TradingTracker
from services.bot_registry import bot_registry
from services.bot_interface import TradingSignal, SignalType
from persistence.service import PersistenceService
from persistence.file_repository import FilePersistenceRepository

# API modules
from features import health, trading, positions, bots, orders, klines, metrics
from websocket import manager as ws_manager

# Disable FastAPI access logs for polling endpoints
uvicorn_logger = logging.getLogger("uvicorn.access")
uvicorn_logger.setLevel(logging.WARNING)

# Application logger
logger = logging.getLogger("server")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Initialize FastAPI app
app = FastAPI(
    title="SMA Cross Trading Bot API", 
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todos los orígenes para desarrollo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
manager = ws_manager.ConnectionManager()

# Initialize services
real_trading_manager = RealTradingManager()
trading_tracker = TradingTracker(real_trading_manager.client)

# Set dependencies for API modules
if hasattr(health, 'set_dependencies'):
    health.set_dependencies()
trading.set_dependencies(trading_tracker)
positions.set_dependencies(real_trading_manager, trading_tracker, bot_registry)
bots.set_dependencies(real_trading_manager, trading_tracker)
orders.set_dependencies(trading_tracker)
# klines no necesita dependencias - usa Binance directamente
metrics.set_dependencies(real_trading_manager, trading_tracker)

# Set dependencies for services
from services.position_service import set_dependencies as set_position_service_deps
set_position_service_deps(real_trading_manager, trading_tracker, bot_registry)

# Register routes
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(trading.router, prefix="/api", tags=["trading"])
app.include_router(positions.router, prefix="/api", tags=["positions"])
app.include_router(bots.router, prefix="/api", tags=["bots"])
app.include_router(orders.router, prefix="/api", tags=["orders"])
app.include_router(klines.router, prefix="/api", tags=["klines"])
app.include_router(metrics.router, prefix="/api", tags=["metrics"])

# Import and register margin router
from api import margin
app.include_router(margin.router, prefix="/api", tags=["margin"])

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    logger.info("WebSocket client connected")
    
    try:
        # Send initial data
        await send_initial_data(websocket)
        
        # Start background task for periodic updates
        asyncio.create_task(periodic_data_updates(websocket))
        
        # Listen for client messages
        while True:
            try:
                # Wait for client message with timeout
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                await handle_client_message(websocket, data)
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                await manager.send_personal_message(json.dumps({
                    "type": "heartbeat",
                    "timestamp": datetime.now().isoformat()
                }), websocket)
            except WebSocketDisconnect:
                break
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")

async def send_initial_data(websocket: WebSocket):
    """Send initial data when client connects"""
    try:
        # Get current price
        current_price = None
        try:
            current_price = real_trading_manager.get_current_price('DOGEUSDT')
        except:
            pass
        
        # Get position info
        from services.position_service import get_position_info_for_frontend
        position_info = get_position_info_for_frontend(current_price)
        
        # Send initial data
        initial_data = {
            "type": "initial_data",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "current_price": current_price,
                "active_positions": position_info.get("active_positions", {}),
                "account_balance": position_info.get("account_balance", {}),
                "bot_status": position_info.get("bot_status", {})
            }
        }
        
        await manager.send_personal_message(json.dumps(initial_data), websocket)
        logger.info("Initial data sent to WebSocket client")
        
    except Exception as e:
        logger.error(f"Error sending initial data: {e}")

async def periodic_data_updates(websocket: WebSocket):
    """Send periodic updates every 5 seconds"""
    while True:
        try:
            await asyncio.sleep(5)  # Update every 5 seconds
            
            # Check if connection is still alive
            if websocket not in manager.active_connections:
                break
                
            # Get current price
            current_price = None
            try:
                current_price = real_trading_manager.get_current_price('DOGEUSDT')
            except:
                pass
            
            # Execute bot trading loop
            try:
                from services.bot_interface import MarketData
                market_data = MarketData(
                    symbol="DOGEUSDT",
                    interval="1m",
                    current_price=current_price or 0.0,
                    closes=[current_price or 0.0] * 10,  # Simular datos históricos
                    highs=[current_price or 0.0] * 10,
                    lows=[current_price or 0.0] * 10,
                    volumes=[1000] * 10,
                    timestamps=[int(datetime.now().timestamp())] * 10
                )
                bot_signals = bot_registry.analyze_all_bots(market_data)
                
                # Log simplificado: nombre, status, precio y confianza
                for bot_name, signal in bot_signals.items():
                    if signal and 'signal_type' in signal:
                        signal_type = signal.get('signal_type', 'HOLD')
                        confidence = signal.get('confidence', 0.0)
                        
                        # Log del bot y status
                        logger.info(f"🤖 {bot_name}: {signal_type}")
                        
                        # Log del precio
                        logger.info(f"💰 Precio: ${current_price or 0.0:.5f}")
                        
                        # Log de la confianza
                        logger.info(f"📊 Confianza: {confidence:.1%}")
            except Exception as e:
                logger.error(f"Error in bot trading loop: {e}")
            
            # Get updated position info
            from services.position_service import get_position_info_for_frontend
            position_info = get_position_info_for_frontend(current_price)
            
            # Send update
            update_data = {
                "type": "update",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "current_price": current_price,
                    "active_positions": position_info.get("active_positions", {}),
                    "account_balance": position_info.get("account_balance", {}),
                    "bot_status": position_info.get("bot_status", {})
                }
            }
            
            await manager.send_personal_message(json.dumps(update_data), websocket)
            
        except Exception as e:
            logger.error(f"Error in periodic updates: {e}")
            break

async def handle_client_message(websocket: WebSocket, message: str):
    """Handle messages from client"""
    try:
        data = json.loads(message)
        message_type = data.get("type")
        
        if message_type == "ping":
            # Respond to ping
            await manager.send_personal_message(json.dumps({
                "type": "pong",
                "timestamp": datetime.now().isoformat()
            }), websocket)
            
        elif message_type == "request_update":
            # Send immediate update
            await send_initial_data(websocket)
            
        else:
            logger.warning(f"Unknown message type: {message_type}")
            
    except json.JSONDecodeError:
        logger.error("Invalid JSON received from client")
    except Exception as e:
        logger.error(f"Error handling client message: {e}")

# Legacy endpoints (to be moved to api/ modules)
# These will be moved to their respective api/ modules

# WebSocket handlers for real-time data implemented above

async def background_trading_loop():
    """Background task to execute bot trading loop every 5 seconds"""
    while True:
        try:
            await asyncio.sleep(5)  # Wait 5 seconds
            
            # Get current price
            current_price = None
            try:
                current_price = real_trading_manager.get_current_price('DOGEUSDT')
            except:
                pass
            
            # Execute bot trading loop
            try:
                from services.bot_interface import MarketData
                market_data = MarketData(
                    symbol="DOGEUSDT",
                    interval="1m",
                    current_price=current_price or 0.0,
                    closes=[current_price or 0.0] * 10,  # Simular datos históricos
                    highs=[current_price or 0.0] * 10,
                    lows=[current_price or 0.0] * 10,
                    volumes=[1000] * 10,
                    timestamps=[int(datetime.now().timestamp())] * 10
                )
                bot_signals = bot_registry.analyze_all_bots(market_data)
                # Log simplificado: nombre, status, precio y confianza
                for bot_name, signal in bot_signals.items():
                    if signal and 'signal_type' in signal:
                        signal_type = signal.get('signal_type', 'HOLD')
                        confidence = signal.get('confidence', 0.0)
                        
                        # Log del bot y status
                        logger.info(f"🤖 {bot_name}: {signal_type}")
                        
                        # Log del precio
                        logger.info(f"💰 Precio: ${current_price or 0.0:.5f}")
                        
                        # Log de la confianza
                        logger.info(f"📊 Confianza: {confidence:.1%}")
            except Exception as e:
                logger.error(f"Error in background trading loop: {e}")
                
        except Exception as e:
            logger.error(f"Error in background trading loop: {e}")
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    """Start background tasks on server startup"""
    asyncio.create_task(background_trading_loop())
    logger.info("🚀 Background trading loop started")

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.info("Starting FastAPI server (simplified version)...")
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )