#!/usr/bin/env python3
"""
WebSocket Service Integration - Hexagonal Architecture
Maneja la configuración e integración del WebSocket Service con FastAPI
"""

from typing import Optional
import asyncio
from backend.shared.logger import get_logger

log = get_logger("websocket.integration")

# Instancia global del servicio para inyección
_websocket_service: Optional["WebSocketService"] = None


async def websocket_service_factory():
    """
    Factory function para obtener la instancia global del WebSocket Service
    Compatible con FastAPI Depends
    """
    global _websocket_service

    if _websocket_service is None:
        _websocket_service = await create_websocket_service()

    return _websocket_service


def get_websocket_service() -> Optional["WebSocketService"]:
    """Obtener la instancia del servicio si existe"""
    return _websocket_service


async def initialize_websocket_hexagonal():
    """Inicializar el servicio WebSocket hexagonalmente sin singleton"""
    global _websocket_service

    try:
        _websocket_service = await create_websocket_service()
        await _websocket_service.start()

        log.info("🚀 Hexagonal WebSocket Service initialized successfully")
        return _websocket_service

    except Exception as e:
        log.error(f"Failed to initialize Hexagonal WebSocket Service: {e}")
        raise


async def create_websocket_service() -> "WebSocketService":
    """
    Crear nueva instancia de WebSocketService

    Returns:
        WebSocketService: Nueva instancia configurada sin singleton
    """
    try:
        from backend.v0_2.infrastructure.adapters.communication.websocket_service import (
            WebSocketService,
            WebSocketServiceAdapter,
        )

        # Crear nueva instancia sin singleton
        websocket_service = WebSocketService()

        log.info("✅ WebSocket Service created (hexagonal - no singleton)")
        return websocket_service

    except Exception as e:
        log.error(f"Error creating WebSocket Service: {e}")
        raise


async def shutdown_websocket_service():
    """Shutdown del servicio WebSocket hexagonal"""
    global _websocket_service

    if _websocket_service:
        try:
            await _websocket_service.stop()
            log.info("✅ Hexagonal WebSocket Service stopped")
        except Exception as e:
            log.error(f"Error stopping WebSocket Service: {e}")
        finally:
            _websocket_service = None


async def websocket_service_dependency():
    """
    Dependency injection para routers FastAPI
    Proporciona servicio WebSocket hexagonal
    """
    global _websocket_service

    if _websocket_service is None:
        log.warning("WebSocket Service not initialized, creating on demand...")
        _websocket_service = await create_websocket_service()
        await _websocket_service.start()

    return _websocket_service


def create_legacy_websocket_adapter():
    """
    Crear adapter para código legacy que esperaba WebSocketManager singleton

    Returns:
        WebSocketServiceAdapter: Adapter compatible con código legacy
    """
    try:
        from backend.v0_2.infrastructure.adapters.communication.websocket_service import (
            WebSocketServiceAdapter,
        )

        global _websocket_service

        if _websocket_service is None:
            raise ValueError("WebSocket Service not initialized")

        return WebSocketServiceAdapter(_websocket_service)

    except Exception as e:
        log.error(f"Error creating legacy WebSocket adapter: {e}")
        raise


# Función de compatibilidad con código legacy
async def get_websocket_manager():
    """
    Función de compatibilidad para código legacy
    Retorna adapter que imita la interface del singleton WebSocketManager
    """
    try:
        # Lógica hexagonal
        websocket_service = await websocket_service_dependency()
        adapter = create_legacy_websocket_adapter()
        return adapter

    except Exception as e:
        log.warning(f"Failed to use hexagonal WebSocket service: {e}")

        # Fallback al WebSocketManager legacy como último recurso
        try:
            from backend.v0_2.server.services.websocket_manager import WebSocketManager

            return WebSocketManager()
        except Exception as fallback_error:
            log.error(
                f"Fallback to legacy WebSocketManager also failed: {fallback_error}"
            )
            raise e
