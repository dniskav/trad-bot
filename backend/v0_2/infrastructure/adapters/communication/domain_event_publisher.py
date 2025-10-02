#!/usr/bin/env python3
"""
Domain Event Publisher Adapter
Implementación del IEventPublisher usando broadcast a multiples canales
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from backend.shared.logger import get_logger

from ...domain.ports.communication_ports import IEventPublisher, DomainEvent, EventType
from ...domain.models.position import PositionAggregate
from ...domain.models.order import OrderAggregate

log = get_logger("domain_event_publisher")


class DomainEventPublisher(IEventPublisher):
    """Publisher de eventos del dominio con múltiples canales de salida"""

    def __init__(self):
        self._subscribers = []
        self._event_history = []
        self._max_history_size = 1000

    def add_subscriber(self, subscriber) -> None:
        """Agregar suscriptor a eventos"""
        self._subscribers.append(subscriber)

    async def publish_position_opened(self, position: PositionAggregate) -> None:
        """Publicar evento de posición abierta"""
        event_data = {
            "event_type": EventType.POSITION_OPENED.value,
            "position_id": position.position_id,
            "symbol": position.symbol,
            "side": position.side.value,
            "quantity": str(position.quantity.amount),
            "entry_price": str(position.entry_price.value),
            "leverage": position.leverage,
            "stop_loss": str(position.stop_loss_price.value) if position.stop_loss_price else None,
            "take_profit": str(position.take_profit_price.value) if position.take_profit_price else None,
            "timestamp": datetime.now().isoformat()
        }
        
        await self._broadcast_event(event_data)
        await self._notify_smt(position)
        log.info(f"📈 Position opened: {position.symbol} {position.side.value} {position.quantity.amount}")

    async def publish_position_closed(
        self, 
        position: PositionAggregate, 
        exit_price: float, 
        pnl: float
    ) -> None:
        """Publicar evento de posición cerrada"""
        event_data = {
            "event_type": EventType.POSITION_CLOSED.value,
            "position_id": position.position_id,
            "symbol": position.symbol,
            "side": position.side.value.value,
            "quantity": str(position.quantity.amount),
            "entry_price": str(position.entry_price.value),
            "exit_price": str(exit_price),
            "pnl": str(pnl),
            "duration_seconds": self._calculate_duration(position),
            "timestamp": datetime.now().isoformat()
        }
        
        await self._broadcast_event(event_data)
        await self._notify_smt(event_data)
        log.info(f"📉 Position closed: {position.symbol} P&L: {pnl:.4f}")

    async def publish_position_updated(
        self, 
        position: PositionAggregate, 
        changes: Dict[str, Any]
    ) -> None:
        """Publicar evento de posición actualizada"""
        event_data = {
            "event_type": EventType.POSITION_UPDATED.value,
            "position_id": position.position_id,
            "symbol": position.symbol,
            "changes": changes,
            "current_pnl": str(position.pnl.amount),
            "timestamp": datetime.now().isoformat()
        }
        
        await self._broadcast_event(event_data)
        log.info(f"🔄 Position updated: {position.symbol} {changes}")

    async def publish_order_executed(
        self, 
        order: OrderAggregate, 
        execution_details: Dict[str, Any]
    ) -> None:
        """Publicar evento de orden ejecutada"""
        event_data = {
            "event_type": EventType.ORDER_EXECUTED.value,
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side.value,
            "order_type": order.order_type.value,
            "status": order.status.value,
            "executed_price": str(order.executed_price.value) if order.executed_price else None,
            "executed_quantity": str(order.executed_quantity.amount) if order.executed_quantity else None,
            "commission": str(order.commission.amount) if order.commission else None,
            "execution_details": execution_details,
            "timestamp": datetime.now().isoformat()
        }
        
        await self._broadcast_event(event_data)
        log.info(f"⚡ Order executed: {order.symbol} {order.side.value} {order.order_type.value}")

    async def publish_signal_generated(self, signal) -> None:
        """Publicar evento de señal generada"""
        event_data = {
            "event_type": EventType.SIGNAL_GENERATED.value,
            "signal_type": signal.signal_type.value,
            "confidence": signal.confidence,
            "strategy_name": signal.strategy_name,
            "metadata": signal.metadata,
            "timestamp": signal.timestamp
        }
        
        await self._broadcast_event(event_data)
        log.info(f"📊 Signal generated: {signal.signal_type.value} {signal.strategy_name} ({signal.confidence:.2f})")

    async def publish_strategy_event(
        self, 
        strategy_id: str, 
        event_type: str, 
        details: Dict[str, Any]
    ) -> None:
        """Publicar evento de estrategia"""
        event_data = {
            "event_type": event_type,
            "strategy_id": strategy_id,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
        await self._broadcast_event(event_data)
        log.info(f"🤖 Strategy event: {strategy_id} {event_type}")

    async def publish_stringency_event(
        self, 
        strategy_id: str, 
        event_type: str, 
        details: Dict[str, Any]
    ) -> None:
        """Publicar evento de estrategia (mantiene compatibilidad con typo)"""
        await self.publish_strategy_event(strategy_id, event_type, details)

    # === MÉTODOS PRIVADOS ===

    async def _broadcast_event(self, event_data: Dict[str, Any]) -> None:
        """Broadcast evento a todos los suscriptores"""
        # Agregar a historial
        self._add_to_history(event_data)
        
        # Notificar suscriptores
        for subscriber in self._subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(event_data)
                else:
                    subscriber(event_data)
            except Exception as e:
                log.warning(f"Subscriber notification error: {e}")

    async def _notify_smt(self, event_data: Dict[str, Any]) -> None:
        """Notificar al servidor principal sobre eventos importantes"""
        try:
            # Solo notificar eventos críticos al servidor
            critical_events = [
                EventType.POSITION_OPENED.value,
                EventType.POSITION_CLOSED.value,
                EventType.ORDER_EXECUTED.value
            ]
            
            if event_data.get("event_type") in critical_events:
                await self._send_to_server(event_data)
                
        except Exception as e:
            log.error(f"Error notifying server: {e}")

    async def _send_to_server(self, event_data: Dict[str, Any]) -> None:
        """Enviar evento al servidor principal (formato Binance-compatible)"""
        try:
            import aiohttp
            
            # Solo enviar si tenemos información suficiente
            if event_data.get("event_type") == EventType.POSITION_OPENED.value:
                await self._send_position_init_msg(event_data)
            elif event_data.get("event_type") == EventType.POSITION_CLOSED.value:
                await self._send_position_balance_msg(event_data)
                
        except Exception as e:
            log.error(f"Failed to send position event to server: {e}")

    async def _send_position_init_msg(self, event_data: Dict[str, Any]) -> None:
        """Enviar mensaje de position init al servidor"""
        try:
            import aiohttp
            
            # Construir mensaje compatible con Binance Streaming
            stm_msg = {
                "stream": "accountPos",
                "data": {
                    "E": int(datetime.now().timestamp() * 1000),
                    "s": "DOGEUSDT",
                    "pa": event_data.get("quantity", "0"),
                    "ep": event_data.get("entry_price", "0"),
                    "cr": "0.0",
                    "up": "0.0",
                    "mt": "ISOLATED",
                    "iw": "0.0",
                    "ps": "BOTH"
                }
            }
            
            # Enviar al servidor si tenemos WebSocket connection disponible
            await self._broadcast_to_websocket(stm_msg)
            
        except Exception as e:
            log.error(f"Position init message error: {e}")

    async def _send_position_balance_msg(self, event_data: Dict[str, Any]) -> None:
        """Enviar mensaje de account position al servidor"""
        try:
            import aiohttp
            
            stm_msg = {
                "stream": "accountPos",
                "data": {
                    "E": int(datetime.now().timestamp() * 1000),
                    "s": event_data.get("symbol", "DOGEUSDT"),
                    "pa": "0",  # Position amount becomes 0 when closed
                    "ep": "0",
                    "cr": event_data.get("pnl", "0"),
                    "up": event_data.get("pnl", "0"),
                    "mt": "ISOLATED",
                    "iw": "0.0",
                    "ps": "BOTH"
                }
            }
            
            await self._broadcast_to_websocket(stm_msg)
            
        except Exception as e:
            log.error(f"Position balance message error: {e}")

    async def _broadcast_to_websocket(self, message: Dict[str, Any]) -> None:
        """Broadcast mensaje a WebSocket (simulación)"""
        # Aquí se integraría con el WebSocket Manager existente
        # Por ahora solo loguear el evento
        log.info(f"📡 WebSocket broadcast: {message}")

    def _calculate_duration(self, position: PositionAggregate) -> float:
        """Calcular duración de posición en segundos"""
        try:
            from datetime import datetime
            start_time = datetime.fromisoformat(str(position.created_at).replace('Z', '+00:00'))
            end_time = datetime.now()
            return (end_time - start_time).total_seconds()
        except:
            return 0.0

    def _add_to_history(self, event_data: Dict[str, Any]) -> None:
        """Agregar evento al historial"""
        self._event_history.append(event_data)
        
        # Mantener historial limitado
        if len(self._event_history) > self._max_history_size:
            self._event_history = self._event_history[-self._max_history_size:]

    def get_event_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtener historial de eventos"""
        return self._event_history[-limit:]

    def get_event_stats(self) -> Dict[str, int]:
        """Obtener estadísticas de eventos"""
        stats = {}
        for event in self._event_history:
            event_type = event.get("event_type", "unknown")
            stats[event_type] = stats.get(event_type, 0) + 1
        return stats


if __name__ == "__main__":
    # Test del publisher
    async def test_publisher():
        publisher = DomainEventPublisher()
        
        print("📡 Testing DomainEventPublisher...")
        
        # Test position opened event
        from ...domain.models.position import PositionAggregate, OrderSide, Quantity, Price
        
        test_position = PositionAggregate(
            position_id="test_event_123",
            symbol="DOGEUSDT",
            side=OrderSide.BUY,
            quantity=Quantity.from_float(100.0),
            entry_price=Price.from_float(0.085, "DOGEUSDT"),
            leverage=5
        )
        
        await publisher.publish_position_opened(test_position)
        
        # Test position closed event
        await publisher.publish_position_closed(test_position, 0.090, 5.0)
        
        # Ver estadísticas
        stats = publisher.get_event_stats()
        print(f"✅ Event stats: {stats}")
        
        print("🎯 Publisher test complete!")
    
    # Comentado para evitar imports circulares
    # asyncio.run(test_publisher())
