#!/usr/bin/env python3
"""
Order Domain Model
Modelos de dominio para órdenes de trading
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from .position import OrderSide, OrderType, OrderStatus, Price, Quantity, Money


@dataclass
class OrderAggregate:
    """Agregado de dominio para Orden"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Quantity
    price: Optional[Price] = None
    stop_price: Optional[Price] = None
    status: OrderStatus = OrderStatus.PENDING
    executed_price: Optional[Price] = None
    executed_quantity: Optional[Quantity] = None
    commission: Optional[Money] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    position_id: Optional[str] = None
    client_order_id: Optional[str] = None

    def __post_init__(self):
        """Validación después de inicializar"""
        # Validar que órdenes LIMIT tengan precio
        if self.order_type == OrderType.LIMIT and not self.price:
            raise ValueError("LIMIT orders must have a price")
        
        # Validar que órdenes STOP tengan stop_price
        if self.order_type in [OrderType.STOP_MARKET, OrderType.STOP_LOSS] and not self.stop_price:
            raise ValueError("STOP orders must have a stop_price")

    def execute(self, execution_price: Price, executed_qty: Quantity, commission: Money) -> None:
        """Ejecutar orden"""
        if self.status != OrderStatus.PENDING:
            raise ValueError("Can only execute pending orders")
        
        if executed_qty.amount > self.quantity.amount:
            raise ValueError("Executed quantity cannot exceed order quantity")
        
        self.status = OrderStatus.PARTIALLY_FILLED if executed_qty.amount < self.quantity.amount else OrderStatus.FILLED
        self.executed_price = execution_price
        self.executed_quantity = executed_qty
        self.commission = commission
        self.updated_at = datetime.now()

    def cancel(self) -> None:
        """Cancelar orden"""
        if self.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
            raise ValueError(f"Cannot cancel {self.status.value} order")
        
        self.status = OrderStatus.CANCELLED
        self.updated_at = datetime.now()

    def get_filled_percentage(self) -> float:
        """Obtener porcentaje de llenado"""
        if not self.executed_quantity:
            return 0.0
        
        return float(self.executed_quantity.amount / self.quantity.amount * 100)

    def get_remaining_quantity(self) -> Quantity:
        """Obtener cantidad restante"""
        if not self.executed_quantity:
            return self.quantity
        
        remaining_amount = self.quantity.amount - self.executed_quantity.amount
        return Quantity(remaining_amount, self.quantity.unit)

    def calculate_total_executed_value(self) -> Optional[Money]:
        """Calcular valor total ejecutado"""
        if not self.executed_quantity or not self.executed_price:
            return None
        
        total_value = self.executed_quantity.amount * self.executed_price.value
        return Money(total_value, "USDT")

    def is_completely_filled(self) -> bool:
        """Verificar si está completamente llenada"""
        return self.status == OrderStatus.FILLED

    def is_stop_order(self) -> bool:
        """Verificar si es orden stop"""
        return self.order_type in [OrderType.STOP_MARKET, OrderType.STOP_LOSS]

    def is_profit_order(self) -> bool:
        """Verificar si es orden de take profit"""
        return self.order_type == OrderType.TAKE_PROFIT

    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para persistencia"""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": str(self.quantity.amount),
            "price": str(self.price.value) if self.price else None,
            "stop_price": str(self.stop_price.value) if self.stop_price else None,
            "status": self.status.value,
            "executed_price": str(self.executed_price.value) if self.executed_price else None,
            "executed_quantity": str(self.executed_quantity.amount) if self.executed_quantity else None,
            "commission": str(self.commission.amount) if self.commission else None,
            "position_id": self.position_id,
            "client_order_id": self.client_order_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OrderAggregate':
        """Crear desde diccionario de persistencia"""
        quantity = Quantity.from_float(float(data["quantity"]))
        
        price = None
        if data.get("price"):
            price = Price.from_float(float(data["price"]), data["symbol"])
        
        stop_price = None
        if data.get("stop_price"):
            stop_price = Price.from_float(float(data["stop_price"]), data["symbol"])

        executed_price = None
        if data.get("executed_price"):
            executed_price = Price.from_float(float(data["executed_price"]), data["symbol"])

        executed_quantity = None
        if data.get("executed_quantity"):
            executed_quantity = Quantity.from_float(float(data["executed_quantity"]))

        commission = None
        if data.get("commission"):
            commission = Money.from_float(float(data["commission"]))

        return cls(
            order_id=data["order_id"],
            symbol=data["symbol"],
            side=OrderSide(data["side"]),
            order_type=OrderType(data["order_type"]),
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            status=OrderStatus(data["status"]),
            executed_price=executed_price,
            executed_quantity=executed_quantity,
            commission=commission,
            position_id=data.get("position_id"),
            client_order_id=data.get("client_order_id"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


class OrderFactory:
    """Factory para crear órdenes"""
    
    @staticmethod
    def create_market_order(
        symbol: str, 
        side: OrderSide, 
        quantity: float,
        client_order_id: Optional[str] = None
    ) -> OrderAggregate:
        """Crear orden market"""
        return OrderAggregate(
            order_id=f"market_{datetime.now().timestamp()}",
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=Quantity.from_float(quantity),
            client_order_id=client_order_id
        )

    @staticmethod
    def create_limit_order(
        symbol: str, 
        side: OrderSide, 
        quantity: float, 
        price: float,
        client_order_id: Optional[str] = None
    ) -> OrderAggregate:
        """Crear orden limit"""
        return OrderAggregate(
            order_id=f"limit_{datetime.now().timestamp()}",
            symbol=symbol,
            side=side,
            order_type=OrderType.LIMIT,
            quantity=Quantity.from_float(quantity),
            price=Price.from_float(price, symbol),
            client_order_id=client_order_id
        )

    @staticmethod
    def create_stop_loss_order(
        symbol: str, 
        side: OrderSide, 
        quantity: float, 
        stop_price: float,
        client_order_id: Optional[str] = None
    ) -> OrderAggregate:
        """Crear orden stop loss"""
        return OrderAggregate(
            order_id=f"stop_{datetime.now().timestamp()}",
            symbol=symbol,
            side=side,
            order_type=OrderType.STOP_MARKET,
            quantity=Quantity.from_float(quantity),
            stop_price=Price.from_float(stop_price, symbol),
            client_order_id=client_order_id
        )

    @staticmethod
    def create_take_profit_order(
        symbol: str, 
        side: OrderSide, 
        quantity: float, 
        price: float,
        client_order_id: Optional[str] = None
    ) -> OrderAggregate:
        """Crear orden take profit"""
        return OrderAggregate(
            order_id=f"tp_{datetime.now().timestamp()}",
            symbol=symbol,
            side=side,
            order_type=OrderType.TAKE_PROFIT,
            quantity=Quantity.from_float(quantity),
            price=Price.from_float(price, symbol),
            client_order_id=client_order_id
        )
