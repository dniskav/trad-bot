#!/usr/bin/env python3
"""
Trading Domain Ports
Interfaces para el dominio de trading (Ports & Adapters pattern)
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from .base_types import Position, Order, OrderResult, MarketData


class IPositionRepository(ABC):
    """Repositorio para gestión de posiciones"""

    @abstractmethod
    async def save_position(self, position: Position) -> None:
        """Guardar una nueva posición"""
        pass

    @abstractmethod
    async def get_position(self, position_id: str) -> Optional[Position]:
        """Obtener posición por ID"""
        pass

    @abstractmethod
    async def get_active_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Obtener posiciones activas, opcionalmente filtradas por símbolo"""
        pass

    @abstractmethod
    async def update_position(self, position: Position) -> None:
        """Actualizar posición existente"""
        pass

    @abstractmethod
    async def close_position(self, position_id: str, exit_price: float, reason: str = "manual") -> None:
        """Cerrar posición"""
        pass


class IOrderRepository(ABC):
    """Repositorio para gestión de órdenes"""

    @abstractmethod
    async def save_order(self, order: Order) -> None:
        """Guardar una nueva orden"""
        pass

    @abstractmethod
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Obtener orden por ID"""
        pass

    @abstractmethod
    async def get_orders_by_position(self, position_id: str) -> List[Order]:
        """Obtener todas las órdenes de una posición"""
        pass

    @abstractmethod
    async def get_active_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Obtener órdenes activas, opcionalmente filtradas por símbolo"""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancelar orden"""
        pass


class IMarketDataProvider(ABC):
    """Proveedor de datos de mercado"""

    @abstractmethod
    async def get_current_price(self, symbol: str) -> float:
        """Obtener precio actual del símbolo"""
        pass

    @abstractmethod
    async def get_candlestick_data(self, symbol: str, interval: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtener datos de velas para análisis técnico"""
        pass

    @abstractmethod
    async def get_ticker_data(self, symbol: str) -> Dict[str, Any]:
        """Obtener datos de ticker (precio bid/ask/volumen)"""
        pass


class ITradingExecutor(ABC):
    """Ejecutor de operaciones de trading"""

    @abstractmethod
    async def execute_market_order(self, symbol: str, side: str, quantity: float) -> OrderResult:
        """Ejecutar orden market"""
        pass

    @abstractmethod
    async def execute_limit_order(self, symbol: str, side: str, quantity: float, price: float) -> OrderResult:
        """Ejecutar orden limit"""
        pass

    @abstractmethod
    async def execute_stop_order(self, symbol: str, side: str, quantity: float, stop_price: float) -> OrderResult:
        """Ejecutar orden stop"""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancelar orden"""
        pass


class ICommissionCalculator(ABC):
    """Calculadora de comisiones"""

    @abstractmethod
    def calculate_maker_commission(self, quantity: float, price: float) -> float:
        """Calcular comisión maker"""
        pass

    @abstractmethod
    def calculate_taker_commission(self, quantity: float, price: float) -> float:
        """Calcular comisión taker"""
        pass

    @abstractmethod
    def calculate_funding_fee(self, position_size: float, price: float) -> float:
        """Calcular funding fee"""
        pass


class IExecutionValidator(ABC):
    """Validador de ejecución de órdenes"""

    @abstractmethod
    async def validate_position_size(self, symbol: str, quantity: float, leverage: int) -> bool:
        """Validar tamaño de posición con leverage"""
        pass

    @abstractmethod
    async def validate_min_notional(self, symbol: str, quantity: float, price: float) -> bool:
        """Validar mínima notional requerida"""
        pass

    @abstractmethod
    async def validate_margin_requirement(self, account_id: str, required_margin: float) -> bool:
        """Validar margin disponible"""
        pass


class IPositionTracker(ABC):
    """Tracker de posiciones para SL/TP"""

    @abstractmethod
    async def check_stop_loss(self, position: Position, current_price: float) -> bool:
        """Verificar si debe activarse stop loss"""
        pass

    @abstractmethod
    async def check_take_profit(self, position: Position, current_price: float) -> bool:
        """Verificar si debe activarse take profit"""
        pass

    @abstractmethod
    async def execute_risk_management(self, position: Position, current_price: float) -> Optional[OrderResult]:
        """Ejecutar gestión de riesgo automática"""
        pass
