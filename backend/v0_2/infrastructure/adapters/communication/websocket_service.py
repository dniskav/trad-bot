#!/usr/bin/env python3
"""
WebSocket Service - Hexagonal Architecture Implementation
Implementa WebSocketManager sin singleton pattern siguiendo Clean Architecture
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import WebSocket
from backend.shared.logger import get_logger

log = get_logger("websocket.service")


class WebSocketService:
    """
    Service para manejo de WebSocket connections sin singleton pattern
    Aplicando principios de Clean Architecture y Dependency Injection
    """

    def __init__(self):
        self.connections: List[WebSocket] = []
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.message_queue: List[Dict[str, Any]] = []
        self._health_check_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Inicializar el servicio y iniciar health checks"""
        log.info("🚀 Starting WebSocket Service")
        
        # Iniciar health check task en background
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        log.info("✅ WebSocket Service started")

    async def stop(self) -> None:
        """Detener el servicio y cleanup"""
        log.info("🛑 Stopping WebSocket Service")
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect all clients gracefully
        await self._disconnect_all_clients()
        
        log.info("✅ WebSocket Service stopped")

    async def connect(self, websocket: WebSocket, client_id: Optional[str] = None) -> str:
        """
        Aceptar y rastrear una nueva conexión WebSocket
        
        Args:
            websocket: La conexión WebSocket
            client_id: ID opcional del cliente (se genera uno si no se proporciona)
            
        Returns:
            str: ID único del cliente
        """
        try:
            await websocket.accept()
            
            # Generar ID único para el cliente
            if not client_id:
                client_id = f"client_{len(self.connections)}_{int(datetime.now().timestamp())}"
            
            # Agregar conexión
            self.connections.append(websocket)
            
            # Metadatos de conexión
            connection_time = datetime.now(timezone.utc)
            self.connection_metadata[client_id] = {
                "websocket": websocket,
                "connected_at": connection_time,
                "last_activity": connection_time,
                "message_count": 0,
                "status": "active"
            }
            
            log.info(f"WS client connected: {client_id} (total: {len(self.connections)})")
            
            # Enviar mensaje de bienvenida
            await self._send_to_client(client_id, {
                "type": "welcome",
                "client_id": client_id,
                "message": "Connected to Trading Bot WebSocket Service",
                "timestamp": connection_time.isoformat()
            })
            
            return client_id
            
        except Exception as e:
            log.error(f"Error connecting WebSocket client: {e}")
            raise

    async def disconnect(self, client_id: str) -> None:
        """
        Desconectar un cliente específico
        
        Args:
            client_id: ID del cliente a desconectar
        """
        try:
            if client_id in self.connection_metadata:
                metadata = self.connection_metadata[client_id]
                websocket = metadata["websocket"]
                
                # Remover de conexiones activas
                if websocket in self.connections:
                    self.connections.remove(websocket)
                
                # Remover metadatos
                del self.connection_metadata[client_id]
                
                log.info(f"WS client disconnected: {client_id} (total: {len(self.connections)})")
                
        except Exception as e:
            log.error(f"Error disconnecting client {client_id}: {e}")

    async def disconnect_websocket(self, websocket: WebSocket) -> None:
        """
        Desconectar un WebSocket directamente
        
        Args:
            websocket: La conexión WebSocket a desconectar
        """
        try:
            # Buscar cliente por websocket
            client_id = None
            for cid, metadata in self.connection_metadata.items():
                if metadata["websocket"] is websocket:
                    client_id = cid
                    break
            
            # Remover de conexiones
            if websocket in self.connections:
                self.connections.remove(websocket)
            
            # Remover metadatos
            if client_id:
                del self.connection_metadata[client_id]
                log.info(f"WS client disconnected by websocket: {client_id}")
            
            log.info(f"WS client disconnected (total: {len(self.connections)})")
            
        except Exception as e:
            log.error(f"Error disconnecting WebSocket: {e}")

    async def broadcast(self, message: Dict[str, Any], client_filter: Optional[List[str]] = None) -> None:
        """
        Transmitir mensaje a todos los clientes conectados
        
        Args:
            message: Mensaje a transmitir
            client_filter: Lista opcional de client IDs a los que enviar (None = todos)
        """
        if not self.connections:
            msg_id = message.get("message_id", "unknown")
            log.debug(f"No connections for broadcast message: {msg_id}")
            return

        # Agregar timestamp si no existe
        if "timestamp" not in message:
            message["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Determinar clientes destinatarios
        target_clients = client_filter or list(self.connection_metadata.keys())
        
        if not target_clients:
            return

        disconnected_clients = []
        successful_sends = 0

        for client_id in target_clients:
            if client_id in self.connection_metadata:
                metadata = self.connection_metadata[client_id]
                websocket = metadata["websocket"]
                
                if websocket in self.connections:
                    try:
                        await websocket.send_json(message)
                        metadata["last_activity"] = datetime.now(timezone.utc)
                        successful_sends += 1
                        
                    except Exception as e:
                        log.warning(f"Error sending to client {client_id}: {type(e).__name__}: {e}")
                        disconnected_clients.append(client_id)
                        metadata["status"] = "disconnected"

        # Cleanup de clientes desconectados
        for client_id in disconnected_clients:
            await self.disconnect(client_id)

        log.debug(f"Broadcast completed: {successful_sends} sent, {len(disconnected_clients)} disconnected")

    async def send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """
        Enviar mensaje a un cliente específico
        
        Args:
            client_id: ID del cliente
            message: Mensaje a enviar
            
        Returns:
            bool: True si se envío correctamente
        """
        return await self._send_to_client(client_id, message)

    async def _send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """Método interno para enviar mensaje a cliente"""
        try:
            if client_id not in self.connection_metadata:
                
                return False

            metadata = self.connection_metadata[client_id]
            websocket = metadata["websocket"]
            
            if websocket not in self.connections or metadata["status"] != "active":
                log.warning(f"Client {client_id} is not active")
                return False

            # Agregar timestamp si no existe
            if "timestamp" not in message:
                message["timestamp"] = datetime.now(timezone.utc).isoformat()

            await websocket.send_json(message)
            
            # Actualizar metadatos
            metadata["last_activity"] = datetime.now(timezone.utc)
            metadata["message_count"] += 1
            
            return True
            
        except Exception as e:
            log.error(f"Error sending to client {client_id}: {e}")
            await self.disconnect(client_id)
            return False

    async def get_client_status(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener estado de un cliente específico
        
        Args:
            client_id: ID del cliente
            
        Returns:
            Dict con información del cliente o None si no existe
        """
        if client_id not in self.connection_metadata:
            return None

        metadata = self.connection_metadata[client_id].copy()
        
        # Remover websocket de la respuesta (no serializable)
        metadata.pop("websocket", None)
        
        # Agregar métricas calculadas
        now = datetime.now(timezone.utc)
        metadata["uptime_seconds"] = (now - metadata["connected_at"]).total_seconds()
        metadata["idle_seconds"] = (now - metadata["last_activity"]).total_seconds()
        
        return metadata

    async def get_service_status(self) -> Dict[str, Any]:
        """
        Obtener estado completo del servicio WebSocket
        
        Returns:
            Dict con métricas y estadísticas del servicio
        """
        now = datetime.now(timezone.utc)
        
        # Calcular métricas de conexiones
        active_connections = len(self.connections)
        total_messages = sum(m["message_count"] for m in self.connection_metadata.values())
        
        # Calcular uptime promedio
        avg_uptime = 0
        if self.connection_metadata:
            uptimes = [
                (now - meta["connected_at"]).total_seconds() 
                for meta in self.connection_metadata.values()
            ]
            avg_uptime = sum(uptimes) / len(uptimes)

        return {
            "service_status": "active",
            "active_connections": active_connections,
            "registered_clients": len(self.connection_metadata),
            "total_messages_sent": total_messages,
            "message_queue_size": len(self.message_queue),
            "health_check_active": self._health_check_task is not None and not self._health_check_task.done(),
            "average_uptime_seconds": avg_uptime,
            "timestamp": now.isoformat()
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Health check del servicio WebSocket
        
        Returns:
            Dict con estado de salud del servicio
        """
        try:
            status_response = await self.get_service_status()
            
            # Determinar estado de salud
            is_healthy = (
                status_response["active_connections"] is not None and
                status_response["registered_clients"] is not None and
                self._health_check_task is not None and not self._health_check_task.done()
            )
            
            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "details": status_response,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def _health_check_loop(self) -> None:
        """Loop de health check en background"""
        while True:
            try:
                await asyncio.sleep(30)  # Health check cada 30 segundos
                
                # Limpiar conexiones muertas
                await self._cleanup_dead_connections()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error en health check loop: {e}")
                await asyncio.sleep(5)  # Esperar antes de reintentar

    async def _cleanup_dead_connections(self) -> None:
        """Limpiar conexiones que ya no están activas"""
        dead_clients = []
        
        for client_id, metadata in self.connection_metadata.items():
            websocket = metadata["websocket"]
            
            # Verificar si la conexión está realmente activa
            try:
                if websocket not in self.connections:
                    dead_clients.append(client_id)
                    continue
                    
                # Intentar enviar ping
                await self._send_to_client(client_id, {
                    "type": "ping",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
            except Exception:
                dead_clients.append(client_id)
        
        # Limpiar clientes muertos
        for client_id in dead_clients:
            await self.disconnect(client_id)
            
        if dead_clients:
            log.info(f"Cleaned up {len(dead_clients)} dead connections")

    async def _disconnect_all_clients(self) -> None:
        """Desconectar todos los clientes de forma ordenada"""
        if not self.connection_metadata:
            return
            
        disconnect_tasks = []
        
        for client_id, metadata in list(self.connection_metadata.items()):
            websocket = metadata["websocket"]
            
            # Enviar mensaje de cierre
            try:
                await self._send_to_client(client_id, {
                    "type": "shutdown",
                    "message": "Server shutting down",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                # Crear task para disconnect
                task = asyncio.create_task(self.disconnect(client_id))
                disconnect_tasks.append(task)
                
            except Exception:
                continue
        
        # Esperar a que todos los disconnects terminen
        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        
        log.info("All WebSocket clients disconnected")


class WebSocketServiceAdapter:
    """
    Adapter para mantener compatibilidad con el código legacy
    que esperaba el singleton WebSocketManager
    """

    def __init__(self, websocket_service: WebSocketService):
        self.websocket_service = websocket_service

    async def connect(self, websocket: WebSocket) -> str:
        """Adapter para connect method legacy"""
        return await self.websocket_service.connect(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        """Adapter para disconnect method legacy"""
        await self.websocket_service.disconnect_websocket(websocket)

    async def broadcast(self, message: dict) -> None:
        """Adapter para broadcast method legacy"""
        await self.websocket_service.broadcast(message)
