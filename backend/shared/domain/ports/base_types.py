#!/usr/bin/env python3
"""
Base Types para Ports
Tipos base compartidos entre todos los dominios
"""

from enum import Enum
from typing import Optional, Dict, Any, List, TypeVar, Generic
from datetime import datetime
from dataclasses import dataclass


class OrderSide(Enum):
    """Lados de orden"""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Tipos de orden"""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


class OrderStatus(Enum):
    """Estados de orden"""

    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    REJECTED = "REJECTED"


class PositionStatus(Enum):
    """Estados de posición"""

    OPEN = "open"
    CLOSED = "closed"
    STOPPED = "stopped"
    PROFITED = "profited"


@dataclass
class OrderResult:
    """Resultado de ejecución de orden"""

    success: bool
    order_id: Optional[str] = None
    message: Optional[str] = None
    executed_price: Optional[float] = None
    executed_quantity: Optional[float] = None
    commission: Optional[float] = None
    timestamp: str = datetime.now().isoformat()


@dataclass
class Position:
    """Modelo de dominio para posición"""

    position_id: str
    symbol: str
    side: OrderSide
    quantity: float
    entry_price: float
    leverage: int = 1

    # Risk Management
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None

    # Status
    status: PositionStatus = PositionStatus.OPEN
    pnl: float = 0.0

    # Timestamps
    created_at: str = datetime.now().isoformat()
    updated_at: str = datetime.now().isoformat()
    closed_at: Optional[str] = None

    def calculate_pnl(self, current_price: float) -> float:
        """Calcular P&L basado en precio actual"""
        if self.side == OrderSide.BUY:
            return (current_price - self.entry_price) * self.quantity
        else:  # SELL
            return (self.entry_price - current_price) * self.quantity


@dataclass
class Order:
    """Modelo de dominio para orden"""

    order_id: str
    position_id: Optional[str]
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    executed_price: Optional[float] = None
    executed_quantity: Optional[float] = None
    commission: Optional[float] = None

    # Metadata
    created_at: str = datetime.now().isoformat()
    updated_at: str = datetime.now().isoformat()


@dataclass
class MarketData:
    """Datos de mercado"""

    symbol: str
    current_price: float
    volume: float
    bid: float
    ask: float
    timestamp: str = datetime.now().isoformat()


@dataclass
class Candlestick:
    """Datos de vela"""

    symbol: str
    interval: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: str
    closed: bool = False


# Generic types para repositorios
T = TypeVar("T")


class RepositoryResult(Generic[T]):
    """Resultado genérico de operaciones de repositorio"""

    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    count: int = 0
