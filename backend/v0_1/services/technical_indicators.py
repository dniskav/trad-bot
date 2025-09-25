#!/usr/bin/env python3
"""
Servicio para calcular indicadores técnicos
"""

import logging
import requests
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)

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

def calculate_sma(prices: List[float], period: int) -> List[Optional[float]]:
    """
    Calcula la Media Móvil Simple (SMA)
    """
    if len(prices) < period:
        return [None] * len(prices)
    
    sma_values = []
    for i in range(len(prices)):
        if i < period - 1:
            sma_values.append(None)
        else:
            sma_sum = sum(prices[i - period + 1:i + 1])
            sma_values.append(sma_sum / period)
    
    return sma_values

def calculate_rsi(prices: List[float], period: int = 14) -> List[Optional[float]]:
    """
    Calcula el Relative Strength Index (RSI)
    """
    if len(prices) < period + 1:
        return [None] * len(prices)
    
    # Calcular cambios de precio
    deltas = []
    for i in range(1, len(prices)):
        deltas.append(prices[i] - prices[i-1])
    
    # Separar ganancias y pérdidas
    gains = [delta if delta > 0 else 0 for delta in deltas]
    losses = [-delta if delta < 0 else 0 for delta in deltas]
    
    rsi_values = [None]  # Primer valor es None
    
    # Calcular RSI usando media móvil exponencial
    if len(gains) >= period:
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        for i in range(period, len(gains)):
            if avg_loss == 0:
                rsi_values.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                rsi_values.append(rsi)
            
            # Actualizar promedios usando suavizado exponencial
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    else:
        rsi_values.extend([None] * (len(gains) - 1))
    
    return rsi_values

def calculate_technical_indicators(symbol: str = "DOGEUSDT", interval: str = "1m", limit: int = 100) -> Dict[str, Any]:
    """
    Calcula todos los indicadores técnicos para un símbolo dado
    """
    try:
        # Obtener datos de velas
        klines_data = get_klines_from_binance(symbol, interval, limit)
        
        if not klines_data:
            return {
                "candles": [],
                "indicators": {
                    "sma_fast": [],
                    "sma_slow": [],
                    "rsi": [],
                    "volume": [],
                    "timestamps": []
                }
            }
        
        # Extraer datos para cálculos
        closes = [kline["close"] for kline in klines_data]
        volumes = [kline["volume"] for kline in klines_data]
        timestamps = [kline["timestamp"] for kline in klines_data]
        
        # Calcular indicadores
        sma_fast = calculate_sma(closes, 8)   # SMA 8 períodos
        sma_slow = calculate_sma(closes, 21)  # SMA 21 períodos
        rsi = calculate_rsi(closes, 14)       # RSI 14 períodos
        
        # Formatear velas para el frontend
        formatted_candles = []
        for kline in klines_data:
            formatted_candles.append({
                "time": kline["timestamp"],
                "open": kline["open"],
                "high": kline["high"],
                "low": kline["low"],
                "close": kline["close"],
                "volume": kline["volume"]
            })
        
        return {
            "candles": formatted_candles,
            "indicators": {
                "sma_fast": sma_fast,
                "sma_slow": sma_slow,
                "rsi": rsi,
                "volume": volumes,
                "timestamps": timestamps
            }
        }
        
    except Exception as e:
        logger.error(f"Error calculating technical indicators: {e}")
        return {
            "candles": [],
            "indicators": {
                "sma_fast": [],
                "sma_slow": [],
                "rsi": [],
                "volume": [],
                "timestamps": []
            }
        }
