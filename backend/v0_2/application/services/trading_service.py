#!/usr/bin/env python3
"""
Trading Application Service
Servicio de aplicación para operaciones de trading siguiendo Clean Architecture
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

from ...domain.models.position import PositionAggregate, PositionStatus, OrderSide
from ...domain.models.order import OrderAggregate, OrderStatus, OrderFactory
from ...domain.ports.trading_ports import (
    IPositionRepository,
    IOrderRepository, 
    IMarketDataProvider,
    ITradingExecutor,
    ICommissionCalculator,
    IExecutionValidator,
    IPositionTracker
)
from ...domain.ports.communication_ports import IEventPublisher


class TradingApplicationService:
    """Application Service para operaciones de trading"""

    def __init__(
        self,
        position_repository: IPositionRepository,
        order_repository: IOrderRepository,
        market_data_provider: IMarketDataProvider,
        trading_executor: ITradingExecutor,
        commission_calculator: ICommissionCalculator,
        execution_validator: IExecutionValidator,
        position_tracker: IPositionTracker,
        event_publisher: IEventPublisher
    ):
        self.position_repository = position_repository
        self.order_repository = order_repository
        self.market_data_provider = market_data_provider
        self.trading_executor = trading_executor
        self.commission_calculator = commission_calculator
        self.execution_validator = execution_validator
        self.position_tracker = position_tracker
        self.event_publisher = event_publisher

    async def open_position(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        leverage: int = 1,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        client_order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Caso de uso: Abrir nueva posición
        
        Este es el caso de uso principal para abrir posiciones,
        que orquesta todos los servicios del dominio de trading.
        """
        try:
            # 1. Validar parámetros de entrada
            await self._validate_open_position_params(symbol, side, quantity, leverage, order_type, price)
            
            # 2. Obtener precio de mercado si es necesario
            current_price = await self._get_execution_price(symbol, order_type, price)
            
            # 3. Validar requisitos de ejecución
            await self._validate_execution_requirements(symbol, quantity, current_price, leverage)
            
            # 4. Crear posición y orden
            position, order = await self._create_position_and_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                leverage=leverage,
                order_type=order_type,
                execution_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                client_order_id=client_order_id
            )
            
            # 5. Ejecutar orden
            execution_result = await self._execute_order(order, current_price)
            
            # 6. Actualizar posición con resultado de ejecución
            if execution_result.success:
                position = await self._update_position_with_execution(position, execution_result)
                
                # 7. Persistir cambios
                await self.position_repository.save_position(position)
                await self.order_repository.save_order(order)
                
                # 8. Publicar eventos
                await self.event_publisher.publish_position_opened(position)
                await self.event_publisher.publish_order_executed(order, execution_result.__dict__)
                
                return {
                    "success": True,
                    "position_id": position.position_id,
                    "order_id": order.order_id,
                    "executed_price": float(execution_result.executed_price),
                    "executed_quantity": float(execution_result.executed_quantity),
                    "commission": float(execution_result.commission) if execution_result.commission else 0.0,
                    "message": "Position opened successfully"
                }
            else:
                return {
                    "success": False,
                    "message": execution_result.message,
                    "error": "Execution failed"
                }
                
        except Exception as e:
            # TODO: Mejorar manejo de errores con tipos específicos
            return {
                "success": False,
                "message": f"Error opening position: {str(e)}",
                "error": str(e)
            }

    async def close_position(
        self,
        position_id: str,
        reason:=str = "manual"
    ) -> Dict[str, Any]:
        """
        Caso de uso: Cerrar posición existente
        """
        try:
            # 1. Obtener posición
            position = await self.position_repository.get_position(position_id)
            if not position:
                return {"success": False, "message": f"Position {position_id} not found"}
            
            if position.status != PositionStatus.OPEN:
                return {"success": False, "message": f"Position {position_id} is not open"}
            
            # 2. Obtener precio actual
            current_price = await self.market_data_provider.get_current_price(position.symbol)
            
            # 3. Calcular P&L final
            final_pnl = position.close_position(
                Price.from_float(current_price, position.symbol),
                reason
            )
            
            # 4. Crear orden de cierre
            close_order = OrderFactory.create_market_order(
                symbol=position.symbol,
                side=position.side.opposite(),
                quantity=float(position.quantity.amount)
            )
            close_order.position_id = position_id
            
            # 5. Ejecutar orden de cierre
            execution_result = await self._execute_order(close_order, Price.from_float(current_price, position.symbol))
            
            if execution_result.success:
                # 6. Actualizar orden con resultados
                close_order.execute(
                    Price.from_float(current_price, position.symbol),
                    position.quantity,
                    Money.from_float(float(execution_result.commission)) if execution_result.execution_commission else Money.zero()
                )
                
                # 7. Persistir cambios
                await self.position_repository.update_position(position)
                await self.order_repository.save_order(close_order)
                
                # 8. Publicar eventos
                await self.event_publisher.publish_position_closed(position, current_price, float(final_pnl.amount))
                
                return {
                    "success": True,
                    "position_id": position_id,
                    "final_pnl": float(final_pnl.amount),
                    "exit_price": current_price,
                    "order_id": close_order.order_id,
                    "message": f"Position closed successfully. P&L: {float(final_pnl.amount):.4f}"
                }
            else:
                return {
                    "success": False,
                    "message": execution_result.message,
                    "error": "Close execution failed"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Error closing position: {str(e)}",
                "error": str(e)
            }

    async def check_and_execute_risk_management(self) -> Dict[str, Any]:
        """
        Caso de uso: Verificar y ejecutar gestión de riesgo automática
        """
        try:
            # 1. Obtener todas las posiciones abiertas
            open_positions = await self.position_repository.get_active_positions()
            
            executions_count = 0
            for position in open_positions:
                # 2. Obtener precio actual
                current_price = await self.market_data_provider.get_current_price(position.symbol)
                current_price_obj = Price.from_float(current_price, position.symbol)
                
                # 3. Verificar triggers de riesgo
                risk_result = await self.position_tracker.execute_risk_management(position, current_price)
                
                if risk_result:
                    executions_count += 1
                    await self.event_publisher.publish_position_closed(
                        position, 
                        current_price, 
                        float(position.pnl.amount)
                    )
            
            return {
                "success": True,
                "positions_checked": len(open_positions),
                "risk_executions": executions_count,
                "message": f"Risk management executed on {executions_count} positions"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error in risk management: {str(e)}",
                "error": str(e)
            }

    async def get_position_status(self, position_id: str) -> Optional[Dict[str, Any]]:
        """
        Caso de uso: Obtener estado detallado de posición
        """
        try:
            position = await self.position_repository.get_position(position_id)
            if not position:
                return None
            
            # Actualizar P&L con precio actual
            current_price = await self.market_data_provider.get_current_price(position.symbol)
            position.update_pnl(Price.from_float(current_price, position.symbol))
            
            # Obtener órdenes relacionadas
            orders = await self.order_repository.get_orders_by_position(position_id)
            
            return {
                "position": position.to_dict(),
                "current_price": current_price,
                "orders_count": len(orders),
                "unrealized_pnl": float(position.pnl.amount),
                "position_value": float(position.get_position_value(Price.from_float(current_price, position.symbol)).amount)
            }
            
        except Exception as e:
            # TODO: Mejorar logging de errores
            return None

    # === MÉTODOS PRIVADOS ===

    async def _validate_open_position_params(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        leverage: int,
        order_type: str,
        price: Optional[float]
    ) -> None:
        """Validar parámetros de apertura de posición"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        if leverage < 1 or leverage > 125:
            raise ValueError("Leverage must be between 1 and 125")
        
        if order_type == "LIMIT" and not price:
            raise ValueError("LIMIT orders require price parameter")

    async def _get_execution_price(self, symbol: str, order_type: str, price: Optional[float]) -> float:
        """Obtener precio de ejecución según tipo de orden"""
        if order_type == "MARKET" or not price:
            return await self.market_data_provider.get_current_price(symbol)
        return price

    async def _validate_execution_requirements(
        self,
        symbol: str,
        quantity: float,
        price: float,
        leverage: int
    ) -> None:
        """Validar requisitos de ejecución"""
        # Validar mínimo notional
        if not await self.execution_validator.validate_min_notional(symbol, quantity, price):
            raise ValueError("Order does not meet minimum notional requirement")
        
        # Validar tamaño de posición
        if not await self.execution_validator.validate_position_size(symbol, quantity, leverage):
            raise ValueError("Position size validation failed")
        
        # TODO: Agregar validación de margin disponible

    async def _create_position_and_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        leverage: int,
        order_type: str,
        execution_price: float,
        stop_loss: Optional[float],
        take_profit: Optional[float],
        client_order_id: Optional[str]
    ) -> tuple[PositionAggregate, OrderAggregate]:
        """Crear posición y orden correspondiente"""
        
        # Crear posición
        position_id = f"pos_{datetime.now().timestamp()}"
        position = PositionAggregate(
            position_id=position_id,
            symbol=symbol,
            side=side,
            quantity=Quantity.from_float(quantity),
            entry_price=Price.from_float(execution_price, symbol),
            leverage=leverage
        )
        
        # Establecer SL/TP si se proporcionan
        if stop_loss:
            position.set_stop_loss(Price.from_float(stop_loss, symbol))
        
        if take_profit:
            position.set_take_profit(Price.from_float(take_profit, symbol))
        
        # Crear orden según tipo
        if order_type == "MARKET":
            order = OrderFactory.create_market_order(symbol, side, quantity, client_order_id)
        elif order_type == "LIMIT":
            order = OrderFactory.create_limit_order(symbol, side, quantity, execution_price, client_order_id)
        else:
            raise ValueError(f"Unsupported order type: {order_type}")
        
        order.position_id = position_id
        
        return position, order

    async def _execute_order(self, order: OrderAggregate, execution_price_price) -> Any:
        """Ejecutar orden usando trading executor"""
        if order.order_type.value == "MARKET":
            return await self.trading_executor.execute_market_order(
                symbol=order.symbol,
                side=order.side.value,
                quantity=float(order.quantity.amount)
            )
        elif order.order_type.value == "LIMIT":
            return await self.trading_executor.execute_limit_order(
                symbol=order.symbol,
                side=order.side.value,
                quantity=float(order.quantity.amount),
                price=float(order.price.value)  # type: ignore
            )
        else:
            raise ValueError(f"Cannot execute order type: {order.order_type}")

    async def _update_position_with_execution(self, position: PositionAggregate, execution_result: Any) -> PositionAggregate:
        """Actualizar posición con resultados de ejecución"""
        # Marcar orden como ejecutada
        # TODO: Implementar lógica de actualización según execution_result
        
        # Actualizar timestamp de posición
        position.updated_at = datetime.now()
        
        return position
