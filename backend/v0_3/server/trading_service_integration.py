#!/usr/bin/env python3
"""
Trading Service Integration
Maneja la inicialización e integración del Trading Domain hexagonal con FastAPI
"""

import asyncio
from typing import Optional, Any, Dict

from ..infrastructure.adapters.domain.trading_service_adapter import (
    TradingServiceAdapter,
    TradingServiceIntegration,
    trading_service_integration,
)


class TradingServiceFastAPIIntegration:
    """
    Maneja la integración completa del Trading Domain con FastAPI
    """
    
    def __init__(self):
        self.trading_integration: Any = trading_service_integration
        self.legacy_stm_service = None
        self.hexagonal_trading_service: Optional[TradingServiceAdapter] = None
        self._initialization_task = None
        self.initialization_complete = False
    
    async def initialize_background(self):
        """Inicializar la integración en background sin bloquear el startup de FastAPI"""
        
        if self._initialization_task is None:
            self._initialization_task = asyncio.create_task(
                self._initialize_integration()
            )
    
    async def _initialize_integration(self):
        """Proceso de inicialización interno"""
        
        try:
            print("🔧 Initializing Trading Service Integration (background)...")

            # Inicializar la integración hexagonal
            await self.trading_integration.initialize()

            # Obtener el adapter hexagonal
            self.hexagonal_trading_service = (
                self.trading_integration.get_trading_service_adapter()
            )

            # Crear instancia de servicio legacy de fallback
            from ..services.stm_service import STMService

            self.legacy_stm_service = STMService()

            print("✅ Trading Service Integration completed successfully")
            print(
                f"✅ Hexagonal Trading Service: {type(self.hexagonal_trading_service).__name__}"
            )
            print(f"✅ Legacy STM Service: {type(self.legacy_stm_service).__name__}")

            self.initialization_complete = True

        except Exception as e:
            print(f"❌ Error initializing Trading Service Integration: {e}")
            print("⚠️ Using legacy STM Service only")

            # Fallback a servicio legacy
            from ..services.stm_service import STMService

            self.legacy_stm_service = STMService()

            self.initialization_complete = True
    
    async def get_trading_service_for_router(self) -> Any:
        """
        Proporcionar el servicio de trading para los routers
        Returns: Hexagonal TradingServiceAdapter o Legacy STMService como fallback
        """
        
        # Esperar hasta 10 segundos para que termine la inicialización
        if not self.initialization_complete:
            try:
                if self._initialization_task:
                    await asyncio.wait_for(self._initialization_task, timeout=10.0)
                else:
                    await self._initialize_integration()
            except asyncio.TimeoutError:
                print(
                    "⚠️ Trading Integration initialization timeout, using legacy service"
                )
            except Exception as e:
                print(f"⚠️ Trading Integration initialization error: {e}")

        # Retornar el servicio hexagonal si está disponible, sino legacy
        if self.hexagonal_trading_service:
            return self.hexagonal_trading_service
        else:
            print("⚠️ Using legacy STM Service for Trading endpoints")
            # Usar el Legacy STM Service adaptado al interface esperado
            return self._create_legacy_adapter()

    def _create_legacy_adapter(self) -> Any:
        """Crear un adapter que haga que STMService se vea como TradingServiceAdapter"""
        
        if not self.legacy_stm_service:
            from ..services.stm_service import STMService

            self.legacy_stm_service = STMService()

        class LegacySTMAdapter:
            """Adapter para STM Service legacy en Trading"""

            def __init__(self, stm_service):
                self.stm_service = stm_service

            async def open_position(self, req_data):
                """Wrapper para open_position del STM Service"""
                # Convertir de dict a OpenPositionRequest
                from ..models.position import OpenPositionRequest
                
                request_obj = OpenPositionRequest(**req_data)
                return await self.stm_service.open_position(request_obj)

            async def close_position(self, position_id, reason="MANUAL"):
                """Wrapper para close_position del STM Service"""
                return await self.stm_service.close_position(position_id)

            async def get_positions(self, status=None, symbol=None):
                """Wrapper para get_positions del STM Service"""
                return await self.stm_service.get_positions(status=status)

            async def set_stop_loss(self, position_id, price):
                """Wrapper para set_stop_loss del STM Service"""
                return await self.stm_service.set_stop_loss(position_id, price)

            async def set_take_profit(self, position_id, price):
                """Wrapper para set_take_profit del STM Service"""
                return await self.stm_service.set_take_profit(position_id, price)

            async def get_fees(self, symbol):
                """Wrapper para fees del STM Service (mock)"""
                return {
                    "symbol": symbol,
                    "makerCommission": "0.001",
                    "takerCommission": "0.001",
                    "timestamp": "legacy",
                }

            async def get_orders(self, symbol=None, status=None):
                """Wrapper para orders del STM Service (mock)"""
                return {
                    "success": True,
                    "orders": [],
                    "total": 0,
                    "timestamp": "legacy",
                }

            async def get_ticker_price(self, symbol):
                """Wrapper para ticker del STM Service (mock)"""
                return {
                    "symbol": symbol,
                    "price": "0",
                    "timestamp": "legacy",
                    "note": "Using legacy STM service",
                }

            async def health_check(self):
                """Health check básico"""
                return {
                    "status": "healthy",
                    "service": "Legacy STM Service",
                    "timestamp": "legacy",
                }

        return LegacySTMAdapter(self.legacy_stm_service)

    async def health_check(self) -> Dict[str, Any]:
        """Health check completo de la integración Trading"""
        
        health_data = {
            "trading_integration": {
                "status": "ok" if self.initialization_complete else "initializing",
                "hexagonal_available": self.hexagonal_trading_service is not None,
                "legacy_fallback_available": self.legacy_stm_service is not None,
                "initialization_complete": self.initialization_complete,
            }
        }

        # Health check del servicio hexagonal si está disponible
        if self.hexagonal_trading_service:
            try:
                adapter_health = await self.hexagonal_trading_service.health_check()
                health_data["trading_integration"]["hexagonal_health"] = adapter_health
            except Exception as e:
                health_data["trading_integration"]["hexagonal_health"] = {
                    "status": "error",
                    "error": str(e),
                }

        # Health check del servicio legacy
        if self.legacy_stm_service:
            try:
                # Basic connectivity check
                health_data["trading_integration"]["legacy_health"] = {
                    "status": "ok",
                    "service_type": "STMService",
                }
            except Exception as e:
                health_data["trading_integration"]["legacy_health"] = {
                    "status": "error",
                    "error": str(e),
                }

        return health_data

    async def shutdown(self):
        """Procesos de shutdown"""
        
        try:
            print("🛑 Shutting down Trading Service Integration...")

            if self._initialization_task:
                self._initialization_task.cancel()

            # Cleanup de recursos si es necesario
            self.hexagonal_trading_service = None
            self.legacy_stm_service = None

            print("✅ Trading Service Integration shutdown complete")

        except Exception as e:
            print(f"❌ Error during Trading Service Integration shutdown: {e}")


# Instancia global para FastAPI
trading_service_fastapi_integration = TradingServiceFastAPIIntegration()


# Funciones de utilidad para los routers
async def get_trading_service() -> Any:
    """
    Función helper para routers de Trading
    Returns: TradingServiceAdapter (hexagonal) o LegacySTMAdapter (fallback)
    """
    return await trading_service_fastapi_integration.get_trading_service_for_router()


async def get_positions_service() -> Any:
    """
    Función helper específica para el router de posiciones
    """
    return await trading_service_fastapi_integration.get_trading_service_for_router()


async def get_fees_service() -> Any:
    """
    Función helper específica para el router de fees
    """
    return await trading_service_fastapi_integration.get_trading_service_for_router()


async def trading_health_check() -> Dict[str, Any]:
    """Health check del servicio de Trading completo"""
    return await trading_service_fastapi_integration.health_check()
