#!/usr/bin/env python3
"""
Bot simple de ejemplo para testing con lógica completa de trading
"""

from typing import List
from bot_interface import BaseBot, BotConfig, MarketData, TradingSignal, SignalType

class SimpleBot(BaseBot):
    """
    Bot simple que genera señales BUY y SELL con gestión básica de riesgo
    """
    
    def __init__(self, config: BotConfig):
        super().__init__(config)
        
        # Parámetros de trading
        self.lookback_periods = 3  # Períodos para analizar tendencia
        self.min_price_change = 0.001  # Cambio mínimo de precio (0.1%)
        self.stop_loss_pct = 0.02  # Stop Loss: 2%
        self.take_profit_pct = 0.03  # Take Profit: 3%
        self.binance_fee_rate = 0.001  # Comisión de Binance: 0.1%
        
        self.logger.info(f"📊 Simple Bot configurado: {config.name}")
        self.logger.info(f"   📈 Lookback: {self.lookback_periods} períodos")
        self.logger.info(f"   📊 Min change: {self.min_price_change*100:.1f}%")
        self.logger.info(f"   🛑 Stop Loss: {self.stop_loss_pct*100:.1f}%")
        self.logger.info(f"   🎯 Take Profit: {self.take_profit_pct*100:.1f}%")
        self.logger.info(f"   💰 Comisión Binance: {self.binance_fee_rate*100:.1f}%")
    
    def analyze_market(self, market_data: MarketData) -> TradingSignal:
        """
        Analiza el mercado y genera una señal con gestión de riesgo
        
        Args:
            market_data: Datos de mercado actuales
            
        Returns:
            TradingSignal: Señal generada
        """
        current_price = market_data.current_price
        
        # Verificar datos suficientes
        if len(market_data.closes) < self.lookback_periods:
            return TradingSignal(
                bot_name=self.config.name,
                signal_type=SignalType.HOLD,
                confidence=0.0,
                entry_price=current_price,
                reasoning="Datos insuficientes",
                metadata={
                    "data_points": len(market_data.closes),
                    "current_price": current_price
                }
            )
        
        # Analizar tendencia de los últimos períodos
        recent_closes = market_data.closes[-self.lookback_periods:]
        price_change = (recent_closes[-1] - recent_closes[0]) / recent_closes[0]
        
        # Determinar señal basada en tendencia
        signal_type = SignalType.HOLD
        confidence = 0.0
        reasoning = f"Precio estable: {current_price:.5f}"
        
        # Señal de compra: tendencia alcista significativa
        if price_change > self.min_price_change:
            signal_type = SignalType.BUY
            confidence = min(0.8, abs(price_change) / self.min_price_change * 0.3)
            reasoning = f"Tendencia alcista: {price_change*100:.2f}% ({recent_closes[0]:.5f} → {recent_closes[-1]:.5f})"
        
        # Señal de venta: tendencia bajista significativa
        elif price_change < -self.min_price_change:
            signal_type = SignalType.SELL
            confidence = min(0.8, abs(price_change) / self.min_price_change * 0.3)
            reasoning = f"Tendencia bajista: {price_change*100:.2f}% ({recent_closes[0]:.5f} → {recent_closes[-1]:.5f})"
        
        # Calcular stop loss y take profit
        stop_loss = None
        take_profit = None
        
        if signal_type != SignalType.HOLD:
            if signal_type == SignalType.BUY:
                # Para compras: SL abajo, TP arriba
                stop_loss = current_price * (1 - self.stop_loss_pct)
                take_profit = current_price * (1 + self.take_profit_pct)
            else:  # SELL
                # Para ventas: SL arriba, TP abajo
                stop_loss = current_price * (1 + self.stop_loss_pct)
                take_profit = current_price * (1 - self.take_profit_pct)
        
        return TradingSignal(
            bot_name=self.config.name,
            signal_type=signal_type,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reasoning=reasoning,
            metadata={
                "data_points": len(market_data.closes),
                "current_price": current_price,
                "price_change_pct": price_change * 100,
                "lookback_periods": self.lookback_periods,
                "min_price_change": self.min_price_change,
                "stop_loss_pct": self.stop_loss_pct,
                "take_profit_pct": self.take_profit_pct,
                "binance_fee_rate": self.binance_fee_rate
            }
        )
    
    def get_required_indicators(self) -> List[str]:
        """
        Retorna los indicadores que necesita este bot
        
        Returns:
            List[str]: Lista de indicadores requeridos
        """
        return ["Price"]
    
    def get_performance_metrics(self) -> dict:
        """
        Métricas específicas del bot simple
        
        Returns:
            dict: Métricas de rendimiento
        """
        base_metrics = super().get_performance_metrics()
        
        # Agregar métricas específicas
        simple_metrics = {
            "lookback_periods": self.lookback_periods,
            "min_price_change": self.min_price_change,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "binance_fee_rate": self.binance_fee_rate,
            "last_price_change": self.last_signal.metadata.get("price_change_pct") if self.last_signal else None
        }
        
        base_metrics.update(simple_metrics)
        return base_metrics

# Función para crear instancia del bot
def create_simple_bot(name: str = "simple_bot") -> SimpleBot:
    """
    Crea una instancia del bot simple
    
    Args:
        name: Nombre del bot
        
    Returns:
        SimpleBot: Instancia configurada del bot
    """
    config = BotConfig(
        name=name,
        description="Bot simple con lógica completa de trading (BUY/SELL, SL/TP, comisiones)",
        version="2.0.0",
        author="Sistema Plug-and-Play",
        symbol="DOGEUSDT",
        interval="1m",
        risk_level="medium",
        max_positions=3,
        position_size=0.5
    )
    
    return SimpleBot(config)
