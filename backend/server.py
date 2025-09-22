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
from real_trading_manager import RealTradingManager
from trading_tracker import TradingTracker
from bot_registry import bot_registry
from bot_interface import TradingSignal, SignalType
from persistence.service import PersistenceService
from persistence.file_repository import FilePersistenceRepository

# API modules
from api import health, trading, positions, bots, orders, klines, metrics
from websocket import manager as ws_manager

# Disable FastAPI access logs for polling endpoints
uvicorn_logger = logging.getLogger("uvicorn.access")
uvicorn_logger.setLevel(logging.WARNING)

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
trading_tracker = TradingTracker()

# Set dependencies for API modules
if hasattr(health, 'set_dependencies'):
    health.set_dependencies()
trading.set_dependencies(trading_tracker)
positions.set_dependencies(real_trading_manager, trading_tracker, bot_registry)
bots.set_dependencies(real_trading_manager, trading_tracker)
orders.set_dependencies(trading_tracker)
klines.set_dependencies(real_trading_manager)
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

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client")
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Legacy endpoints (to be moved to api/ modules)
# These will be moved to their respective api/ modules

# TODO: Move remaining endpoints from server_simple.py to appropriate api/ modules
# TODO: Add WebSocket handlers for real-time data
# TODO: Add background tasks for data synchronization

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