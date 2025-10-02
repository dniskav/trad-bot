#!/usr/bin/env python3
"""
Strategy Application Service
Servicio de aplicación para gestión de estrategias de trading
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

from ...domain.models.strategy import (
    StrategyConfig, 
    StrategyInstance, 
    StrategyStatus, 
    TradingSignal, 
    SignalType,
    SignalGenerationResult
)
from ...domain.models.account import AssetType
from ...domain.models.position import Money
from ...domain.ports.strategy_ports import (
    IStrategyEngine,
    IIndicatorService,
    ISignalEvaluator,
    IStrategyRepository,
    IRiskManager,
    IStrategyPerformanceTracker
)
from ...domain.ports.communication_ports import IEventPublisher


class StrategyApplicationService:
    """Servicio de aplicación para Strategy Domain"""

    def __init__(
        self,
        strategy_engine: IStrategyEngine,
        indicator_service: IIndicatorService,
        signal_evaluator: ISignalEvaluator,
        strategy_repository: IStrategyRepository,
        risk_manager: IRiskManager,
        performance_tracker: IStrategyPerformanceTracker,
        event_publisher: IEventPublisher
    ):
        self.strategy_engine = strategy_engine
        self.indicator_service = indicator_service
        self.signal_evaluator = signal_evaluator
        self.strategy_repository = strategy_repository
        self.risk_manager = risk_manager
        self.performance_tracker = performance_tracker
        self.event_publisher = event_publisher

    async def create_strategy(self, config: StrategyConfig) -> Optional[StrategyInstance]:
        """Crear nueva estrategia"""
        
        # Validar configuración
        errors = config.validate_config()
        if errors:
            await self.event_publisher.publish_strategy_event(
                config.name,
                f"strategy_config_error: {'; '.join(errors)}"
            )
            return None
        
        # Verificar que no existe estrategia con el mismo nombre
        existing = await self.strategy_repository.get_strategy_by_name(config.name)
        if existing:
            return None  # Ya existe
        
        # Crear instancia de estrategia
        strategy_instance = StrategyInstance(
            strategy_id=f"{config.name}_{int(datetime.now().timestamp())}",
            config=config
        )
        
        # Registrar con el engine
        await self.strategy_engine.register_strategy(strategy_instance)
        
        # Guardar en repositorio
        await self.strategy_repository.save_strategy(strategy_instance)
        
        # Publicar evento
        await self.event_publisher.publish_strategy_event(
            strategy_instance.strategy_id,
            "strategy_created",
            {"name": config.name, "symbol": config.symbol}
        )
        
        return strategy_instance

    async def start_strategy(self, strategy_id: str) -> bool:
        """Iniciar ejecución de estrategia"""
        
        strategy = await self.strategy_repository.get_strategy(strategy_id)
        if not strategy:
            return False
        
        if strategy.status == StrategyStatus.ACTIVE:
            return True  # Ya está activa
        
        # Activar en el engine
        success = await self.strategy_engine.start_strategy(strategy_id)
        
        if success:
            strategy.set_status(StrategyStatus.ACTIVE)
            await self.strategy_repository.save_strategy(strategy)
            
            # Publicar evento
            await self.event_publisher.publish_strategy_event(
                strategy_id,
                "strategy_started",
                {"symbol": strategy.config.symbol}
            )
            
            return True
        
        return False

    async def stop_strategy(self, strategy_id: str) -> bool:
        """Detener ejecución de estrategia"""
        
        strategy = await self.strategy_repository.get_strategy(strategy_id)
        if not strategy:
            return False
        
        if strategy.status == StrategyStatus.INACTIVE:
            return True  # Ya está inactiva
        
        # Detener en el engine
        success = await self.strategy_engine.stop_strategy(strategy_id)
        
        if success:
            strategy.set_status(StrategyStatus.INACTIVE)
            await self.strategy_repository.save_strategy(strategy)
            
            # Publicar evento
            await self.event_publisher.publish_strategy_event(
                strategy_id,
                "strategy_stopped",
                {"symbol": strategy.config.symbol}
            )
            
            return True
        
        return False

    async def generate_signal(
        self, 
        strategy_id: str, 
        market_data: Dict[str, Any]
    ) -> Optional[TradingSignal]:
        """Generar señal de trading para una estrategia"""
        
        strategy = await self.strategy_repository.get_strategy(strategy_id)
        if not strategy or strategy.status != StrategyStatus.ACTIVE:
            return None
        
        # Obtener datos de indicadores
        indicators_data = {}
        for indicator_config in strategy.config.indicators:
            if indicator_config.enabled:
                try:
                    indicator_data = await self.indicator_service.calculate_indicator(
                        indicator_config.indicator_type.value,
                        indicator_config.params,
                        market_data
                    )
                    indicators_data[indicator_config.name] = indicator_data
                except Exception as e:
                    await self.event_publisher.publish_strategy_event(
                        strategy_id,
                        "indicator_error",
                        {"indicator": indicator_config.name, "error": str(e)}
                    )
                    continue
        
        # Evaluar señales usando SignalEvaluator
        signal_result = await self.signal_evaluator.evaluate_signals(
            strategy.config.signals,
            indicators_data,
            market_data
        )
        
        if not signal_result.signal:
            return None  # No se generó señal
        
        # Aplicar gestión de riesgo
        if strategy.config.risk_management.enabled:
            # Obtener balance actual de cuenta
            account_balance = await self.get_account_balance_for_strategy(strategy_id)
            if account_balance and account_balance.amount < Money.from_float(10.0).amount:
                await self.event_publisher.publish_strategy_event(
                    strategy_id,
                    "insufficient_balance",
                    {"required": "10.0", "available": str(account_balance.amount)}
                )
                return None
            
            signal_result.signal = await self.risk_manager.apply_risk_management(
                signal_result.signal,
                account_balance.amount if account_balance else 0
            )
        
        if signal_result.signal:
            # Actualizar métricas de la estrategia
            strategy.signals_generated += 1
            strategy.last_signal_at = datetime.now()
            
            # Guardar cambios
            await self.strategy_repository.save_strategy(strategy)
            
            # Registrar performance
            await self.performance_tracker.record_signal_generated(
                strategy_id, 
                signal_result.signal
            )
            
            # Publicar evento
            await self.event_publisher.publish_strategy_event(
                strategy_id,
                "signal_generated",
                {
                    "signal_type": signal_result.signal.signal_type.value,
                    "confidence": str(signal_result.signal.confidence),
                    "reasoning": signal_result.signal.reasoning
                }
            )
        
        return signal_result.signal

    async def update_strategy_config(
        self, 
        strategy_id: str, 
        new_config: StrategyConfig
    ) -> bool:
        """Actualizar configuración de estrategia"""
        
        strategy = await self.strategy_repository.get_strategy(strategy_id)
        if not strategy or strategy.status == StrategyStatus.ACTIVE:
            return False  # Solo se puede actualizar si está inactiva
        
        # Validar nueva configuración
        errors = new_config.validate_config()
        if errors:
            return False
        
        # Validar que el cambio no rompe consistencia
        if await self.validate_strategy_safety(strategy_id, new_config):
            strategy.config = new_config
            strategy.config.updated_at = datetime.now()
            
            # Guardar cambios
            await self.strategy_repository.save_strategy(strategy)
            
            # Actualizar engine si es necesario
            await self.strategy_engine.update_strategy_config(strategy_id, new_config)
            
            # Publicar evento
            await self.event_publisher.publish_strategy_event(
                strategy_id,
                "strategy_config_updated",
                {"updated_at": strategy.config.updated_at.isoformat()}
            )
            
            return True
        
        return False

    async def get_strategy_performance(self, strategy_id: str) -> Dict[str, Any]:
        """Obtener performance de estrategia"""
        
        strategy = await self.strategy_repository.get_strategy(strategy_id)
        if not strategy:
            return {}
        
        # Obtener métricas adicionales del tracker
        performance_data = await self.performance_tracker.get_strategy_performance(
            strategy_id
        )
        
        # Combinar datos de estrategia y tracker
        base_summary = strategy.get_status_summary()
        
        return {
            **base_summary,
            **performance_data,
            "is_healthy": strategy.is_healthy()
        }

    async def evaluate_strategy_safety(
        self, 
        strategy_id: str
    ) -> Dict[str, Any]:
        """Evaluar seguridad y health de una estrategia"""
        
        strategy = await self.strategy_repository.get_strategy(strategy_id)
        if not strategy:
            return {"safe": False, "reasons": ["Strategy not found"]}
        
        safety_report = {
            "safe": True,
            "reasons": [],
            "warnings": []
        }
        
        # Verificar estado actual
        if strategy.status == StrategyStatus.ERROR:
            safety_report["safe"] = False
            safety_report["reasons"].append(f"Strategy in ERROR state: {strategy.last_error}")
        
        # Verificar métricas de pérdidas
        if abs(strategy.total_pnl.amount) > Money.from_float(1000.0).amount:
            safety_report["warnings"].append("High total P&L exposure")
        
        # Verificar win rate bajo
        if strategy.signals_generated > 10 and strategy.win_rate < 0.3:
            safety_report["warnings"].append("Low win rate detected")
        
        # Verificar frecuencia de errores
        if strategy.error_count > 5:
            safety_report["warnings"].append("High error count")
        
        # Verificar última actividad
        if strategy.last_signal_at:
            time_since_signal = (datetime.now() - strategy.last_signal_at).total_seconds()
            if time_since_signal > 7200:  # 2 horas sin señales
                safety_report["warnings"].append("No signals for extended period")
        
        return safety_report

    async def get_account_balance_for_strategy(self, strategy_id: str) -> Optional[Money]:
        """Obtener balance de cuenta asociada a la estrategia"""
        
        # Esto sería una integración con AccountDomain
        # Por ahora retornamos un valor mock
        return Money.from_float(1000.0)  # Mock $1000 balance

    async def validate_strategy_safety(
        self, 
        strategy_id: str, 
        new_config: StrategyConfig
    ) -> bool:
        """Validar que cambios en configuración son seguros"""
        
        current_strategy = await self.strategy_repository.get_strategy(strategy_id)
        if not current_strategy:
            return False
        
        # Verificar que los cambios no introducen riesgos críticos
        if new_config.risk_management.position_size > 0.05:  # Máximo 5%
            return False
        
        if new_config.risk_management.max_daily_loss > 0.10:  # Máximo 10%
            return False
        
        # Verificar que tiene al menos una señal configurada
        if not new_config.signals:
            return False
        
        return True

    async def run_strategy_health_check(self) -> Dict[str, Dict[str, Any]]:
        """Ejecutar health check en todas las estrategias activas"""
        
        active_strategies = await self.strategy_repository.get_strategies_by_status(
            StrategyStatus.ACTIVE
        )
        
        health_report = {}
        
        for strategy in active_strategies:
            safety_report = await self.evaluate_strategy_safety(strategy.strategy_id)
            health_report[strategy.strategy_id] = {
                "strategy_name": strategy.config.name,
                "symbol": strategy.config.symbol,
                "safe": safety_report["safe"],
                "healthy": strategy.is_healthy(),
                "performance": await self.get_strategy_performance(strategy.strategy_id),
                "issues": safety_report["reasons"],
                "warnings": safety_report["warnings"]
            }
        
        # Publicar reporte de salud
        await self.event_publisher.publish_strategy_event(
            "system",
            "health_check_completed",
            {"reporting_strategies": len(health_report)}
        )
        
        return health_report

    async def get_all_strategies_summary(self) -> Dict[str, Any]:
        """Obtener resumen de todas las estrategias"""
        
        all_strategies = await self.strategy_repository.get_all_strategies()
        
        summary = {
            "total_strategies": len(all_strategies),
            "by_status": {},
            "by_symbol": {},
            "global_metrics": {
                "total_signals": 0,
                "active_strategies": 0,
                "problem_strategies": 0
            }
        }
        
        for strategy in all_strategies:
            status = strategy.status.value
            symbol = strategy.config.symbol
            
            # Contar por estado
            summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
            
            # Contar por símbolo
            summary["by_symbol"][symbol] = summary["by_symbol"].get(symbol, 0) + 1
            
            # Métricas globales
            summary["global_metrics"]["total_signals"] += strategy.signals_generated
            
            if strategy.status == StrategyStatus.ACTIVE:
                summary["global_metrics"]["active_strategies"] += 1
            
            if not strategy.is_healthy():
                summary["global_metrics"]["problem_strategies"] += 1
        
        return summary
