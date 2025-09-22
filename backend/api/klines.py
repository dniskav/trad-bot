#!/usr/bin/env python3
"""
Klines (candlestick data) endpoints
"""

from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# These will be injected by the main server
real_trading_manager = None

def set_dependencies(rtm):
    """Set dependencies from main server"""
    global real_trading_manager
    real_trading_manager = rtm

@router.get("/klines")
async def get_klines(symbol: str = "DOGEUSDT", interval: str = "1m", limit: int = 100):
    """Obtiene datos de velas japonesas"""
    try:
        klines_data = real_trading_manager.get_klines(symbol, interval, limit)
        return {"status": "success", "data": klines_data}
    except Exception as e:
        logger.error(f"Error getting klines: {e}")
        return {"status": "error", "message": str(e)}
