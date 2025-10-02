#!/usr/bin/env python3
"""
Position Domain Model
Modelos de dominio para posiciones y trading
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from decimal import Decimal


class OrderSide(Enum):
    """Lado de la orden"""
    BUY = "BUY"
    SELL = "SELL"

    def opposite(self) -> 'OrderSide':
        """Obtener lado opuesto"""
        return OrderSide.SELL if self == OrderSide.BUY else OrderSide.BUY


class OrderType(Enum):
    """Tipo de orden"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


class OrderStatus(Enum):
    """Estado de orden"""
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    REJECTED = "REJECTED"


class PositionStatus(Enum):
    """Estado de posición"""
    OPEN = "open"
    CLOSED = "closed"
    STOPPED = "stopped"
    PROFITED = "profited"


@dataclass
class Money:
    """Value Object para representar dinero"""
    amount: Decimal
    currency: str = "USDT"

    def __post_init__(self):
        """Validar después de inicializar"""
        if isinstance(self.amount, (int, float)):
            self.amount = Decimal(str(self.amount))
        
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")

    def __add__(self, other: 'Money') -> 'Money':
        """Sumar money del mismo tipo"""
        if not isinstance(other, Money):
            raise TypeError("Can only add Money to Money")
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} to {other.currency}")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: 'Money') -> 'Money':
        """Restar money del mismo tipo"""
        if not isinstance(other, Money):
            raise TypeError("Can only subtract Money from Money")
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {other.currency} from {self.currency}")
        result = self.amount - other.amount
        if result < 0:
            return Money(Decimal('0'), self.currency)
        return Money(result, self.currency)

    def __mul__(self, multiplier: float) -> 'Money':
        """Multiplicar por un escalar"""
        return Money(self.amount * Decimal(str(multiplier)), self.currency)

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"

    @classmethod
    def zero(cls, currency: str = "USDT") -> 'Money':
        """Crear dinero en cero"""
        return cls(Decimal('0'), currency)

    @classmethod
    def from_float(cls, amount: float, currency: str = "USDT") -> 'Money':
        """Crear desde float"""
        return cls(Decimal(str(amount)), currency)


@dataclass
class Price:
    """Value Object para representar precios"""
    value: Decimal
    symbol: str

    def __post_init__(self):
        """Validar después de inicializar"""
        if isinstance(self.value, (int, float)):
            self.value = Decimal(str(self.value))
        
        if self.value <= 0:
            raise ValueError("Price must be positive")

    def __str__(self) -> str:
        return f"{self.value} ({self.symbol})"

    @classmethod
    def from_float(cls, value: float, symbol: str) -> 'Price':
        """Crear desde float"""
        return cls(Decimal(str(value)), symbol)


@dataclass
class Quantity:
    """Value Object para representar cantidades"""
    amount: Decimal
    unit: str = "units"

    def __post_init__(self):
        """Validar después de inicializar"""
        if isinstance(self.amount, (int, float)):
            self.amount = Decimal(str(self.amount))
        
        if self.amount <= 0:
            raise ValueError("Quantity must be positive")

    def __str__(self) -> str:
        return f"{self.amount} {self.unit}"

    @classmethod
    def from_float(cls, amount: float, unit: str = "units") -> 'Quantity':
        """Crear desde float"""
        return cls(Decimal(str(amount)), unit)


