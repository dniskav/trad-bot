#!/usr/bin/env python3
"""
Klines (candlestick data) endpoints
"""

from fastapi import APIRouter
import logging
import requests
import time
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter()

# Binance API base URL
BINANCE_BASE_URL = "https://api.binance.com"

def get_klines_from_binance(symbol: str = "DOGEUSDT", interval: str = "1m", limit: int = 100) -> List[Dict[str, Any]]:
    """
    Obtiene datos de velas japonesas directamente desde Binance
    """
    try:
        url = f"{BINANCE_BASE_URL}/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        klines = response.json()
        
        # Convertir a formato más legible
        formatted_klines = []
        for kline in klines:
            formatted_klines.append({
                "timestamp": int(kline[0]),
                "open": float(kline[1]),
                "high": float(kline[2]),
                "low": float(kline[3]),
                "close": float(kline[4]),
                "volume": float(kline[5]),
                "close_time": int(kline[6]),
                "quote_volume": float(kline[7]),
                "trades": int(kline[8]),
                "taker_buy_base_volume": float(kline[9]),
                "taker_buy_quote_volume": float(kline[10])
            })
        
        return formatted_klines
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to Binance API: {e}")
        raise Exception(f"Error connecting to Binance: {e}")
    except Exception as e:
        logger.error(f"Error processing klines data: {e}")
        raise Exception(f"Error processing data: {e}")

@router.get("/klines")
async def get_klines(symbol: str = "DOGEUSDT", interval: str = "1m", limit: int = 100):
    """Obtiene datos de velas japonesas directamente desde Binance"""
    try:
        # Validar parámetros
        if limit > 1000:
            limit = 1000
        if limit < 1:
            limit = 100
            
        # Intervalos válidos de Binance
        valid_intervals = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
        if interval not in valid_intervals:
            interval = "1m"
            
        klines_data = get_klines_from_binance(symbol, interval, limit)
        
        return {
            "status": "success", 
            "data": klines_data,
            "symbol": symbol,
            "interval": interval,
            "count": len(klines_data)
        }
        
    except Exception as e:
        logger.error(f"Error getting klines: {e}")
        return {"status": "error", "message": str(e)}
