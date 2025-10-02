#!/usr/bin/env python3
"""
Strategy Manager Implementation
Implementación para gestión del lifecycle completo de estrategias
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from ...domain.models.strategy import (
    StrategyInstance, 
    StrategyConfig, 
    StrategyStatus, 
    TradingSignal,
    SignalType
)
from ...domain.models.position import Money
from ...domain.ports.strategy_ports import IStrategyEngine
from ...domain.ports.communication_ports import IEventPublisher


class StrategyManager:
    """Manager para lifecycle completo de estrategias"""

    def __init__(
        self,
        strategy_engine: IStrategyEngine,
        event_publisher: IEventPublisher
    ):
        self.strategy_engine = strategy_engine
        self.event_publisher = event_publisher
        
        # Estado interno
        self.managed_strategies: Dict[str, StrategyInstance] = {}
        self.execution_tasks: Dict[str, asyncio.Task] = {}
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        
        # Configuración
        self.execution_interval = 30  # segundos
        self.monitoring_interval = 60  # segundos
        self.max_concurrent_strategies = 10
        self.health_check_threshold = 300  # 5 minutos sin señales

    async def register_strategy(self, strategy: StrategyInstance) -> bool:
        """Registrar estrategia para gestión automática"""
        
        try:
            # Verificar límite de estrategias concurrentes
            if len(self.managed_strategies) >= self.max_concurrent_strategies:
                await self.event_publisher.publish_strategy_event(
                    strategy.strategy_id,
                    "registration_failed",
                    {"reason": "max_concurrent_strategies_reached"}
                )
                return False
            
            # Registrar en el engine interno
            self.managed_strategies[strategy.strategy_id] = strategy
            
            # Publicar evento de registro
            await self.event_publisher.publish_strategy_event(
                strategy.strategy_id,
                "strategy_registered",
                {
                    "name": strategy.config.name,
                    "symbol": strategy.config.symbol,
                    "managed_count": len(self.managed_strategies)
                }
            )
            
            return True
            
        except Exception as e:
            await self.event_publisher.publish_strategy_event(
                strategy.strategy_id,
                "registration_error",
                {"error": str(e)}
            )
            return False

    async def start_strategy_execution(self, strategy_id: str) -> bool:
        """Iniciar ejecución automática de estrategia"""
        
        strategy = self.managed_strategies.get(strategy_id)
        if not strategy:
            return False
        
        if strategy_id in self.execution_tasks:
            return True  # Ya está ejecutándose
        
        try:
            # Iniciar task de ejecución
            execution_task = asyncio.create_task(
                self._execution_loop(strategy_id)
            )
            self.execution_tasks[strategy_id] = execution_task
            
            # Iniciar task de monitoreo
            monitoring_task = asyncio.create_task(
                self._monitoring_loop(strategy_id)
            )
            self.monitoring_tasks[strategy_id] = monitoring_task
            
            strategy.set_status(StrategyStatus.ACTIVE)
            
            await self.event_publisher.publish_strategy_event(
                strategy_id,
                "execution_started",
                {"execution_interval": self.execution_interval}
            )
            
            return True
            
        except Exception as e:
            await self.event_publisher.publish_strategy_event(
                strategy_id,
                "execution_failed",
                {"error": str(e)}
            )
            return False

    async def stop_strategy_execution(self, strategy_id: str) -> bool:
        """Detener ejecución automática de estrategia"""
        
        try:
            # Cancelar task de ejecución
            if strategy_id in self.execution_tasks:
                task = self.execution_tasks[strategy_id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                del self.execution_tasks[strategy_id]
            
            # Cancelar task de monitoreo
            if strategy_id in self.monitoring_tasks:
                task = self.monitoring_tasks[strategy_id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                del self.monitoring_tasks[strategy_id]
            
            # Actualizar estado
            strategy = self.managed_strategies.get(strategy_id)
            if strategy:
                strategy.set_status(StrategyStatus.INACTIVE)
            
            await self.event_publisher.publish_strategy_event(
                strategy_id,
                "execution_stopped",
                {"stopped_at": datetime.now().isoformat()}
            )
            
            return True
            
        except Exception as e:
            await self.event_publisher.publish_strategy_event(
                strategy_id,
                "stop_failed",
                {"error": str(e)}
            )
            return False

    async def restart_strategy(self, strategy_id: str) -> bool:
        """Reiniciar estrategia completamente"""
        
        try:
            # Detener primero
            await self.stop_strategy_execution(strategy_id)
            
            # Esperar un poco
            await asyncio.sleep(2)
            
            # Iniciar nuevamente
            success = await self.start_strategy_execution(strategy_id)
            
            await self.event_publisher.publish_strategy_event(
                strategy_id,
                "strategy_restarted",
                {"success": success}
            )
            
            return success
            
        except Exception as e:
            await self.event_publisher.publish_strategy_event(
                strategy_id,
                "restart_failed",
                {"error": str(e)}
            )
            return False

    async def get_strategy_status(self, strategy_id: str) -> Dict[str, Any]:
        """Obtener estado completo de una estrategia"""
        
        strategy = self.managed_strategies.get(strategy_id)
        if not strategy:
            return {"error": "Strategy not found"}
        
        # Estado de ejecución
        is_executing = strategy_id in self.execution_tasks
        is_monitoring = strategy_id in self.monitoring_tasks
        
        # Última actividad
        time_since_last_signal = None
        if strategy.last_signal_at:
            time_since_last_signal = (
                datetime.now() - strategy.last_signal_at
            ).total_seconds()
        
        return {
            "strategy_id": strategy_id,
            "status": strategy.status.value,
            "is_executing": is_executing,
            "is_monitoring": is_monitoring,
            "signals_generated": strategy.signals_generated,
            "last_signal_at": strategy.last_signal_at.isoformat() if strategy.last_signal_at else None,
            "time_since_last_signal": time_since_last_signal,
            "error_count": strategy.error_count,
            "last_error": strategy.last_error,
            "is_healthy": strategy.is_healthy()
        }

    async def get_all_strategies_status(self) -> Dict[str, Dict[str, Any]]:
        """Obtener estado de todas las estrategias gestionadas"""
        
        status_report = {}
        
        for strategy_id in self.managed_strategies:
            status_report[strategy_id] = await self.get_strategy_status(strategy_id)
        
        return status_report

    async def health_check_all_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Ejecutar health check en todas las estrategias"""
        
        health_report = {}
        
        for strategy_id, strategy in self.managed_strategies.items():
            health_status = await self._check_strategy_health(strategy_id, strategy)
            health_report[strategy_id] = health_status
        
        await self.event_publisher.publish_strategy_event(
            "system",
            "health_check_completed",
            {
                "total_strategies": len(health_report),
                "healthy_count": sum(1 for h in health_report.values() if h["healthy"])
            }
        )
        
        return health_report

    async def _execution_loop(self, strategy_id: str):
        """Loop principal de ejecución de estrategia"""
        
        strategy = self.managed_strategies.get(strategy_id)
        if not strategy:
            return
        
        await self.event_publisher.publish_strategy_event(
            strategy_id,
            "execution_loop_started",
            {"execution_interval": self.execution_interval}
        )
        
        try:
            while True:
                start_time = datetime.now()
                
                try:
                    # Ejecutar ciclo de trading
                    await self._execute_strategy_cycle(strategy_id)
                    
                except Exception as e:
                    await self.event_publisher.publish_strategy_event(
                        strategy_id,
                        "execution_error",
                        {"error": str(e), "cycle_time": start_time.isoformat()}
                    )
                    strategy.set_status(StrategyStatus.ERROR, str(e))
                
                # Esperar hasta el siguiente ciclo
                execution_time = (datetime.now() - start_time).total_seconds()
                sleep_time = max(0, self.execution_interval - execution_time)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                
        except asyncio.CancelledError:
            await self.event_publisher.publish_strategy_event(
                strategy_id,
                "execution_loop_stopped",
                {"stopped_at": datetime.now().isoformat()}
            )
            raise
        except Exception as e:
            await self.event_publisher.publish_strategy_event(
                strategy_id,
                "execution_loop_error",
                {"error": str(e)}
            )
            strategy.set_status(StrategyStatus.ERROR, str(e))

    async def _monitoring_loop(self, strategy_id: str):
        """Loop de monitoreo y salud de estrategia"""
        
        strategy = self.managed_strategies.get(strategy_id)
        if not strategy:
            return
        
        try:
            while True:
                # Verificar salud
                health_status = await self._check_strategy_health(strategy_id, strategy)
                
                # Si no está saludable, intentar recuperar
                if not health_status["healthy"]:
                    await self._attempt_strategy_recovery(strategy_id, health_status)
                
                # Esperar próximo check
                await asyncio.sleep(self.monitoring_interval)
                
        except asyncio.CancelledError:
            raise
        except Exception as e:
            await self.event_publisher.publish_strategy_event(
                strategy_id,
                "monitoring_error",
                {"error": str(e)}
            )

    async def _execute_strategy_cycle(self, strategy_id: str):
        """Ejecutar un ciclo completo de la estrategia"""
        
        strategy = self.managed_strategies.get(strategy_id)
        if not strategy:
            return
        
        # Simular obtención de market data
        market_data = await self._get_market_data_for_strategy(strategy)
        
        # Ejecutar estrategia usando el engine
        signal_result = await self.strategy_engine.generate_signal(
            strategy_id, market_data
        )
        
        if signal_result:
            # Manejar señal generada
            await self._handle_generated_signal(strategy_id, signal_result, market_data)

    async def _handle_generated_signal(
        self, 
        strategy_id: str, 
        signal: TradingSignal, 
        market_data: Dict[str, Any]
    ):
        """Manejar señal generada por la estrategia"""
        
        strategy = self.managed_strategies.get(strategy_id)
        if not strategy:
            return
        
        try:
            # Actualizar métricas de la estrategia
            strategy.signals_generated += 1
            strategy.last_signal_at = datetime.now()
            
            # Publicar evento de señal
            await self.event_publisher.publish_strategy_event(
                strategy_id,
                "signal_generated",
                {
                    "signal_type": signal.signal_type.value,
                    "confidence": str(signal.confidence),
                    "entry_price": str(signal.entry_price.amount),
                    "reasoning": signal.reasoning,
                    "signal_strength": signal.signal_strength.value
                }
            )
            
            # Aquí se podría integrar con el sistema de órdenes
            await self._process_generated_signal(signal, market_data)
            
        except Exception as e:
            await self.event_publisher.publish_strategy_event(
                strategy_id,
                "signal_handling_error",
                {"error": str(e)}
            )

    async def _process_generated_signal(
        self, 
        signal: TradingSignal, 
        market_data: Dict[str, Any]
    ):
        """Procesar señal generada (integración futura con sistema de órdenes)"""
        
        # Por ahora solo registrar la señal
        # En el futuro esto podría:
        # - Crear órdenes automáticamente
        # - Validar contra balance disponible
        # - Aplicar reglas de riesgo
        
        signal_data = {
            "timestamp": datetime.now().isoformat(),
            "signal_type": signal.signal_type.value,
            "confidence": float(signal.confidence),
            "entry_price": float(signal.entry_price.amount),
            "reasoning": signal.reasoning
        }
        
        # Esto iría a un sistema de persistência de señales
        pass

    async def _get_market_data_for_strategy(self, strategy: StrategyInstance) -> Dict[str, Any]:
        """Obtener datos de mercado para la estrategia"""
        
        # Simular datos de mercado (en el futuro esto vendría del MarketDataProvider)
        return {
            "symbol": strategy.config.symbol,
            "current_price": 0.085,  # Mock DOGE price
            "volume": 1000000,
            "timestamp": datetime.now().isoformat(),
            "price_change_24h": 0.02  # +2%
        }

    async def _check_strategy_health(self, strategy_id: str, strategy: StrategyInstance) -> Dict[str, Any]:
        """Verificar salud de una estrategia"""
        
        health_status = {
            "healthy": True,
            "issues": [],
            "last_check": datetime.now().isoformat()
        }
        
        # Verificar estado actual
        if strategy.status == StrategyStatus.ERROR:
            health_status["healthy"] = False
            health_status["issues"].append(f"Strategy in ERROR state: {strategy.last_error}")
        
        # Verificar últimas señales
        if strategy.last_signal_at:
            time_since_signal = (
                datetime.now() - strategy.last_signal_at
            ).total_seconds()
            
            if time_since_signal > self.health_check_threshold:
                health_status["issues"].append(
                    f"No signals for {time_since_signal:.0f} seconds"
                )
        
        # Verificar frecuencia de errores
        if strategy.error_count > 3:
            health_status["issues"].append(f"High error count: {strategy.error_count}")
        
        if health_status["issues"]:
            health_status["healthy"] = False
        
        return health_status

    async def _attempt_strategy_recovery(self, strategy_id: str, health_status: Dict[str, Any]):
        """Intentar recuperar estrategia con problemas"""
        
        try:
            await self.event_publisher.publish_strategy_event(
                strategy_id,
                "recovery_attempt",
                {"issues": health_status["issues"]}
            )
            
            # Si hay errores críticos, reiniciar la estrategia
            if len(health_status["issues"]) > 2:
                await self.restart_strategy(strategy_id)
            
        except Exception as e:
            await self.event_publisher.publish_strategy_event(
                strategy_id,
                "recovery_failed",
                {"error": str(e)}
            )

    async def shutdown_all_strategies(self):
        """Detener todas las estrategias gestionadas"""
        
        shutdown_tasks = []
        
        for strategy_id in list(self.execution_tasks.keys()):
            shutdown_tasks.append(self.stop_strategy_execution(strategy_id))
        
        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)
        
        await self.event_publisher.publish_strategy_event(
            "system",
            "all_strategies_shutdown",
            {"total_shutdown": len(shutdown_tasks)}
        )

    def get_manager_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del manager"""
        
        return {
            "managed_strategies": len(self.managed_strategies),
            "executing_strategies": len(self.execution_tasks),
            "monitoring_strategies": len(self.monitoring_tasks),
            "max_concurrent": self.max_concurrent_strategies,
            "execution_interval": self.execution_interval,
            "monitoring_interval": self.monitoring_interval,
            "health_threshold": self.health_check_threshold,
            "strategy_ids": list(self.managed_strategies.keys())
        }
