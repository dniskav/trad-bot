#!/usr/bin/env python3
"""
Strategy Service Integration
Integración del nuevo Strategy Domain con el sistema legacy de routers
"""

import asyncio
from typing import Optional

from ..infrastructure.di_configuration import create_production_container
from ..infrastructure.adapters.domain.strategy_service_adapter import (
    StrategyServiceAdapter,
)
from ..application.services.strategy_service import StrategyApplicationService
from .services.binance_service import BinanceService


class StrategyServiceIntegration:
    """
    Clase para integrar el nuevo Strategy Domain con el sistema legacy
    """

    def __init__(self):
        self.container = None
        self.strategy_application_service: Optional[StrategyApplicationService] = None
        self.strategy_adapter: Optional[StrategyServiceAdapter] = None
        self.initialized = False

    async def initialize(self, binance_service: BinanceService):
        """Inicializar la integración con servicios externos"""

        if self.initialized:
            return

        try:
            print("🔧 Initializing Strategy Service Integration...")

            # Configurar DI Container
            self.container = create_production_container()

            # Resolver StrategyApplicationService
            self.strategy_application_service = await self.container.resolve_service(
                StrategyApplicationService
            )

            if not self.strategy_application_service:
                raise Exception(
                    "Failed to resolve StrategyApplicationService from DI Container"
                )

            print(
                f"✅ StrategyApplicationService resolved: {type(self.strategy_application_service).__name__}"
            )

            # Crear adapter que conecta con el router legacy
            self.strategy_adapter = StrategyServiceAdapter(
                self.strategy_application_service
            )

            print("✅ StrategyServiceAdapter created")

            # Cargar estrategias iniciales desde archivos config
            await self._load_initial_strategies()

            self.initialized = True
            print("✅ Strategy Service Integration initialized successfully")

        except Exception as e:
            print(f"❌ Error initializing Strategy Service Integration: {e}")
            print("⚠️ Falling back to legacy StrategyService")
            self.initialized = False

    async def _load_initial_strategies(self):
        """Cargar estrategias iniciales desde archivos de configuración"""

        try:
            # Lista de estrategias a cargar automáticamente
            auto_load_strategies = [
                "simple_trend_strategy",
                "rsi_strategy",
                "macd_strategy",
                "sma_cross_strategy",
            ]

            loaded_count = 0

            for strategy_name in auto_load_strategies:
                try:
                    success = await self.strategy_adapter.load_strategy(strategy_name)
                    if success:
                        loaded_count += 1
                        print(f"✅ Loaded strategy: {strategy_name}")
                    else:
                        print(f"⚠️ Failed to load strategy: {strategy_name}")

                except Exception as e:
                    print(f"❌ Error loading strategy {strategy_name}: {e}")

            print(
                f"📊 Strategy Loading Summary: {loaded_count}/{len(auto_load_strategies)} strategies loaded"
            )

        except Exception as e:
            print(f"❌ Error in initial strategy loading: {e}")

    def get_strategy_service_adapter(self):
        """Obtener adapter para usar con el router"""

        if not self.initialized or not self.strategy_adapter:
            raise Exception("Strategy Service Integration not initialized")

        return self.strategy_adapter

    async def shutdown(self):
        """Apagar la integración"""

        if self.initialized and self.strategy_adapter:
            try:
                # Obtener todas las estrategias gestionadas y detenerlas
                all_strategies = await self.strategy_adapter.get_all_strategies()

                for name, strategy in all_strategies.items():
                    try:
                        await self.strategy_adapter.stop_strategy(name)
                        print(f"🛑 Stopped strategy: {name}")
                    except Exception as e:
                        print(f"⚠️ Error stopping strategy {name}: {e}")

                print("✅ Strategy Service Integration shutdown completed")

            except Exception as e:
                print(f"❌ Error during Strategy Service Integration shutdown: {e}")

        self.initialized = False

    async def health_check(self) -> dict:
        """Health check de la integración"""

        try:
            if not self.initialized or not self.strategy_adapter:
                return {
                    "status": "error",
                    "message": "Strategy Service Integration not initialized",
                }

            # Ejecutar health check en estrategias
            health_report = await self.strategy_adapter.health_check()

            # Estadísticas del adapter
            adapter_stats = self.strategy_adapter.get_adapter_stats()

            return {
                "status": "ok",
                "integration_initialized": self.initialized,
                "total_strategies": health_report.get("total_strategies", 0),
                "healthy_strategies": health_report.get("healthy_strategies", 0),
                "adapter_stats": adapter_stats,
                "timestamp": asyncio.get_event_loop().time(),
            }

        except Exception as e:
            return {"status": "error", "message": f"Health check failed: {str(e)}"}


# Instancia global para integración
strategy_service_integration = StrategyServiceIntegration()
