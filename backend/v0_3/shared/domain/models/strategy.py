#!/usr/bin/env python3
"""
Strategy Domain Models
Modelos de dominio para estrategias de trading
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from datetime import datetime
from decimal import Decimal

from .position import Money


class SignalType(Enum):
    """Tipos de señales de trading"""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class StrategyStatus(Enum):
    """Estado de ejecución de estrategia"""

    INACTIVE = "INACTIVE"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ERROR = "ERROR"
    MAINTAINING = "MAINTAINING"


class IndicatorType(Enum):
    """Tipos de indicadores técnicos"""

    SMA = "SMA"  # Simple Moving Average
    EMA = "EMA"  # Exponential Moving Average
    RSI = "RSI"  # Relative Strength Index
    MACD = "MACD"  # Moving Average Convergence Divergence
    BOLLINGER = "BOLLINGER"  # Bollinger Bands
    VOLUME = "VOLUME"  # Volume indicators
    TREND = "TREND"  # Trend indicators


class SignalStrength(Enum):
    """Fuerza de la señal"""

    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    VERY_STRONG = "VERY_STRONG"


@dataclass
class IndicatorConfig:
    """Configuración de indicador técnico"""

    name: str
    indicator_type: IndicatorType
    params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    weight: float = 1.0  # Peso para cálculo de confianza
    timeframe: str = "1m"

    def validate_config(self) -> List[str]:
        """Validar configuración del indicador"""
        errors = []

        if not self.name:
            errors.append("Indicator name is required")

        if not isinstance(self.weight, (int, float)) or self.weight <= 0:
            errors.append("Weight must be a positive number")

        # Validaciones específicas por tipo
        if self.indicator_type == IndicatorType.SMA:
            period = self.params.get("period")
            if not period or not isinstance(period, int) or period <= 0:
                errors.append("SMA period must be a positive integer")

        elif self.indicator_type == IndicatorType.RSI:
            period = self.params.get("period", 14)
            if not isinstance(period, int) or period <= 0:
                errors.append("RSI period must be a positive integer")

        elif self.indicator_type == IndicatorType.MACD:
            fast = self.params.get("fast_period", 12)
            slow = self.params.get("slow_period", 26)
            signal = self.params.get("signal_period", 9)

            if not all(isinstance(p, int) and p > 0 for p in [fast, slow, signal]):
                errors.append("MACD periods must be positive integers")

            if fast >= slow:
                errors.append("MACD fast period must be smaller than slow period")

        return errors


@dataclass
class SignalCondition:
    """Condición de señal"""

    indicator: str
    operator: str  # ">", "<", "==", ">=", "<=", "crosses_above", "crosses_below"
    value: Union[float, int]
    enabled: bool = True

    def validate_condition(self) -> bool:
        """Validar condición de señal"""
        valid_operators = (">", "<", "==", ">=", "<=", "crosses_above", "crosses_below")
        return self.operator in valid_operators


@dataclass
class SignalConfig:
    """Configuración de señal"""

    name: str
    signal_type: SignalType
    conditions: List[SignalCondition] = field(default_factory=list)
    enabled: bool = True
    logic_type: str = "AND"  # AND, OR
    min_confidence: float = 0.5  # Confianza mínima requerida
    description: str = ""

    def validate_config(self) -> List[str]:
        """Validar configuración de señal"""
        errors = []

        if not self.name:
            errors.append("Signal name is required")

        if self.logic_type not in ["AND", "OR"]:
            errors.append("Logic type must be 'AND' or 'OR'")

        if not (0.0 <= self.min_confidence <= 1.0):
            errors.append("Min confidence must be between 0.0 and 1.0")

        for condition in self.conditions:
            if not condition.validate_condition():
                errors.append(f"Invalid condition for signal: {condition}")

        return errors


@dataclass
class RiskManagement:
    """Configuración de gestión de riesgo"""

    enabled: bool = True
    max_positions: int = 3  # Máximo número de posiciones simultáneas
    position_size: float = 0.02  # 2% del balance por posición
    stop_loss_pct: float = 0.02  # 2% stop loss
    take_profit_pct: float = 0.04  # 4% take profit
    max_daily_loss: float = 0.05  # 5% pérdida máxima diaria

    def validate_config(self) -> List[str]:
        """Validar configuración de riesgo"""
        errors = []

        if self.max_positions <= 0:
            errors.append("Max positions must be positive")

        if not (0.0 < self.position_size <= 1.0):
            errors.append("Position size must be between 0 and 1")

        if not (0.0 < self.stop_loss_pct <= 1.0):
            errors.append("Stop loss percentage must be between 0 and 1")

        if not (0.0 < self.take_profit_pct <= 1.0):
            errors.append("Take profit percentage must be between 0 and 1")

        return errors


@dataclass
class StrategyConfig:
    """Configuración completa de estrategia"""

    name: str
    description: str
    version: str = "1.0.0"
    author: str = "Strategy Engine"
    symbol: str = "DOGEUSDT"
    timeframe: str = "1m"
    enabled: bool = True

    # Indicadores técnicos
    indicators: List[IndicatorConfig] = field(default_factory=list)

    # Configuración de señales
    signals: List[SignalConfig] = field(default_factory=list)

    # Gestión de riesgo
    risk_management: RiskManagement = field(default_factory=RiskManagement)

    # Parámetros personalizados
    custom_params: Dict[str, Any] = field(default_factory=dict)

    # Metadatos
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def validate_config(self) -> List[str]:
        """Validar configuración completa"""
        errors = []

        if not self.name:
            errors.append("Strategy name is required")

        if not self.symbol:
            errors.append("Symbol is required")

        # Validar indicadores
        for indicator in self.indicators:
            indicator_errors = indicator.validate_config()
            errors.extend(
                [f"Indicator {indicator.name}: {e}" for e in indicator_errors]
            )

        # Validar señales
        for signal in self.signals:
            signal_errors = signal.validate_config()
            errors.extend([f"Signal {signal.name}: {e}" for e in signal_errors])

        # Validar gestión de riesgo
        risk_errors = self.risk_management.validate_config()
        errors.extend([f"Risk: {e}" for e in risk_errors])

        return errors


@dataclass
class TradingSignal:
    """Señal de trading generada"""

    strategy_id: str
    signal_type: SignalType
    confidence: Decimal
    entry_price: Money
    stop_loss: Optional[Money] = None
    take_profit: Optional[Money] = None
    quantity: Optional[Money] = None
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    signal_strength: SignalStrength = SignalStrength.MODERATE

    def calculate_leverage_based_position(
        self, account_balance: Money, leverage: int = 1, risk_pct: float = 0.02
    ) -> Optional[Money]:
        """Calcular tamaño de posición basado en leverage y riesgo"""
        try:
            if leverage <= 0:
                leverage = 1

            # Calcular tamaño de posición
            risk_amount = account_balance.amount * Decimal(str(risk_pct))
            position_value = risk_amount * Decimal(str(leverage))

            # Convertir a cantidad de base currency
            if self.entry_price.amount > 0:
                quantity = position_value / self.entry_price.amount
                return Money(quantity, self.entry_price.currency)

            return None

        except Exception:
            return None


@dataclass
class StrategyInstance:
    """Instancia ejecutando una estrategia"""

    strategy_id: str
    config: StrategyConfig
    status: StrategyStatus = StrategyStatus.INACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    last_signal_at: Optional[datetime] = None
    signals_generated: int = 0
    signals_successful: int = 0

    # Métricas de performance
    total_pnl: Money = field(default_factory=lambda: Money.zero("USDT"))
    win_rate: float = 0.0
    max_drawdown: Money = field(default_factory=lambda: Money.zero("USDT"))
    sharpe_ratio: float = 0.0

    # Datos de mercado cache
    market_data: Dict[str, Any] = field(default_factory=dict)

    # Estados internos
    indicators: Dict[str, Any] = field(default_factory=dict)
    error_count: int = 0
    last_error: Optional[str] = None

    def update_performance_metrics(self, pnl_change: Money, success: bool) -> None:
        """Actualizar métricas de performance"""

        self.total_pnl = self.total_pnl + pnl_change

        if success:
            self.signals_successful += 1

        # Calcular win Rate
        if self.signals_generated > 0:
            self.win_rate = self.signals_successful / self.signals_generated

        # Actualizar drawdown si es mayor
        if pnl_change.amount < 0:
            current_drawdown = abs(pnl_change.amount)
            if current_drawdown > abs(self.max_drawdown.amount):
                self.max_drawdown = Money(Decimal(str(current_drawdown)), "USDT")

    def set_status(
        self, new_status: StrategyStatus, error: Optional[str] = None
    ) -> None:
        """Cambiar estado de la estrategia"""
        self.status = new_status

        if error:
            self.error_count += 1
            self.last_error = error
        else:
            # Reset error count if no error
            if new_status == StrategyStatus.ACTIVE:
                self.error_count = 0
                self.last_error = None

    def get_status_summary(self) -> Dict[str, Any]:
        """Obtener resumen del estado"""
        return {
            "strategy_id": self.strategy_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_signal_at": (
                self.last_signal_at.isoformat() if self.last_signal_at else None
            ),
            "signals_generated": self.signals_generated,
            "signals_successful": self.signals_successful,
            "win_rate": self.win_rate,
            "total_pnl": str(self.total_pnl.amount),
            "max_drawdown": str(self.max_drawdown.amount),
            "error_count": self.error_count,
            "last_error": self.last_error,
        }

    def is_healthy(self) -> bool:
        """Verificar si la estrategia está saludable"""
        return (
            self.status == StrategyStatus.ACTIVE
            and self.error_count < 5  # Menos de 5 errores
            and self.last_signal_at
            and (datetime.now() - self.last_signal_at).total_seconds()
            < 3600  # Señal en la última hora
        )


@dataclass
class SignalGenerationResult:
    """Resultado de generación de señal"""

    signal: Optional[TradingSignal]
    indicators_data: Dict[str, Any]
    conditions_evaluated: Dict[str, bool]
    reasoning_parts: List[str]
    confidence_calculation: Dict[str, float]
    errors: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
