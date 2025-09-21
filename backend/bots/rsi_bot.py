#!/usr/bin/env python3
"""
Bot de trading basado en RSI (Relative Strength Index)
Ejemplo de bot plug-and-play
"""

import numpy as np
from typing import List
from bot_interface import BaseBot, BotConfig, MarketData, TradingSignal, SignalType

class RSIBot(BaseBot):
    """
    Bot que usa RSI para generar señales de trading
    """
    
    def __init__(self, config: BotConfig):
        super().__init__(config)
        
        # Parámetros específicos del bot RSI
        self.rsi_period = config.custom_params.get('rsi_period', 14) if config.custom_params else 14
        self.oversold_threshold = config.custom_params.get('oversold_threshold', 30) if config.custom_params else 30
        self.overbought_threshold = config.custom_params.get('overbought_threshold', 70) if config.custom_params else 70
        self.confirmation_periods = config.custom_params.get('confirmation_periods', 2) if config.custom_params else 2
        
        self.logger.info(f"📊 RSI Bot configurado: período={self.rsi_period}, oversold={self.oversold_threshold}, overbought={self.overbought_threshold}")
    
    def calculate_rsi(self, prices: List[float], period: int = None) -> float:
        """
        Calcula el RSI para una serie de precios
        
        Args:
            prices: Lista de precios de cierre
            period: Período para el cálculo (opcional)
            
        Returns:
            float: Valor del RSI
        """
        if period is None:
            period = self.rsi_period
        
        if len(prices) < period + 1:
            return 50.0  # Valor neutral si no hay suficientes datos
        
        # Calcular cambios de precio
        deltas = np.diff(prices[-period-1:])
        
        # Separar ganancias y pérdidas
        gains = np.where(deltas > 0, deltas, 0).astype(float)
        losses = np.where(deltas < 0, -deltas, 0).astype(float)
        
        # Calcular promedios - asegurar que son escalares
        avg_gains = float(np.mean(gains))
        avg_losses = float(np.mean(losses))
        
        # Evitar división por cero
        if avg_losses == 0:
            return 100.0
        
        # Calcular RS y RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def analyze_market(self, market_data: MarketData) -> TradingSignal:
        """
        Analiza el mercado usando RSI y genera una señal
        
        Args:
            market_data: Datos de mercado actuales
            
        Returns:
            TradingSignal: Señal generada
        """
        if len(market_data.closes) < self.rsi_period + 1:
            return TradingSignal(
                bot_name=self.config.name,
                signal_type=SignalType.HOLD,
                confidence=0.0,
                entry_price=market_data.current_price,
                reasoning="Datos insuficientes para calcular RSI",
                is_synthetic=self.config.synthetic_mode,
                metadata={"rsi": None, "data_points": len(market_data.closes)}
            )
        
        # Calcular RSI actual
        current_rsi = self.calculate_rsi(market_data.closes)
        
        # Calcular RSI anterior para confirmación
        previous_rsi = self.calculate_rsi(market_data.closes[:-1]) if len(market_data.closes) > self.rsi_period + 1 else current_rsi
        
        # Determinar señal basada en RSI
        signal_type = SignalType.HOLD
        confidence = 0.0
        reasoning = f"RSI: {current_rsi:.2f}"
        
        # Señal de compra: RSI sale de zona de sobreventa
        if (current_rsi > self.oversold_threshold and 
            previous_rsi <= self.oversold_threshold and
            current_rsi < 50):  # Aún no sobrecomprado
            
            signal_type = SignalType.BUY
            confidence = min(0.9, (50 - current_rsi) / 20)  # Mayor confianza cuanto más cerca de 50
            reasoning = f"RSI sale de sobreventa: {current_rsi:.2f} (anterior: {previous_rsi:.2f})"
        
        # Señal de venta: RSI sale de zona de sobrecompra
        elif (current_rsi < self.overbought_threshold and 
              previous_rsi >= self.overbought_threshold and
              current_rsi > 50):  # Aún no sobrevendido
            
            signal_type = SignalType.SELL
            confidence = min(0.9, (current_rsi - 50) / 20)  # Mayor confianza cuanto más cerca de 50
            reasoning = f"RSI sale de sobrecompra: {current_rsi:.2f} (anterior: {previous_rsi:.2f})"
        
        # Señales adicionales basadas en niveles extremos
        elif current_rsi < 20:  # RSI muy bajo
            signal_type = SignalType.BUY
            confidence = 0.7
            reasoning = f"RSI extremadamente bajo: {current_rsi:.2f}"
            
        elif current_rsi > 80:  # RSI muy alto
            signal_type = SignalType.SELL
            confidence = 0.7
            reasoning = f"RSI extremadamente alto: {current_rsi:.2f}"
        
        # Calcular stop loss y take profit
        stop_loss = None
        take_profit = None
        
        if signal_type != SignalType.HOLD:
            if signal_type == SignalType.BUY:
                # Para compras: SL 2% abajo, TP 3% arriba
                stop_loss = market_data.current_price * 0.98
                take_profit = market_data.current_price * 1.03
            else:  # SELL
                # Para ventas: SL 2% arriba, TP 3% abajo
                stop_loss = market_data.current_price * 1.02
                take_profit = market_data.current_price * 0.97
        
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
                "rsi": current_rsi,
                "previous_rsi": previous_rsi,
                "oversold_threshold": self.oversold_threshold,
                "overbought_threshold": self.overbought_threshold,
                "data_points": len(market_data.closes)
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
        return ["RSI"]
    
    def get_performance_metrics(self) -> dict:
        """
        Métricas específicas del bot RSI
        
        Returns:
            dict: Métricas de rendimiento
        """
        base_metrics = super().get_performance_metrics()
        
        # Agregar métricas específicas de RSI
        rsi_metrics = {
            "rsi_period": self.rsi_period,
            "oversold_threshold": self.oversold_threshold,
            "overbought_threshold": self.overbought_threshold,
            "last_rsi": self.last_signal.metadata.get("rsi") if self.last_signal else None
        }
        
        base_metrics.update(rsi_metrics)
        return base_metrics

# Función para crear instancia del bot con configuración personalizada
def create_rsi_bot(
    name: str = "rsi_bot",
    rsi_period: int = 14,
    oversold_threshold: int = 30,
    overbought_threshold: int = 70,
    risk_level: str = "medium"
) -> RSIBot:
    """
    Crea una instancia del bot RSI con configuración personalizada
    
    Args:
        name: Nombre del bot
        rsi_period: Período para el cálculo del RSI
        oversold_threshold: Umbral de sobreventa
        overbought_threshold: Umbral de sobrecompra
        risk_level: Nivel de riesgo
        
    Returns:
        RSIBot: Instancia configurada del bot
    """
    config = BotConfig(
        name=name,
        description=f"Bot RSI con período {rsi_period}, oversold {oversold_threshold}, overbought {overbought_threshold}",
        version="1.0.0",
        author="Sistema Plug-and-Play",
        symbol="DOGEUSDT",
        interval="1m",
        risk_level=risk_level,
        max_positions=3,
        position_size=1.0,
        custom_params={
            "rsi_period": rsi_period,
            "oversold_threshold": oversold_threshold,
            "overbought_threshold": overbought_threshold
        }
    )
    
    return RSIBot(config)
