#!/usr/bin/env python3
"""
Strategy Engine Models
Data models for strategy configuration and execution
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from datetime import datetime


class SignalType(Enum):
    """Trading signal types"""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class StrategyStatus(Enum):
    """Strategy execution status"""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PAUSED = "PAUSED"
    ERROR = "ERROR"


@dataclass
class IndicatorConfig:
    """Configuration for a technical indicator"""

    name: str
    type: str  # sma, rsi, macd, volume_ma, etc.
    params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class SignalCondition:
    """Condition for generating a trading signal"""

    indicator: str  # Reference to indicator name
    operator: str  # >, <, >=, <=, ==, !=, cross_above, cross_below
    value: Union[float, str]  # Threshold value or reference to another indicator
    logic: str = "AND"  # AND, OR for combining conditions


@dataclass
class SignalConfig:
    """Configuration for trading signals"""

    signal_type: SignalType
    conditions: List[SignalCondition]
    confidence: float = 0.5  # Minimum confidence threshold
    enabled: bool = True


@dataclass
class RiskManagement:
    """Risk management configuration"""

    stop_loss_pct: float = 0.02  # 2% stop loss
    take_profit_pct: float = 0.03  # 3% take profit
    max_positions: int = 3
    position_size: float = 0.5  # Percentage of available balance
    max_daily_loss: float = 0.05  # 5% max daily loss
    enabled: bool = True


@dataclass
class StrategyConfig:
    """Complete strategy configuration"""

    name: str
    description: str
    version: str = "1.0.0"
    author: str = "Strategy Engine"
    symbol: str = "DOGEUSDT"
    interval: str = "1m"
    enabled: bool = True

    # Technical indicators
    indicators: List[IndicatorConfig] = field(default_factory=list)

    # Signal generation
    signals: List[SignalConfig] = field(default_factory=list)

    # Risk management
    risk_management: RiskManagement = field(default_factory=RiskManagement)

    # Custom parameters
    custom_params: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class StrategySignal:
    """Generated trading signal"""

    strategy_name: str
    signal_type: SignalType
    confidence: float
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class StrategyInstance:
    """Running strategy instance"""

    config: StrategyConfig
    status: StrategyStatus
    last_signal: Optional[StrategySignal] = None
    positions: List[Dict[str, Any]] = field(default_factory=list)
    performance: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    last_updated: datetime = field(default_factory=datetime.now)
