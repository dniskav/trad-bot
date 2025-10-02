#!/usr/bin/env python3
"""
Strategy Domain Ports
Interfaces para el dominio de estrategias
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from .base_types import MarketData
from enum import Enum


class StrategyStatus(Enum):
    """Estados de estrategia"""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PAUSED = "PAUSED"
    ERROR = "ERROR"


class SignalType(Enum):
    """Tipos de señal de trading"""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@abstractmethod
class Signal:
    """Señal de trading generada"""

    def __init__(
        self,
        signal_type: SignalType,
        confidence: float,
        strategy_name: str,
        metadata: Dict[str, Any],
    ):
        self.signal_type = signal_type
        self.confidence = confidence
        self.strategy_name = strategy_name
        self.metadata = metadata
        self.timestamp = datetime.now().isoformat()


class IStrategyEngine(ABC):
    """Motor de estrategias"""

    @abstractmethod
    async def start_strategy(self, strategy_id: str) -> bool:
        """Iniciar estrategia"""
        pass

    @abstractmethod
    async def stop_strategy(self, strategy_id: str) -> bool:
        """Parar estrategia"""
        pass

    @abstractmethod
    async def pause_strategy(self, strategy_id: str) -> bool:
        """Pausar estrategia"""
        pass

    @abstractmethod
    async def resume_strategy(self, strategy_id: str) -> bool:
        """Reanudar estrategia"""
        pass

    @abstractmethod
    async def evaluate_signals(self, market_data: MarketData) -> List[Signal]:
        """Evaluar señales basadas en datos de mercado"""
        pass

    @abstractmethod
    async def get_strategy_status(self, strategy_id: str) -> Optional[StrategyStatus]:
        """Obtener estado de estrategia"""
        pass

    @abstractmethod
    async def reload_strategy_config(self, strategy_id: str) -> bool:
        """Recargar configuración de estrategia"""
        pass


class IIndicatorService(ABC):
    """Servicio de indicadores técnicos"""

    @abstractmethod
    async def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calcular RSI (Relative Strength Index)"""
        pass

    @abstractmethod
    async def calculate_sma(self, prices: List[float], period: int) -> float:
        """Calcular SMA (Simple Moving Average)"""
        pass

    @abstractmethod
    async def calculate_ema(self, prices: List[float], period: int) -> float:
        """Calcular EMA (Exponential Moving Average)"""
        pass

    @abstractmethod
    async def calculate_macd(
        self,
        prices: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> Dict[str, float]:
        """Calcular MACD"""
        pass

    @abstractmethod
    async def calculate_bollinger_bands(
        self, prices: List[float], period: int = 20, std_dev: float = 2.0
    ) -> Dict[str, float]:
        """Calcular Bandas de Bollinger"""
        pass


class ISignalEvaluator(ABC):
    """Evaluador de señales de trading"""

    @abstractmethod
    async def evaluate_buy_conditions(
        self, market_data: MarketData, strategy_config: Dict[str, Any]
    ) -> Optional[Signal]:
        """Evaluar condiciones de compra"""
        pass

    @abstractmethod
    async def evaluate_sell_conditions(
        self, market_data: MarketData, strategy_config: Dict[str, Any]
    ) -> Optional[Signal]:
        """Evaluar condiciones de venta"""
        pass

    @abstractmethod
    async def evaluate_hold_conditions(
        self, market_data: MarketData, strategy_config: Dict[str, Any]
    ) -> Optional[Signal]:
        """Evaluar condiciones de mantener posición"""
        pass

    @abstractmethod
    async def validate_signal_strength(
        self, signal: Signal, market_data: MarketData
    ) -> bool:
        """Validar fortaleza de señal"""
        pass


class IStrategyRepository(ABC):
    """Repositorio para estrategias"""

    @abstractmethod
    async def load_strategy_config(
        self, strategy_name: str
    ) -> Optional[Dict[str, Any]]:
        """Cargar configuración de estrategia"""
        pass

    @abstractmethod
    async def save_strategy_config(
        self, strategy_name: str, config: Dict[str, Any]
    ) -> bool:
        """Guardar configuración de estrategia"""
        pass

    @abstractmethod
    async def get_available_strategies(self) -> List[str]:
        """Obtener estrategias disponibles"""
        pass

    @abstractmethod
    async def delete_strategy_config(self, strategy_name: str) -> bool:
        """Eliminar configuración de estrategia"""
        pass


class IRiskManager(ABC):
    """Gestor de riesgo para estrategias"""

    @abstractmethod
    async def validate_position_size(
        self, strategy_id: str, symbol: str, quantity: float, account_balance: float
    ) -> bool:
        """Validar tamaño de posición"""
        pass

    @abstractmethod
    async def calculate_stop_loss(
        self, entry_price: float, strategy_config: Dict[str, Any]
    ) -> float:
        """Calcular stop loss basado en configuración"""
        pass

    @abstractmethod
    async def calculate_take_profit(
        self, entry_price: float, strategy_config: Dict[str, Any]
    ) -> float:
        """Calcular take profit basado en configuración"""
        pass

    @abstractmethod
    async def check_max_positions_limit(self, strategy_id: str) -> bool:
        """Verificar límite de posiciones máximas"""
        pass

    @abstractmethod
    async def check_daily_loss_limit(self, strategy_id: str, daily_pnl: float) -> bool:
        """Verificar límite de pérdida diaria"""
        pass


class IStrategyPerformanceTracker(ABC):
    """Tracker de performance de estrategias"""

    @abstractmethod
    async def record_strategy_execution(
        self, strategy_id: str, signal: Signal, executed: bool, result: Dict[str, Any]
    ) -> None:
        """Registrar ejecución de estrategia"""
        pass

    @abstractmethod
    async def get_strategy_performance(self, strategy_id: str) -> Dict[str, Any]:
        """Obtener performance de estrategia"""
        pass

    @abstractmethod
    async def get_strategy_statistics(
        self, strategy_id: str, days: int = 30
    ) -> Dict[str, Any]:
        """Obtener estadísticas de estrategia"""
        pass

    @abstractmethod
    async def reset_strategy_performance(self, strategy_id: str) -> bool:
        """Resetear performance de estrategia"""
        pass
