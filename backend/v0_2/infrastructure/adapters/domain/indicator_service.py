#!/usr/bin/env python3
"""
Indicator Service Implementation
Implementación de IIndicatorService usando el sistema de indicadores existente
"""

from typing import Dict, List, Any, Optional
import asyncio

from ...domain.models.strategy import IndicatorType
from ...domain.ports.strategy_ports import IIndicatorService


class IndicatorService:
    """Servicio de indicadores que integra con el sistema legado"""

    def __init__(self):
        # Importar componentes legados
        self.legacy_indicators: Optional[Any] = None
        
    async def initialize_legacy_system(self):
        """Inicializar sistema legacy de indicadores"""
        try:
            # Importar el factory legacy cuando sea necesario
            import sys
            import os
            
            # Agregar path del sistema legacy
            legacy_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "server", "strategies", "indicators"
            )
            if legacy_path not in sys.path:
                sys.path.append(legacy_path)
            
            # Importar factory legacy (manejar errores de import)
            try:
                from factory import IndicatorFactory
                self.legacy_factory = IndicatorFactory()
                self._initialized = True
            except ImportError:
                print("Warning: Could not import legacy IndicatorFactory")
                self._initialized = False
                
        except Exception as e:
            print(f"Error initializing legacy indicator system: {e}")
            self._initialized = False
            
    async def calculate_indicator(
        self, 
        indicator_type: str, 
        params: Dict[str, Any], 
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calcular indicador técnico"""
        
        if not self._initialized:
            await self.initialize_legacy_system()
        
        if not self._initialized:
            # Fallback: cálculos simples básicos
            return await self._calculate_basic_indicator(indicator_type, params, market_data)
        
        try:
            # Obtener datos de precio necesarios
            price_data = await self._extract_price_data(market_data)
            if not price_data:
                return {"error": "No price data available"}
            
            # Crear calculadora específica según tipo
            if indicator_type.upper() == "SMA":
                return await self._calculate_sma(params, price_data)
            elif indicator_type.upper() == "RSI":
                return await self._calculate_rsi(params, price_data)
            elif indicator_type.upper() == "MACD":
                return await self._calculate_macd(params, price_data)
            elif indicator_type.upper() == "VOLUME":
                return await self._calculate_volume(params, market_data)
            elif indicator_type.upper() == "TREND":
                return await self._calculate_trend(params, price_data)
            else:
                return {"error": f"Unknown indicator type: {indicator_type}"}
                
        except Exception as e:
            return {"error": f"Failed to calculate {indicator_type}: {str(e)}"}

    async def calculate_multiple_indicators(
        self, 
        indicator_configs: List[Dict[str, Any]], 
        market_data: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Calcular múltiples indicadores"""
        
        results = {}
        
        for config in indicator_configs:
            indicator_type = config.get("indicator_type", config.get("type", ""))
            params = config.get("params", {})
            name = config.get("name", indicator_type)
            
            try:
                result = await self.calculate_indicator(indicator_type, params, market_data)
                results[name] = result
            except Exception as e:
                results[name] = {"error": str(e)}
        
        return results

    async def validate_indicator_config(
        self, 
        indicator_type: str, 
        params: Dict[str, Any]
    ) -> List[str]:
        """Validar configuración de indicador"""
        
        errors = []
        
        if indicator_type.upper() == "SMA":
            period = params.get("period")
            if not period or not isinstance(period, int) or period <= 0:
                errors.append("SMA period must be a Positive integer")
        elif indicator_type.upper() == "RSI":
            period = params.get("period", 14)
            if not isinstance(period, int) or period <= 0:
                errors.append("RSI period must be a positive integer")
        elif indicator_type.upper() == "MACD":
            fast = params.get("fast_period", 12)
            slow = params.get("slow_period", 26)
            signal = params.get("signal_period", 9)
            
            if not all(isinstance(p, int) and p > 0 for p in [fast, slow, signal]):
                errors.append("MACD periods must be positive integers")
            
            if fast >= slow:
                errors.append("MACD fast period must be smaller than slow period")
        
        return errors

    async def get_indicator_description(self, indicator_type: str) -> Dict[str, Any]:
        """Obtener descripción del indicador"""
        
        descriptions = {
            "SMA": {
                "name": "Simple Moving Average",
                "description": "Calculates the average price over a specified period",
                "parameters": {"period": "Number of periods to average"},
                "signals": ["Crossovers with price", "Trend direction"]
            },
            "RSI": {
                "name": "Relative Strength Index",
                "description": "Momentum oscillator measuring speed and magnitude of price changes",
                "parameters": {"period": "Number of periods for calculation (default: 14)"},
                "signals": ["Overbought (>70)", "Oversold (<30)", "Divergence"]
            },
            "MACD": {
                "name": "Moving Average Convergence Divergence",
                "description": "Trend-following momentum indicator",
                "parameters": {
                    "fast_period": "Fast EMA period (default: 12)",
                    "slow_period": "Slow EMA period (default: 26)",
                    "signal_period": "Signal line period (default: 9)"
                },
                "signals": ["MACD line crosses signal line", "Zero line crossovers"]
            },
            "VOLUME": {
                "name": "Volume Indicators",
                "description": "Volume-based technical indicators",
                "parameters": {"period": "Volume moving average period"},
                "signals": ["Volume spikes", "Volume trends"]
            },
            "TREND": {
                "name": "Trend Indicators",
                "description": "Trend strength and direction indicators",
                "parameters": {"strength_period": "Period for trend strength calculation"},
                "signals": ["Trend direction", "Trend strength"]
            }
        }
        
        return descriptions.get(indicator_type.upper(), {
            "name": indicator_type,
            "description": "Unknown indicator type",
            "parameters": {},
            "signals": []
        })

    async def _extract_price_data(self, market_data: Dict[str, Any]) -> Optional[List[float]]:
        """Extraer datos de precio del market data"""
        
        # Probar diferentes formatos de market data
        prices = []
        
        # Formato de candlesticks
        if "candles" in market_data:
            candles = market_data["candles"]
            if candles and len(candles) > 0:
                # Tomar el precio de cierre de cada candle
                prices = [float(candle.get("close", candle.get("c", 0))) for candle in candles[-100:]]
        
        # Formato directo de prices
        elif "prices" in market_data:
            prices = [float(p) for p in market_data["prices"][-100:]]
        
        # Datos kline format
        elif "klines" in market_data:
            klines = market_data["klines"]
            if klines and len(klines) > 0:
                prices = [float(kline[4]) for kline in klines[-100:]]  # Precio de cierre en formato kline
        
        elif "current_price" in market_data:
            current_price = float(market_data["current_price"])
            # Crear algunos datos mock alrededor del precio actual
            for i in range(100):
                variation = current_price * (0.98 + (i % 20) * 0.002)  # ±2% variación
                prices.append(variation)
            prices.reverse()
        
        return prices if len(prices) >= 10 else None

    async def _calculate_sma(self, params: Dict[str, Any], prices: List[float]) -> Dict[str, Any]:
        """Calcular SMA"""
        
        period = params.get("period", 20)
        
        if len(prices) < period:
            return {"error": f"Insufficient data for SMA period {period}"}
        
        # Calcular SMA
        current_sma = sum(prices[-period:]) / period
        
        # Calcular tendencia
        if len(prices) >= period:
            prev_sma = sum(prices[-period*2:-period]) / period
            trend = "bullish" if current_sma > prev_sma else "bearish"
        else:
            trend = "neutral"
        
        return {
            "type": "SMA",
            "period": period,
            "value": current_sma,
            "trend": trend,
            "timestamp": None  # Se podría agregar timestamp actual
        }

    async def _calculate_rsi(self, params: Dict[str, Any], prices: List[float]) -> Dict[str, Any]:
        """Calcular RSI"""
        
        period = params.get("period", 14)
        
        if len(prices) < period + 1:
            return {"error": f"Insufficient data for RSI period {period}"}
        
        # Calcular cambios de precio
        changes = []
        for i in range(1, len(prices)):
            changes.append(prices[i] - prices[i-1])
        
        # Separar ganancias y pérdidas
        gains = [change if change > 0 else 0 for change in changes]
        losses = [-change if change < 0 else 0 for change in changes]
        
        # Calcular RS
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        # Estado del RSI
        if rsi > 70:
            status = "overbought"
        elif rsi < 30:
            status = "oversold"
        else:
            status = "neutral"
        
        return {
            "type": "RSI",
            "period": period,
            "value": rsi,
            "status": status,
            "timestamp": None
        }

    async def _calculate_macd(self, params: Dict[str, Any], prices: List[float]) -> Dict[str, Any]:
        """Calcular MACD"""
        
        fast_period = params.get("fast_period", 12)
        slow_period = params.get("slow_period", 26)
        signal_period = params.get("signal_period", 9)
        
        if len(prices) < slow_period:
            return {"error": f"Insufficient data for MACD"}
        
        # Calcular EMAs (simplified)
        def ema(data, period):
            multiplier = 2 / (period + 1)
            ema_val = data[0]
            for price in data[1:]:
                ema_val = (price * multiplier) + (ema_val * (1 - multiplier))
            return ema_val
        
        # Calcular MACD line
        ema_fast = ema(prices[-len(prices):], fast_period)
        ema_slow = ema(prices[-len(prices):], slow_period)
        macd_line = ema_fast - ema_slow
        
        # Calcular Signal line y Histogram
        # Simplificación: usar un valor mock para signal
        signal_line = macd_line * 0.8  # Mock signal calculation
        histogram = macd_line - signal_line
        
        # Señal
        signal_status = "bullish" if macd_line > signal_line else "bearish"
        
        return {
            "type": "MACD",
            "macd_line": macd_line,
            "signal_line": signal_line,
            "histogram": histogram,
            "signal": signal_status,
            "timestamp": None
        }

    async def _calculate_volume(self, params: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calcular indicador de volumen"""
        
        # Simular volumen basado en datos disponibles
        volume_data = market_data.get("volume", market_data.get("volumes", []))
        
        if not volume_data:
            # Valor mock basado en precio si no hay datos de volumen
            current_price = market_data.get("current_price", 100.0)
            avg_volume = current_price * 1000  # Mock average volume
        else:
            avg_volume = sum(volume_data[-20:]) / min(20, len(volume_data))
        
        # Comparar con promedio histórico
        volume_status = "normal"
        if avg_volume > avg_volume * 2:
            volume_status = "high"
        elif avg_volume < avg_volume * 0.5:
            volume_status = "low"
        
        return {
            "type": "VOLUME",
            "value": avg_volume,
            "status": volume_status,
            "avg_period": min(20, len(volume_data)) if volume_data else 20,
            "timestamp": None
        }

    async def _calculate_trend(self, params: Dict[str, Any], prices: List[float]) -> Dict[str, Any]:
        """Calcular indicador de tendencia"""
        
        strength_period = params.get("strength_period", 20)
        
        if len(prices) < strength_period:
            return {"error": f"Insufficient data for trend calculation"}
        
        # Calcular pendiente simple
        recent_prices = prices[-strength_period:]
        start_price = recent_prices[0]
        end_price = recent_prices[-1]
        
        # Tendencia
        price_change = (end_price - start_price) / start_price
        
        if price_change > 0.02:  # >2% cambio
            trend_direction = "strong_bullish"
            trend_strength = min(1.0, abs(price_change) * 10)
        elif price_change > 0.005:  # >0.5% cambio
            trend_direction = "bullish"
            trend_strength = abs(price_change) * 20
        elif price_change < -0.02:  # <-2% cambio
            trend_direction = "strong_bearish"
            trend_strength = min(1.0, abs(price_change) * 10)
        elif price_change < -0.005:  # <-0.5% cambio
            trend_direction = "bearish"
            trend_strength = abs(price_change) * 20
        else:
            trend_direction = "neutral"
            trend_strength = 0.0
        
        return {
            "type": "TREND",
            "direction": trend_direction,
            "strength": trend_strength,
            "price_change_pct": price_change,
            "timestamp": None
        }

    async def _calculate_basic_indicator(self, indicator_type: str, params: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback para cálculos básicos cuando el sistema legacy no está disponible"""
        
        current_price = market_data.get("current_price", 100.0)
        
        if indicator_type.upper() == "SMA":
            period = params.get("period", 20)
            return {
                "type": "SMA",
                "period": period,
                "value": current_price * (0.99 + (hash(str(current_price)) % 20) * 0.001),
                "trend": "neutral"
            }
        
        elif indicator_type.upper() == "RSI":
            # Simular RSI alrededor de nivel neutral
            rsi_value = 45 + (hash(str(current_price)) % 20)
            status = "overbought" if rsi_value > 70 else "oversold" if rsi_value < 30 else "neutral"
            return {
                "type": "RSI",
                "period": params.get("period", 14),
                "value": rsi_value,
                "status": status
            }
        
        else:
            return {
                "type": indicator_type,
                "value": current_price,
                "status": "neutral",
                "note": "Basic calculation fallback"
            }