@dataclass
class PositionAggregate:
    """Agregado de dominio para Posición"""
    position_id: str
    symbol: str
    side: OrderSide
    quantity: Quantity
    entry_price: Price
    leverage: int = 1
    
    # Risk Management
    stop_loss_price: Optional[Price] = None
    take_profit_price: Optional[Price] = None
    
    # Status
    status: PositionStatus = PositionStatus.OPEN
    pnl: Money = field(default_factory=lambda: Money.zero("USDT"))
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    closed_at: Optional[datetime] = None

    def calculate_unrealized_pnl(self, current_price: Price) -> Money:
        """Calcular P&L no realizado"""
        if self.status != PositionStatus.OPEN:
            return Money.zero("USDT")
        
        price_diff = Decimal('0')
        if self.side == OrderSide.BUY:
            # Long position: profit when current price > entry price
            price_diff = current_price.value - self.entry_price.value
        else:  # OrderSide.SELL
            # Short position: profit when current price < entry price
            price_diff = self.entry_price.value - current_price.value
        
        # Calculate absolute P&L amount
        pnl_amount = price_diff * self.quantity.amount
        
        return Money(pnl_amount, "USDT")

    def update_pnl(self, current_price: Price) -> None:
        """Actualizar P&L con precio actual"""
        if self.status == PositionStatus.OPEN:
            self.pnl = self.calculate_unrealized_pnl(current_price)
            self.updated_at = datetime.now()

    def set_stop_loss(self, stop_price: Price) -> None:
        """Establecer stop loss"""
        if self.status != PositionStatus.OPEN:
            raise ValueError("Can only set stop loss on open positions")
        
        # Validar que stop loss sea en dirección de pérdida
        if self.side == OrderSide.BUY and stop_price.value >= self.entry_price.value:
            raise ValueError("Stop loss for long position must be below entry price")
        elif self.side == OrderSide.SELL and stop_price.value <= self.entry_price.value:
            raise ValueError("Stop loss for short position must be above entry price")
        
        self.stop_loss_price = stop_price
        self.updated_at = datetime.now()

    def set_take_profit(self, tp_price: Price) -> None:
        """Establecer take profit"""
        if self.status != PositionStatus.OPEN:
            raise ValueError("Can only set take profit on open positions")
        
        # Validar que take profit sea en dirección de ganancia
        if self.side == OrderSide.BUY and tp_price.value <= self.entry_price.value:
            raise ValueError("Take profit for long position must be above entry price")
        elif self.side == OrderSide.SELL and tp_price.value >= self.entry_price.value:
            raise ValueError("Take profit for short position must be below entry price")
        
        self.take_profit_price = tp_price
        self.updated_at = datetime.now()

    def close_position(self, exit_price: Price, reason: str = "manual") -> Money:
        """Cerrar posición y calcular P&L final"""
        if self.status != PositionStatus.OPEN:
            raise ValueError("Can only close open positions")
        
        # Calcular P&L final
        final_pnl = self.calculate_unrealized_pnl(exit_price)
        
        # Actualizar estado
        self.status = PositionStatus.CLOSED
        self.pnl = final_pnl
        self.closed_at = datetime.now()
        self.updated_at = datetime.now()
        
        return final_pnl

    def check_risk_triggers(self, current_price: Price) -> Optional[str]:
        """Verificar si se activaron triggers de riesgo"""
        if self.status != PositionStatus.OPEN:
            return None
        
        # Trigger stop loss
        if self.stop_loss_price:
            if ((self.side == OrderSide.BUY and current_price.value <= self.stop_loss_price.value) or
                (self.side == OrderSide.SELL and current_price.value >= self.stop_loss_price.value)):
                return "STOP_LOSS_TRIGGERED"
        
        # Trigger take profit
        if self.take_profit_price:
            if ((self.side == OrderSide.BUY and current_price.value >= self.take_profit_price.value) or
                (self.side == OrderSide.SELL and current_price.value <= self.take_profit_price.value)):
                return "TAKE_PROFIT_TRIGGERED"
        
        return None

    def get_position_value(self, current_price: Price) -> Money:
        """Obtener valor total de la posición"""
        position_value = current_price.value * self.quantity.amount
        return Money(position_value, "USDT")

    def get_margin_required(self) -> Money:
        """Calcular margen requerido"""
        position_value = self.entry_price.value * self.quantity.amount
        margin_amount = position_value / Decimal(str(self.leverage))
        return Money(margin_amount, "USDT")

    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para persistencia"""
        return {
            "position_id": self.position_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": str(self.quantity.amount),
            "entry_price": str(self.entry_price.value),
            "leverage": self.leverage,
            "stop_loss_price": str(self.stop_loss_price.value) if self.stop_loss_price else None,
            "take_profit_price": str(self.take_profit_price.value) if self.take_profit_price else None,
            "status": self.status.value,
            "pnl": str(self.pnl.amount),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PositionAggregate':
        """Crear desde diccionario de persistencia"""
        quantity = Quantity.from_float(float(data["quantity"]))
        entry_price = Price.from_float(float(data["entry_price"]), data["symbol"])
        
        stop_loss_price = None
        if data.get("stop_loss_price"):
            stop_loss_price = Price.from_float(float(data["stop_loss_price"]), data["symbol"])
        
        take_profit_price = None
        if data.get("take_profit_price"):
            take_profit_price = Price.from_float(float(data["take_profit_price"]), data["symbol"])

        position = cls(
            position_id=data["position_id"],
            symbol=data["symbol"],
            side=OrderSide(data["side"]),
            quantity=quantity,
            entry_price=entry_price,
            leverage=data.get("leverage", 1),
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            status=PositionStatus(data["status"]),
            pnl=Money.from_float(float(data["pnl"])),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            closed_at=datetime.fromisoformat(data["closed_at"]) if data.get("closed_at") else None,
        )
        
        return position
