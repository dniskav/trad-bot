#!/usr/bin/env python3
"""
Account Service Integration
Maneja la inicialización e integración del Account Domain hexagonal con FastAPI
"""

import asyncio
from typing import Optional, Any, Dict

from ..infrastructure.adapters.domain.account_service_adapter import (
    AccountServiceAdapter,
    AccountServiceIntegration, 
    account_service_integration
)


class AccountServiceFastAPIIntegration:
    """
    Maneja la integración completa del Account Domain con FastAPI
    """
    
    def __init__(self):
        self.account_integration: Any = account_service_integration
        self.legacy_stm_service = None
        self.hexagonal_account_service: Optional[AccountServiceAdapter] = None
        self._initialization_task = None
        self.initialization_complete = False
    
    async def initialize_background(self):
        """Inicializar la integración en background sin bloquear el startup de FastAPI"""
        
        if self._initialization_task is None:
            self._initialization_task = asyncio.create_task(self._initialize_integration())
    
    async def _initialize_integration(self):
        """Proceso de inicialización interno"""
        
        try:
            print("🔧 Initializing Account Service Integration (background)...")
            
            # Inicializar la integración hexagonal
            await self.account_integration.initialize()
            
            # Obtener el adapter hexagonal
            self.hexagonal_account_service = self.account_integration.get_account_service_adapter()
            
            # Crear instancia de servicio legacy de fallback
            from ..services.stm_service import STMService
            self.legacy_stm_service = STMService()
            
            print("✅ Account Service Integration completed successfully")
            print(f"✅ Hexagonal Account Service: {type(self.hexagonal_account_service).__name__}")
            print(f"✅ Legacy STM Service: {type(self.legacy_stm_service).__name__}")
            
            self.initialization_complete = True
            
        except Exception as e:
            print(f"❌ Error initializing Account Service Integration: {e}")
            print("⚠️ Using legacy STM Service only")
            
            # Fallback a servicio legacy
            from ..services.stm_service import STMService
            self.legacy_stm_service = STMService()
            
            self.initialization_complete = True
    
    async def get_account_service_for_router(self) -> Any:
        """
        Proporcionar el servicio de cuenta para el router
        Returns: Hexagonal AccountServiceAdapter o Legacy STMService como fallback
        """
        
        # Esperar hasta 10 segundos para que termine la inicialización
        if not self.initialization_complete:
            try:
                if self._initialization_task:
                    await asyncio.wait_for(self._initialization_task, timeout=10.0)
                else:
                    await self._initialize_integration()
            except asyncio.TimeoutError:
                print("⚠️ Account Integration initialization timeout, using legacy service")
            except Exception as e:
                print(f"⚠️ Account Integration initialization error: {e}")
        
        # Retornar el servicio hexagonal si está disponible, sino legacy
        if self.hexagonal_account_service:
            return self.hexagonal_account_service
        else:
            print("⚠️ Using legacy STM Service for Account endpoints")
            # Usar el Legacy STM Service adaptado al interface esperado
            return self._create_legacy_adapter()
    
    def _create_legacy_adapter(self) -> Any:
        """Crear un adapter que haga que STMService se vea como AccountServiceAdapter"""
        
        if not self.legacy_stm_service:
            from ..services.stm_service import STMService
            self.legacy_stm_service = STMService()
        
        class LegacySTMAdapter:
            """Adapter para STM Service legacy"""
            
            def __init__(self, stm_service):
                self.stm_service = stm_service
            
            async def get_account_synth(self):
                """Wrapper para get_account_synth del STM Service"""
                return await self.stm_service.get_account_synth()
            
            async def reset_account_synth(self):
                """Wrapper para reset_account_synth del STM Service"""
                return await self.stm_service.reset_account_synth()
        
        return LegacySTMAdapter(self.legacy_stm_service)
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check completo de la integración Account"""
        
        health_data = {
            "account_integration": {
                "status": "ok" if self.initialization_complete else "initializing",
                "hexagonal_available": self.hexagonal_account_service is not None,
                "legacy_fallback_available": self.legacy_stm_service is not None,
                "initialization_complete": self.initialization_complete
            }
        }
        
        # Health check del servicio hexagonal si está disponible
        if self.hexagonal_account_service:
            try:
                adapter_health = await self.hexagonal_account_service.health_check()
                health_data["account_integration"]["hexagonal_health"] = adapter_health
            except Exception as e:
                health_data["account_integration"]["hexagonal_health"] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # Health check del servicio legacy
        if self.legacy_stm_service:
            try:
                # Basic connectivity check
                health_data["account_integration"]["legacy_health"] = {
                    "status": "ok",
                    "service_type": "STMService"
                }
            except Exception as e:
                health_data["account_integration"]["legacy_health"] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return health_data
    
    async def shutdown(self):
        """Procesos de shutdown"""
        
        try:
            print("🛑 Shutting down Account Service Integration...")
            
            if self._initialization_task:
                self._initialization_task.cancel()
            
            # Cleanup de recursos si es necesario
            self.hexagonal_account_service = None
            self.legacy_stm_service = None
            
            print("✅ Account Service Integration shutdown complete")
            
        except Exception as e:
            print(f"❌ Error during Account Service Integration shutdown:并发检查 Account Service Integration...")
            
            if self._initialization_task:
                self._initialization_task.cancel()
            
            # Cleanup de recursos si es necesario
            self.hexagonal_account_service = None
            self.legacy_stm_service = None
            
            print("✅ Account Service Integration shutdown complete")
            
        except Exception as e:
            print(f"❌ Error during Account Service Integration shutdown: {e}")


# Instancia global para FastAPI
account_service_fastapi_integration = AccountServiceFastAPIIntegration()


# Funciones de utilidad para el router
async def get_account_service() -> Any:
    """
    Función helper para el router Account
    Returns: AccountServiceAdapter (hexagonal) o LegacySTMAdapter (fallback)
    """
    return await account_service_fastapi_integration.get_account_service_for_router()


async def account_health_check() -> Dict[str, Any]:
    """Health check del servicio de Account completo"""
    return await account_service_fastapi_integration.health_check()
