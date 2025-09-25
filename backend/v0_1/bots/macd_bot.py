#!/usr/bin/env python3
"""
Bot de trading basado en MACD (Moving Average Convergence Divergence)
Ejemplo de bot plug-and-play
"""

import numpy as np
from typing import List, Tuple
from services.bot_interface import BaseBot, BotConfig, MarketData, TradingSignal, SignalType

class MACDBot(BaseBot):
    """
    Bot que usa MACD para generar señales de trading
    """
    
    def __init__(self, config: BotConfig):
        super().__init__(config)
        
        # Parámetros específicos del bot MACD
        self.fast_period = config.custom_params.get('fast_period', 12) if config.custom_params else 12
        self.slow_period = config.custom_params.get('slow_period', 26) if config.custom_params else 26
        self.signal_period = config.custom_params.get('signal_period', 9) if config.custom_params else 9
        self.min_signal_strength = config.custom_params.get('min_signal_strength', 0.0001) if config.custom_params else 0.0001
        
        self.logger.info(f"📊 MACD Bot configurado: fast={self.fast_period}, slow={self.slow_period}, signal={self.signal_period}")
    
    def calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """
        Calcula la Media Móvil Exponencial (EMA)
        
        Args:
            prices: Lista de precios
            period: Período para la EMA
            
        Returns:
            List[float]: Valores de EMA
        """
        if len(prices) < period:
            return []
        
        ema_values = []
        multiplier = 2 / (period + 1)
        
        # EMA inicial (SMA) - asegurar que es escalar
        ema = float(np.mean(prices[:period]))
        ema_values.append(ema)
        
        # Calcular EMA para el resto
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
            ema_values.append(ema)
        
        return ema_values
    
    def calculate_macd(self, prices: List[float]) -> Tuple[List[float], List[float], List[float]]:
        """
        Calcula MACD, Signal y Histogram
        
        Args:
            prices: Lista de precios de cierre
            
        Returns:
            Tuple con (macd_line, signal_line, histogram)
        """
        if len(prices) < self.slow_period:
            return [], [], []
        
        # Calcular EMAs
        ema_fast = self.calculate_ema(prices, self.fast_period)
        ema_slow = self.calculate_ema(prices, self.slow_period)
        
        # Ajustar longitudes
        min_length = min(len(ema_fast), len(ema_slow))
        ema_fast = ema_fast[-min_length:]
        ema_slow = ema_slow[-min_length:]
        
        # Calcular MACD line
        macd_line = [fast - slow for fast, slow in zip(ema_fast, ema_slow)]
        
        if len(macd_line) < self.signal_period:
            return macd_line, [], []
        
        # Calcular Signal line (EMA del MACD)
        signal_line = self.calculate_ema(macd_line, self.signal_period)
        
        # Ajustar longitudes
        min_length = min(len(macd_line), len(signal_line))
        macd_line = macd_line[-min_length:]
        signal_line = signal_line[-min_length:]
        
        # Calcular Histogram
        histogram = [macd - signal for macd, signal in zip(macd_line, signal_line)]
        
        return macd_line, signal_line, histogram
    
    def analyze_market(self, market_data: MarketData) -> TradingSignal:
        """
        Analiza el mercado usando MACD y genera una señal
        
        Args:
            market_data: Datos de mercado actuales
            
        Returns:
            TradingSignal: Señal generada
        """
        if len(market_data.closes) < self.slow_period + self.signal_period:
            return TradingSignal(
                bot_name=self.config.name,
                signal_type=SignalType.HOLD,
                confidence=0.0,
                entry_price=market_data.current_price,
                reasoning="Datos insuficientes para calcular MACD",
                is_synthetic=self.config.synthetic_mode,
                metadata={"macd": None, "data_points": len(market_data.closes)}
            )
        
        # Calcular MACD
        macd_line, signal_line, histogram = self.calculate_macd(market_data.closes)
        
        if len(macd_line) < 2 or len(signal_line) < 2:
            return TradingSignal(
                bot_name=self.config.name,
                signal_type=SignalType.HOLD,
                confidence=0.0,
                entry_price=market_data.current_price,
                reasoning="MACD insuficiente para análisis",
                is_synthetic=self.config.synthetic_mode,
                metadata={"macd": None}
            )
        
        # Valores actuales y anteriores - asegurar que son escalares
        current_macd = float(macd_line[-1])
        previous_macd = float(macd_line[-2])
        current_signal = float(signal_line[-1])
        previous_signal = float(signal_line[-2])
        current_histogram = float(histogram[-1])
        previous_histogram = float(histogram[-2]) if len(histogram) > 1 else 0.0
        
        # Determinar señal basada en MACD
        signal_type = SignalType.HOLD
        confidence = 0.0
        reasoning = f"MACD: {current_macd:.6f}, Signal: {current_signal:.6f}"
        
        # Señal de compra: MACD cruza por encima de Signal
        if (current_macd > current_signal and 
            previous_macd <= previous_signal and
            current_histogram > 0):
            
            signal_type = SignalType.BUY
            confidence = min(0.9, abs(current_histogram) / self.min_signal_strength / 10)
            reasoning = f"MACD cruza arriba Signal: {current_macd:.6f} > {current_signal:.6f}"
        
        # Señal de venta: MACD cruza por debajo de Signal
        elif (current_macd < current_signal and 
              previous_macd >= previous_signal and
              current_histogram < 0):
            
            signal_type = SignalType.SELL
            confidence = min(0.9, abs(current_histogram) / self.min_signal_strength / 10)
            reasoning = f"MACD cruza abajo Signal: {current_macd:.6f} < {current_signal:.6f}"
        
        # Señales adicionales basadas en divergencia
        elif current_histogram > previous_histogram and current_histogram > 0:
            # Histogram creciendo (momentum alcista)
            signal_type = SignalType.BUY
            confidence = 0.6
            reasoning = f"Histogram creciendo: {current_histogram:.6f} > {previous_histogram:.6f}"
            
        elif current_histogram < previous_histogram and current_histogram < 0:
            # Histogram decreciendo (momentum bajista)
            signal_type = SignalType.SELL
            confidence = 0.6
            reasoning = f"Histogram decreciendo: {current_histogram:.6f} < {previous_histogram:.6f}"
        
        # Calcular stop loss y take profit
        stop_loss = None
        take_profit = None
        
        if signal_type != SignalType.HOLD:
            if signal_type == SignalType.BUY:
                # Para compras: SL 1.5% abajo, TP 2.5% arriba
                stop_loss = market_data.current_price * 0.985
                take_profit = market_data.current_price * 1.025
            else:  # SELL
                # Para ventas: SL 1.5% arriba, TP 2.5% abajo
                stop_loss = market_data.current_price * 1.015
                take_profit = market_data.current_price * 0.975
        
        signal = TradingSignal(
            bot_name=self.config.name,
            signal_type=signal_type,
            confidence=confidence,
            entry_price=market_data.current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reasoning=reasoning,
            is_synthetic=self.config.synthetic_mode,
            metadata={
                "macd": current_macd,
                "signal": current_signal,
                "histogram": current_histogram,
                "previous_macd": previous_macd,
                "previous_signal": previous_signal,
                "previous_histogram": previous_histogram,
                "fast_period": self.fast_period,
                "slow_period": self.slow_period,
                "signal_period": self.signal_period
            }
        )
        self.last_signal = signal
        return signal
    
    def get_required_indicators(self) -> List[str]:
        """
        Retorna los indicadores que necesita este bot
        
        Returns:
            List[str]: Lista de indicadores requeridos
        """
        return ["MACD", "EMA"]
    
    def get_performance_metrics(self) -> dict:
        """
        Métricas específicas del bot MACD
        
        Returns:
            dict: Métricas de rendimiento
        """
        base_metrics = super().get_performance_metrics()
        
        # Agregar métricas específicas de MACD
        macd_metrics = {
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
            "signal_period": self.signal_period,
            "last_macd": self.last_signal.metadata.get("macd") if self.last_signal else None,
            "last_signal": self.last_signal.metadata.get("signal") if self.last_signal else None,
            "last_histogram": self.last_signal.metadata.get("histogram") if self.last_signal else None
        }
        
        base_metrics.update(macd_metrics)
        return base_metrics

# Función para crear instancia del bot con configuración personalizada
def create_macd_bot(
    name: str = "macd_bot",
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    risk_level: str = "medium"
) -> MACDBot:
    """
    Crea una instancia del bot MACD con configuración personalizada
    
    Args:
        name: Nombre del bot
        fast_period: Período rápido para EMA
        slow_period: Período lento para EMA
        signal_period: Período para línea de señal
        risk_level: Nivel de riesgo
        
    Returns:
        MACDBot: Instancia configurada del bot
    """
    config = BotConfig(
        name=name,
        description=f"Bot MACD con períodos {fast_period}/{slow_period}/{signal_period}",
        version="1.0.0",
        author="Sistema Plug-and-Play",
        symbol="DOGEUSDT",
        interval="1m",
        risk_level=risk_level,
        max_positions=3,
        position_size=1.0,
        custom_params={
            "fast_period": fast_period,
            "slow_period": slow_period,
            "signal_period": signal_period,
            "min_signal_strength": 0.0001
        }
    )
    
    return MACDBot(config)
