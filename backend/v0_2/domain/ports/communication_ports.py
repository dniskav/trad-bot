#!/usr/bin/env python3
"""
Communication Domain Ports
Interfaces para comunicación entre servicios y con el exterior
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from .base_types import Position, Order, Signal


class EventType(Enum):
    """Tipos de eventos del dominio"""
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_CLOSED = "POSITION_CLOSED"
    POSITION_UPDATED = "POSITION_UPDATED"
    ORDER_EXECUTED = "ORDER_EXECUTED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    STRATEGY_STARTED = "STRATEGY_STARTED"
    STRATEGY_STOPPED = "STRATEGY_STOPPED"
    ACCOUNT_BALANCE_UPDATED = "ACCOUNT_BALANCE_UPDATED"
    ERROR_OCCURRED = "ERROR_OCCURRED"


class NotificationChannel(Enum):
    """Canales de notificación"""
    WEBSOCKET = "WEBSOCKET"
    HTTP_WEBHOOK = "HTTP_WEBHOOK"
    EMAIL = "EMAIL"
    LOG = "LOG"


@abstractmethod
class DomainEvent:
    """Evento del dominio"""
    def __init__(self, event_type: EventType, data: Dict[str, Any]):
        self.event_type = event_type
        self.data = data
        self.timestamp = datetime.now().isoformat()
        self.event_id = f"{event_type.value}_{datetime.now().timestamp()}"


class IEventPublisher(ABC):
    """Publisher de eventos del dominio"""

    @abstractmethod
    async def publish_position_opened(self, position: Position) -> None:
        """Publicar evento de posición abierta"""
        pass

    @abstractmethod
    async def publish_position_closed(self, position: Position, exit_price: float, pnl: float) -> None:
        """Publicar evento de posición cerrada"""
        pass

    @abstractmethod
    async def publish_position_updated(self, position: Position, changes: Dict[str, Any]) -> None:
        """Publicar evento de posición actualizada"""
        pass

    @abstractmethod
    async def publish_order_executed(self, order: Order, execution_details: Dict[str, Any]) -> None:
        """Publicar evento de orden ejecutada"""
        pass

    @abstractmethod
    async def publish_signal_generated(self, signal: Signal) -> None:
        """Publicar evento de señal generada"""
        pass

    @abstractmethod
    async def publish_strategy_event(self, strategy_id: str, event_type: str, details: Dict[str, Any]) -> None:
        """Publicar evento de estrategia"""
        pass

    @abstractmethod
    async def publish_stringency_event(self, strategy_id: str, event_type: str, details: Dict[str, Any]) -> None:
        """Publicar evento de estrategia"""
        pass


class IEventSubscriber(ABC):
    """Subscriber de eventos del dominio"""

    @abstractmethod
    async def on_position_opened(self, event: DomainEvent) -> None:
        """Procesar evento de posición abierta"""
        pass

    @abstractmethod
    async def on_position_closed(self, event: DomainEvent) -> None:
        """Procesar evento de posición cerrada"""
        pass

    @abstractmethod
    class IWebSocketManager(ABC):
        """Gestor de conexiones WebSocket"""

        @abstractmethod
        async def connect(self, client_id: str, websocket) -> None:
            """Conectar cliente WebSocket"""
            pass

        @abstractmethod
        async def disconnect(self, client_id: str) -> None:
            """Desconectar cliente WebSocket"""
            pass

        @abstractmethod
        async def broadcast_message(self, message: Dict[str, Any], channel: str = "general") -> None:
            """Broadcast mensaje a todos los clientes"""
            pass

        @abstractmethod
        async def send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
            """Enviar mensaje a cliente específico"""
            pass

        @abstractmethod
        async def get_connected_clients_count(self) -> int:
            """Obtener número de clientes conectados"""
            pass


class IExternalNotificationService(ABC):
    """Servicio de notificaciones externas"""

    @abstractmethod
    async def notify_position_change(self, change_type: str, position_data: Dict[str, Any]) -> None:
        """Notificar cambio de posición al servidor principal"""
        pass

    @abstractmethod
    async def notify_account_update(self, account_data: Dict[str, Any]) -> None:
        """Notificar actualización de cuenta al servidor principal"""
        pass

    @abstractmethod
    async def notify_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Notificar error crítico"""
        pass

    @abstractmethod
    async def send_execution_report(self, execution_data: Dict[str, Any]) -> None:
        """Enviar reporte de ejecución (formato Binance)"""
        pass

    @abstractmethod
    async def send_account_position(self, account_data: Dict[str, Any]) -> None:
        """Enviar posición de cuenta (formato Binance)"""
        pass


class IMessageQueueAdapter(ABC):
    """Adapter para cola de mensajes"""

    @abstractmethod
    async def publish_message(self, topic: str, message: Dict[str, Any]) -> None:
        """Publicar mensaje en topic"""
        pass

    @abstractmethod
    async def subscribe_to_topic(self, topic: str, handler) -> None:
        """Suscribirse a topic"""
        pass

    @abstractmethod
    async def create_topic(self, topic_name: str) -> bool:
        """Crear nuevo topic"""
        pass

    @abstractmethod
    async def delete_topic(self, topic_name: str) -> bool:
        """Eliminar topic"""
        pass


class ICacheAdapter(ABC):
    """Adapter para caché"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Obtener valor de caché"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Establecer valor en caché"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Eliminar valor de caché"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Verificar si key existe en caché"""
        pass

    @abstractmethod
    async def increment(self, key: str, amount: int = 1) -> int:
        """Incrementar valor en caché"""
        pass


class ILogger(ABC):
    """Logger con niveles específicos"""

    @abstractmethod
    async def log_trading_event(self, event_type: str, data: Dict[str, Any], level: str = "INFO") -> None:
        """Log evento de trading específico"""
        pass

    @abstractmethod
    async def log_strategy_event(self, strategy_id: str, data: Dict[str, Any], level: str = "INFO") -> None:
        """Log evento de estrategia específico"""
        pass

    @abstractmethod
    async def log_account_event(self, account_id: str, data: Dict[str, Any], level: str = "INFO") -> None:
        """Log evento de cuenta específico"""
        pass

    @abstractmethod
    async def log_performance_metric(self, metric_name: str, value: float, context: Dict[str, Any]) -> None:
        """Log métrica de performance"""
        pass


class IRateLimiter(ABC):
    """Rate limiter para APIs externas"""

    @abstractmethod
    async def check_rate_limit(self, endpoint: str, requests_per_minute: int = 1200) -> bool:
        """Verificar límite de requests"""
        pass

    @abstractmethod
    async def wait_for_rate_limit(self, endpoint: str, requests_per_minute: int = 1200) -> None:
        """Esperar hasta que se libere el límite"""
        pass

    @abstractmethod
    async def get_remaining_requests(self, endpoint: str) -> int:
        """Obtener requests restantes"""
        pass
