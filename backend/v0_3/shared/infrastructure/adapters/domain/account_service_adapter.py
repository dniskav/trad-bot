#!/usr/bin/env python3
"""
Account Service Adapter
Adaptador para conectar el router existente con el nuevo AccountApplicationService
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from ..application.services.account_service import AccountApplicationService


class AccountServiceAdapter:
    """
    Adapter que adapta el AccountApplicationService a la interfaz esperada por el router legacy
    Este adapter mantiene compatibilidad con la API existente mientras usa la nueva arquitectura
    """

    def __init__(self, account_application_service: AccountApplicationService):
        self.account_service = account_application_service

    async def get_account_synth(self) -> Dict[str, Any]:
        """Obtener datos de cuenta sintética en formato legacy compatible"""

        try:
            # Obtener datos de cuenta usando el nuevo servicio
            account_details = await self.account_service.get_account_details(
                "main_account"
            )

            if not account_details:
                return {"code": 404, "message": "Account not found", "data": None}

            # Convertir a formato legacy sintético
            synth_data = self._convert_to_legacy_format(account_details)

            return {
                "code": 200,
                "data": synth_data,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "code": 500,
                "message": f"Error retrieving account data: {str(e)}",
                "data": None,
            }

    async def reset_account_synth(self) -> Dict[str, Any]:
        """Resetear cuenta sintética usando el nuevo servicio"""

        try:
            # Crear nueva cuenta con valores por defecto
            initial_balance = (
                await self.account_service.create_initial_balance_changes()
            )

            if initial_balance:
                return {
                    "code": 200,
                    "data": {
                        "account": "main_account",
                        "reset_at": datetime.now().isoformat(),
                        "initial_balance": initial_balance,
                    },
                    "message": "Account reset successfully",
                }
            else:
                return {"code": 500, "message": "Failed to reset account", "data": None}

        except Exception as e:
            return {
                "code": 500,
                "message": f"Error resetting account: {str(e)}",
                "data": None,
            }

    async def process_balance_changes(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Procesar cambios de balance usando el nuevo servicio"""

        try:
            balance_changes = changes.get("changes", [])

            if not balance_changes:
                return {
                    "code": 400,
                    "message": "No balance changes provided",
                    "data": None,
                }

            # Procesar usando el nuevo servicio
            result = await self.account_service.process_balance_changes(
                "main_account", balance_changes
            )

            if result["success"]:
                return {
                    "code": 200,
                    "data": {
                        "processed_changes": len(balance_changes),
                        "updated_balances": result["updated_balances"],
                        "processed_at": datetime.now().isoformat(),
                    },
                    "message": "Balance changes processed successfully",
                }
            else:
                return {
                    "code": 400,
                    "message": result.get("error", "Failed to process balance changes"),
                    "data": None,
                }

        except Exception as e:
            return {
                "code": 500,
                "message": f"Error processing balance changes: {str(e)}",
                "data": None,
            }

    async def get_account_performance(self) -> Dict[str, Any]:
        """Obtener métricas de performance de la cuenta"""

        try:
            # Obtener métricas usando el servicio de balance calculator
            metrics = await self.account_service.get_account_performance("main_account")

            return {
                "code": 200,
                "data": metrics,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "code": 500,
                "message": f"Error retrieving performance data: {str(e)}",
                "data": None,
            }

    def _convert_to_legacy_format(
        self, account_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convertir datos de nueva estructura a formato legacy para compatibilidad"""

        # Extraer balances
        balances = account_details.get("balances", [])
        legacy_balances = {}

        for balance in balances:
            asset = balance.get("asset")
            free = balance.get("free", 0.0)
            locked = balance.get("locked", 0.0)

            legacy_balances[asset] = {"free": str(free), "locked": str(locked)}

        # Crear estructura legacy
        legacy_data = {
            "balances": legacy_balances,
            "fees": account_details.get("fees", {}),
            "total_balance_usdt": str(account_details.get("total_usdt_value", 0.0)),
            "account_type": "spot",  # Default para legacy compatibility
            "permissions": ["SPOT"],
            "updateTime": int(datetime.now().timestamp() * 1000),
            "accountId": account_details.get("account_id", "main_account"),
        }

        return legacy_data

    async def health_check(self) -> Dict[str, Any]:
        """Health check del servicio de cuenta"""

        try:
            # Verificar que podemos obtener datos de cuenta
            account_details = await self.account_service.get_account_details(
                "main_account"
            )

            if account_details:
                return {
                    "status": "healthy",
                    "account_service": "operational",
                    "backend_dependencies": "connected",
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                return {
                    "status": "degraded",
                    "account_service": "data_access_issues",
                    "backend_dependencies": "unknown",
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            return {
                "status": "error",
                "account_service": "offline",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def get_adapter_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del adapter"""

        return {
            "adapter_type": "AccountServiceAdapter",
            "target_service": "AccountApplicationService",
            "status": "active",
            "compatibility_mode": "legacy_synth_format",
            "created_at": datetime.now().isoformat(),
        }


class AccountServiceIntegration:
    """
    Clase para integrar el nuevo Account Domain con el sistema legacy
    """

    def __init__(self):
        self.account_adapter: Optional[AccountServiceAdapter] = None
        self.initialized = False

    async def initialize(self):
        """Inicializar la integración Account"""

        if self.initialized:
            return

        try:
            print("🔧 Initializing Account Service Integration...")

            # Resolver AccountApplicationService del DI Container
            from ..infrastructure.di_configuration import create_production_container

            container = create_production_container()

            from ..application.services.account_service import AccountApplicationService

            account_service = await container.resolve_service(AccountApplicationService)

            if not account_service:
                raise Exception(
                    "Failed to resolve AccountApplicationService from DI Container"
                )

            print(
                f"✅ AccountApplicationService resolved: {type(account_service).__name__}"
            )

            # Crear adapter
            self.account_adapter = AccountServiceAdapter(account_service)

            print("✅ AccountServiceAdapter created")

            self.initialized = True
            print("✅ Account Service Integration initialized successfully")

        except Exception as e:
            print(f"❌ Error initializing Account Service Integration: {e}")
            print("⚠️ Will use fallback STM Service")
            self.initialized = False

    def get_account_service_adapter(self):
        """Obtener adapter para usar con el router"""

        if not self.initialized or not self.account_adapter:
            raise Exception("Account Service Integration not initialized")

        return self.account_adapter

    async def health_check(self) -> Dict[str, Any]:
        """Health check de la integración Account"""

        try:
            if not self.initialized or not self.account_adapter:
                return {
                    "status": "error",
                    "message": "Account Service Integration not initialized",
                    "fallback_available": True,
                }

            # Ejecutar health check del adapter
            adapter_health = await self.account_adapter.health_check()

            return {
                "status": "ok",
                "integration_initialized": self.initialized,
                "adapter_health": adapter_health,
                "fallback_available": True,  # Siempre disponible STM service
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Health check failed: {str(e)}",
                "fallback_available": True,
            }


# Instancia global para integración
account_service_integration = AccountServiceIntegration()
