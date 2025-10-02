#!/usr/bin/env python3
"""
Strategy Service Adapter
Adaptador para conectar el router existente con el nuevo StrategyApplicationService
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from ...domain.models.strategy import StrategyConfig, StrategyInstance, StrategyStatus
from ..application.services.strategy_service import StrategyApplicationService


class StrategyServiceAdapter:
    """
    Adapter que adapta el StrategyApplicationService a la interfaz esperada por el router
    Este adapter mantiene compatibilidad con la API existente mientras usa la nueva arquitectura
    """

    def __init__(self, strategy_application_service: StrategyApplicationService):
        self.strategy_service = strategy_application_service

        # Cache para estrategias cargadas desde archivos config
        self._loaded_strategies_cache: Dict[str, StrategyInstance] = {}

        # Referencias a estrategias por nombre para compatibilidad con router
        self._strategy_by_name: Dict[str, str] = {}  # name -> strategy_id mapping

    async def get_all_strategies(self) -> Dict[str, StrategyInstance]:
        """Obtener todas las estrategias en formato compatible con router"""

        try:
            # Obtener estrategias del nuevo servicio
            summary = await self.strategy_service.get_all_strategies_summary()

            # Para compatibilidad con el router, necesitamos crear un dict por nombre
            strategies_dict = {}

            # Combinar estrategias del nuevo servicio
            all_strategies = (
                await self.strategy_service.strategy_repository.get_all_strategies()
            )

            for strategy in all_strategies:
                strategies_dict[strategy.config.name] = strategy

            # Combinar con estrategias cargadas desde archivos config
            for name, strategy in self._loaded_strategies_cache.items():
                strategies_dict[name] = strategy

            return strategias_dict

        except Exception as e:
            print(f"Error getting all strategies: {e}")
            return self._loaded_strategies_cache

    async def get_strategy(self, strategy_name: str) -> Optional[StrategyInstance]:
        """Obtener estrategia específica por nombre"""

        # Buscar en estrategias del nuevo servicio
        try:
            strategy = (
                await self.strategy_service.strategy_repository.get_strategy_by_name(
                    strategy_name
                )
            )
            if strategy:
                return strategy
        except Exception as e:
            print(f"Error getting strategy {strategy_name} from repository: {e}")

        # Buscar en cache de estrategias cargadas desde archivos
        return self._loaded_strategies_cache.get(strategy_name)

    async def start_strategy(self, strategy_name: str) -> bool:
        """Iniciar estrategia por nombre"""

        strategy = await self.get_strategy(strategy_name)
        if not strategy:
            return False

        return await self.strategy_service.start_strategy(strategy.strategy_id)

    async def stop_strategy(self, strategy_name: str) -> bool:
        """Detener estrategia por nombre"""

        strategy = await self.get_strategy(strategy_name)
        if not strategy:
            return False

        return await self.strategy_service.stop_strategy(strategy.strategy_id)

    async def reload_strategy(self, strategy_name: str) -> bool:
        """Recargar estrategia (compatibilidad con router original)"""

        # Detener primero
        stopped = await self.stop_strategy(strategy_name)

        if stopped:
            # Reiniciar
            return await self.start_strategy(strategy_name)

        return False

    def get_strategy_config(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """Obtener configuración de estrategia"""

        strategy = self._get_strategy_sync(strategy_name)
        if not strategy:
            return None

        # Convertir config a dict compatible con API
        config_dict = {
            "name": strategy.config.name,
            "description": strategy.config.description,
            "symbol": strategy.config.symbol,
            "timeframe": strategy.config.timeframe,
            "enabled": strategy.config.enabled,
            "indicators": [
                {
                    "name": ind.name,
                    "type": ind.indicator_type.value,
                    "params": ind.params,
                    "weight": ind.weight,
                    "enabled": ind.enabled,
                }
                for ind in strategy.config.indicators
            ],
            "signals": [
                {
                    "name": sig.name,
                    "type": sig.signal_type.value,
                    "conditions": [
                        {
                            "indicator": cond.indicator,
                            "operator": cond.operator,
                            "value": cond.value,
                            "enabled": cond.enabled,
                        }
                        for cond in sig.conditions
                    ],
                    "logic_type": sig.logic_type,
                    "min_confidence": sig.min_confidence,
                    "enabled": sig.enabled,
                }
                for sig in strategy.config.signals
            ],
            "risk_management": {
                "enabled": strategy.config.risk_management.enabled,
                "position_size": strategy.config.risk_management.position_size,
                "stop_loss_pct": strategy.config.risk_management.stop_loss_pct,
                "take_profit_pct": strategy.config.risk_management.take_profit_pct,
                "max_daily_loss": strategy.config.risk_management.max_daily_loss,
            },
        }

        return config_dict

    async def get_strategy_performance(
        self, strategy_name: str
    ) -> Optional[Dict[str, Any]]:
        """Obtener métricas de performance de estrategia"""

        strategy = await self.get_strategy(strategy_name)
        if not strategy:
            return None

        return await self.strategy_service.get_strategy_performance(
            strategy.strategy_id
        )

    def get_available_configs(self) -> List[str]:
        """Obtener lista de archivos de configuración disponibles"""

        # Esta función mantiene compatibilidad con el router original
        # En el futuro esto podría cargar desde el FileStrategyRepository

        import os

        config_dir = "backend/v0_2/server/strategies/configs"
        if not os.path.exists(config_dir):
            return []

        configs = []
        for file in os.listdir(config_dir):
            if file.endswith(".json"):
                config_name = file.replace(".json", "")
                configs.append(config_name)

        return sorted(configs)

    async def load_strategy(self, strategy_name: str) -> bool:
        """Cargar estrategia desde archivo de configuración"""

        try:
            # Cargar configuración desde archivo usando el repositorio
            config_file_path = (
                f"backend/v0_2/server/strategies/configs/{strategy_name}.json"
            )
            strategy_config = self.strategy_service.strategy_repository.load_strategy_from_config_file(
                config_file_path
            )

            if not strategy_config:
                return False

            # Crear instancia de estrategia
            strategy_instance = StrategyInstance(
                strategy_id=f"{strategy_name}_{int(datetime.now().timestamp())}",
                config=strategy_config,
                status=StrategyStatus.INACTIVE,
            )

            # Guardar en repositorio
            await self.strategy_service.strategy_repository.save_strategy(
                strategy_instance
            )

            # Agregar a cache local para compatibilidad con router
            self._loaded_strategies_cache[strategy_name] = strategy_instance

            return True

        except Exception as e:
            print(f"Error loading strategy {strategy_name}: {e}")
            return False

    async def unload_strategy(self, strategy_name: str) -> bool:
        """Descargar estrategia de memoria"""

        try:
            strategy = await self.get_strategy(strategy_name)
            if not strategy:
                return False

            # Detener si está corriendo
            await self.strategy_service.stop_strategy(strategy.strategy_id)

            # Eliminar de repositorio
            await self.strategy_service.strategy_repository.delete_strategy(
                strategy.strategy_id
            )

            # Eliminar de cache local
            if strategy_name in self._loaded_strategies_cache:
                del self._loaded_strategies_cache[strategy_name]

            return True

        except Exception as e:
            print(f"Error unloading strategy {strategy_name}: {e}")
            return False

    def _get_strategy_sync(self, strategy_name: str) -> Optional[StrategyInstance]:
        """Versión síncrona para obtener estrategia (para usar en get_config)"""

        # Buscar en cache primero
        if strategy_name in self._loaded_strategies_cache:
            return self._loaded_strategies_cache[strategy_name]

        # Si no está en cache, crear una versión simplificada para compatibilidad
        # Esto es temporal hasta que el adapter esté completamente integrado

        try:
            import os

            config_file_path = (
                f"backend/v0_2/server/strategies/configs/{strategy_name}.json"
            )

            if os.path.exists(config_file_path):
                # Crear estrategia temporal desde archivo config
                config = self.strategy_service.strategy_repository.load_strategy_from_config_file(
                    config_file_path
                )
                if config:
                    strategy_instance = StrategyInstance(
                        strategy_id=f"{strategy_name}_temp",
                        config=config,
                        status=StrategyStatus.INACTIVE,
                    )

                    self._loaded_strategies_cache[strategy_name] = strategy_instance
                    return strategy_instance

        except Exception as e:
            print(f"Error creating sync strategy {strategy_name}: {e}")

        return None

    async def create_strategy_from_config(
        self, strategy_config: StrategyConfig
    ) -> Optional[str]:
        """Crear nueva estrategia desde configuración"""

        try:
            strategy_instance = await self.strategy_service.create_strategy(
                strategy_config
            )
            if strategy_instance:
                # Agregar a cache para compatibilidad
                self._loaded_strategies_cache[strategy_instance.config.name] = (
                    strategy_instance
                )
                return strategy_instance.strategy_id

            return None

        except Exception as e:
            print(f"Error creating strategy from config: {e}")
            return None

    async def health_check(self) -> Dict[str, Any]:
        """Ejecutar health check en todas las estrategias"""

        try:
            health_report = await self.strategy_service.run_strategy_health_check()

            return {
                "total_strategies": len(health_report),
                "healthy_strategies": sum(
                    1 for h in health_report.values() if h.get("healthy", False)
                ),
                "report": health_report,
            }

        except Exception as e:
            print(f"Error running health check: {e}")
            return {"error": str(e), "total_strategies": 0, "healthy_strategies": 0}

    def get_adapter_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del adapter"""

        return {
            "loaded_strategies_cache_size": len(self._loaded_strategies_cache),
            "cached_strategy_names": list(self._loaded_strategies_cache.keys()),
            "strategy_name_mappings": len(self._strategy_by_name),
            "adapter_status": "active",
        }
