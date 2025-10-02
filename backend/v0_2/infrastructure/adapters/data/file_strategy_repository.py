#!/usr/bin/env python3
"""
File Strategy Repository Implementation
Implementación de IStrategyRepository usando persistencia en archivos JSON
"""

import os
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from ...domain.models.strategy import (
    StrategyInstance, 
    StrategyConfig, 
    StrategyStatus
)
from ...domain.ports.base_types import RepositoryResult
from ...domain.ports.strategy_ports import IStrategyRepository
from ...infrastructure.persistence.file_repository import JsonStore


class FileStrategyRepository:
    """Repositorio de estrategias implementado con persistencia en archivos JSON"""

    def __init__(self, data_dir: str = None):
        # Usar data dir por defecto si no se especifica directamente
        if data_dir is None:
            self.data_dir = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "..", "data"
            )
        else:
            self.data_dir = data_dir

        # Crear directorio si no existe
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)

        # Inicializar JsonStore
        self.store = JsonStore(self.data_dir)
        self.strategies_file = "strategies"

    async def get_strategy(self, strategy_id: str) -> Optional[StrategyInstance]:
        """Obtener estrategia por ID"""
        try:
            strategies_data = self._load_strategies()
            
            # Buscar estrategia específica
            for strategy_data in strategies_data:
                if strategy_data.get("strategy_id") == strategy_id:
                    return self._deserialize_strategy(strategy_data)
            
            return None
            
        except Exception as e:
            raise Exception(f"Error getting strategy {strategy_id}: {str(e)}")

    async def get_strategy_by_name(self, name: str) -> Optional[StrategyInstance]:
        """Obtener estrategia por nombre"""
        try:
            strategies_data = self._load_strategies()
            
            # Buscar estrategia específica
            for strategy_data in strategies_data:
                strategy_config = strategy_data.get("config", {})
                if strategy_config.get("name") == name:
                    return self._deserialize_strategy(strategy_data)
            
            return None
            
        except Exception as e:
            raise Exception(f"Error getting strategy by name {name}: {str(e)}")

    async def save_strategy(self, strategy: StrategyInstance) -> None:
        """Guardar estrategia"""
        try:
            strategies_data = self._load_strategies()
            
            # Buscar si ya existe
            existing_index = None
            for i, strategy_data in enumerate(strategies_data):
                if strategy_data.get("strategy_id") == strategy.strategy_id:
                    existing_index = i
                    break
            
            # Convertir estrategia a dict
            strategy_dict = self._serialize_strategy(strategy)
            
            if existing_index is not None:
                # Actualizar estrategia existente
                strategies_data[existing_index] = strategy_dict
            else:
                # Agregar nueva estrategia
                strategies_data.append(strategy_dict)
                
            self._save_strategies(strategies_data)
            
        except Exception as e:
            raise Exception(f"Error saving strategy {strategy.strategy_id}: {str(e)}")

    async def delete_strategy(self, strategy_id: str) -> bool:
        """Eliminar estrategia"""
        try:
            strategies_data = self._load_strategies()
            
            # Buscar estrategia
            for i, strategy_data in enumerate(strategies_data):
                if strategy_data.get("strategy_id") == strategy_id:
                    strategies_data.pop(i)
                    self._save_strategies(strategies_data)
                    return True
            
            return False
            
            
        except Exception as e:
            raise Exception(f"Error deleting strategy {strategy_id}: {str(e)}")

    async def get_all_strategies(self) -> List[StrategyInstance]:
        """Obtener todas las estrategias"""
        try:
            strategies_data = self._load_strategies()
            
            strategies = []
            for strategy_data in strategies_data:
                try:
                    strategy = self._deserialize_strategy(strategy_data)
                    strategies.append(strategy)
                except Exception as e:
                    # Skip estrategias con errores
                    continue
            
            return strategies
            
        except Exception as e:
            raise Exception(f"Error getting all strategies: {str(e)}")

    async def get_strategies_by_status(self, status: StrategyStatus) -> List[StrategyInstance]:
        """Obtener estrategias por estado"""
        try:
            strategies_data = self._load_strategies()
            
            strategies = []
            for strategy_data in strategies_data:
                if strategy_data.get("status") == status.value:
                    try:
                        strategy = self._deserialize_strategy(strategy_data)
                        strategies.append(strategy)
                    except Exception as e:
                        # Skip estrategias con errores
                        continue
            
            return strategies
            
        except Exception as e:
            raise Exception(f"Error getting strategies by status {status}: {str(e)}")

    async def get_strategies_by_symbol(self, symbol: str) -> List[StrategyInstance]:
        """Obtener estrategias por símbolo"""
        try:
            strategies_data = self._load_strategies()
            
            strategies = []
            for strategy_data in strategies_data:
                strategy_config = strategy_data.get("config", {})
                if strategy_config.get("symbol") == symbol:
                    try:
                        strategy = self._deserialize_strategy(strategy_data)
                        strategies.append(strategy)
                    except Exception as e:
                        # Skip estrategias con errores
                        continue
            
            return strategies
            
        except Exception as e:
            raise Exception(f"Error getting strategies by symbol {symbol}: {str(e)}")

    def _load_strategies(self) -> List[Dict[str, Any]]:
        """Cargar datos de estrategias"""
        try:
            strategies_data = self.store.read(self.strategies_file, [])
            
            # Validar campos de timestamp si es necesario
            for strategy_data in strategies_data:
                if "created_at" in strategy_data and isinstance(
                    strategy_data["created_at"], str
                ):
                    try:
                        from datetime import datetime

                        datetime.fromisoformat(
                            strategy_data["created_at"].replace("Z", "+00:00")
                        )
                    except:
                        strategy_data["created_at"] = datetime.now().isoformat()

                if "updated_at" in strategy_data and isinstance(
                    strategy_data["updated_at"], str
                ):
                    try:
                        from datetime import datetime

                        datetime.fromisoformat(
                            strategy_data["updated_at"].replace("Z", "+00:00")
                        )
                    except:
                        strategy_data["updated_at"] = datetime.now().isoformat()

            return strategies_data
            
        except Exception as e:
            # Si hay error cargando, retornar lista vacía
            print(f"Warning: Failed to load strategies: {e}")
            return []

    def _save_strategies(self, strategies_data: List[Dict[str, Any]]) -> None:
        """Guardar datos de estrategias"""
        self.store.write(self.strategies_file, strategies_data)

    def _serialize_strategy(self, strategy: StrategyInstance) -> Dict[str, Any]:
        """Serializar estrategia para almacenamiento"""
        from ...domain.models.strategy import StrategyConfig, RiskManagement, IndicatorConfig, SignalConfig
        
        # Serializar configuración
        config_dict = {
            "name": strategy.config.name,
            "description": strategy.config.description,
            "version": strategy.config.version,
            "author": strategy.config.author,
              symbol: strategy.config.symbol,
            "timeframe": strategy.config.timeframe,
            "enabled": strategy.config.enabled,
            "indicators": [
                {
                    "name": ind.name,
                    "indicator_type": ind.indicator_type.value,
                    "params": ind.params,
                    "enabled": ind.enabled,
                    "weight": ind.weight,
                    "timeframe": ind.timeframe
                }
                for ind in strategy.config.indicators
            ],
            "signals": [
                {
                    "name": sig.name,
                    "signal_type": sig.signal_type.value,
                    "conditions": [
                        {
                            "indicator": condition.indicator,
                            "operator": condition.operator,
                            "value": condition.value,
                            "enabled": condition.enabled
                        }
                        for condition in sig.conditions
                    ],
                    "enabled": sig.enabled,
                    "logic_type": sig.logic_type,
                    "min_confidence": sig.min_confidence,
                    "description": sig.description
                }
                for sig in strategy.config.signals
            ],
            "risk_management": {
                "enabled": strategy.config.risk_management.enabled,
                "max_positions": strategy.config.risk_management.max_positions,
                "position_size": strategy.config.risk_management.position_size,
                "stop_loss_pct": strategy.config.risk_management.stop_loss_pct,
                "take_profit_pct": strategy.config.risk_management.take_profit_pct,
                "max_daily_loss": strategy.config.risk_management.max_daily_loss
            },
            "custom_params": strategy.config.custom_params,
            "created_at": strategy.config.created_at.isoformat(),
            "updated_at": strategy.config.updated_at.isoformat()
        }

        return {
            "strategy_id": strategy.strategy_id,
            "config": config_dict,
            "status": strategy.status.value,
            "created_at": strategy.created_at.isoformat(),
            "last_signal_at": strategy.last_signal_at.isoformat() if strategy.last_signal_at else None,
            "signals_generated": strategy.signals_generated,
            "signals_successful": strategy.signals_successful,
            "total_pnl": str(strategy.total_pnl.amount),
            "win_rate": strategy.win_rate,
            "max_drawdown": str(strategy.max_drawdown.amount),
            "sharpe_ratio": strategy.sharpe_ratio,
            "market_data": strategy.market_data,
            "error_count": strategy.error_count,
            "last_error": strategy.last_error
        }

    def _deserialize_strategy(self, strategy_data: Dict[str, Any]) -> StrategyInstance:
        """Deserializar estrategia desde almacenamiento"""
        from ...domain.models.strategy import (
            StrategyInstance, StrategyConfig, StrategyStatus, RiskManagement,
            IndicatorConfig, IndicatorType, SignalConfig, SignalType, SignalCondition
        )
        from ...domain.models.position import Money
        
        # Deserializar configuración
        config_data = strategy_data.get("strategyConfig", {})
        
        # Deserializar indicadores
        indicators = []
        for ind_data in config_data.get("indicators", []):
            indicator = IndicatorConfig(
                name=ind_data["name"],
                indicator_type=IndicatorType(ind_data["indicator_type"]),
                params=ind_data.get("params", {}),
                enabled=ind_data.get("enabled", True),
                weight=ind_data.get("weight", 1.0),
                timeframe=ind_data.get("timeframe", "1m")
            )
            indicators.append(indicator)
        
        # Deserializar señales
        signals = []
        for sig_data in config_data.get("signals", []):
            conditions = []
            for cond_data in sig_data.get("conditions", []):
                condition = SignalCondition(
                    indicator=cond_data["indicator"],
                    operator=cond_data["operator"],
                    value=cond_data["value"],
                    enabled=cond_data.get("enabled", True)
                )
                conditions.append(condition)
            
            signal = SignalConfig(
                name=sig_data["name"],
                signal_type=SignalType(sig_data["signal_type"]),
                conditions=conditions,
                enabled=sig_data.get("enabled", True),
                logic_type=sig_data.get("logic_type", "AND"),
                min_confidence=sig_data.get("min_confidence", 0.5),
                description=sig_data.get("description", "")
            )
            signals.append(signal)
        
        # Deserializar risk management
        risk_data = config_data.get("risk_management", {})
        risk_management = RiskManagement(
            enabled=risk_data.get("enabled", True),
            max_positions=risk_data.get("max_positions", 3),
            position_size=risk_data.get("position_size", 0.02),
            stop_loss_pct=risk_data.get("stop_loss_pct", 0.02),
            take_profit_pct=risk_data.get("take_profit_pct", 0.04),
            max_daily_loss=risk_data.get("max_daily_loss", 0.05)
        )
        
        # Crear configuración
        config = StrategyConfig(
            name=config_data.get("name", ""),
            description=config_data.get("description", ""),
            version=config_data.get("version", "1.0.0"),
            author=config_data.get("author", ""),
            symbol=config_data.get("symbol", ""),
            timeframe=config_data.get("timeframe", "1m"),
            enabled=config_data.get("enabled", True),
            indicators=indicators,
            signals=signals,
            risk_management=risk_management,
            custom_params=config_data.get("custom_params", {}),
            created_at=datetime.fromisoformat(config_data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(config_data.get("updated_at", datetime.now().isoformat()))
        )
        
        # Crear instancia
        strategy = StrategyInstance(
            strategy_id=strategy_data.get("strategy_id", ""),
            config=config,
            status=StrategyStatus(strategy_data.get("status", "INACTIVE")),
            created_at=datetime.fromisoformat(strategy_data.get("created_at", datetime.now().isoformat())),
            last_signal_at=datetime.fromisoformat(strategy_data["last_signal_at"]) if strategy_data.get("last_signal_at") else None,
            signals_generated=strategy_data.get("signals_generated", 0),
            signals_successful=strategy_data.get("signals_successful", 0),
            total_pnl=Money.from_float(float(strategy_data.get("total_pnl", 0))),
            win_rate=strategy_data.get("win_rate", 0.0),
            max_drawdown=Money.from_float(float(strategy_data.get("max_drawdown", 0))),
            sharpe_ratio=strategy_data.get("sharpe_ratio", 0.0),
            market_data=strategy_data.get("market_data", {}),
            error_count=strategy_data.get("error_count", 0),
            last_error=strategy_data.get("last_error")
        )
        
        return strategy

    def load_strategy_from_config_file(self, config_file_path: str) -> Optional[StrategyConfig]:
        """Cargar configuración de estrategia desde archivo JSON"""
        try:
            with open(config_file_path, 'r') as f:
                config_data = json.load(f)
            
            # Convertir formato legacy a nuestro formato
            return self._convert_legacy_config(config_data)
            
        except Exception as e:
            print(f"Error loading strategy config from {config_file_path}: {e}")
            return None

    def _convert_legacy_config(self, legacy_data: Dict[str, Any]) -> StrategyConfig:
        """Convertir configuración legacy a StrategyConfig"""
        from ...domain.models.strategy import IndicatorConfig, IndicatorType, SignalConfig, SignalType
        
        # Convertir indicadores
        indicators = []
        for ind_data in legacy_data.get("indicators", []):
            indicator = IndicatorConfig(
                name=ind_data["name"],
                indicator_type=IndicatorType(ind_data["type"]),
                params=ind_data.get("params", {}),
                enabled=ind_data.get("enabled", True),
                weight=ind_data.get("weight", 1.0),
                timeframe=ind_data.get("timeframe", "1m")
            )
            indicators.append(indicator)
        
        # Convertir señales
        signals = []
        for sig_data in legacy_data.get("signals", []):
            signal = SignalConfig(
                name=sig_data["name"],
                signal_type=SignalType(sig_data["signal_type"]),
                enabled=sig_data.get("enabled", True),
                min_confidence=sig_data.get("min_confidence", 0.5),
                description=sig_data.get("description", "")
            )
            signals.append(signal)
        
        # Crear configuración
        config = StrategyConfig(
            name=legacy_data.get("name", ""),
            description=legacy_data.get("description", ""),
            symbol=legacy_data.get("symbol", "DOGEUSDT"),
            timeframe=legacy_data.get("interval", "1m"),
            indicators=indicators,
            signals=signals,
            enabled=legacy_data.get("enabled", True)
        )
        
        return config


if __name__ == "__main__":
    # Test del repositorio
    import asyncio
    
    async def test_strategy_repository():
        repo = FileStrategyRepository()
        
        print("📁 Testing FileStrategyRepository...")
        
        # Test crear estrategia
        from ...domain.models.strategy import StrategyConfig, StrategyInstance
        
        config = StrategyConfig(
            name="test_strategy",
            description="Test strategy for repository",
            symbol="DOGEUSDT"
        )
        
        strategy = StrategyInstance(
            strategy_id="test_strategy_123",
            config=config
        )
        
        # Guardar estrategia
        await repo.save_strategy(strategy)
        print("✅ Strategy saved")
        
        # Recuperar estrategia
        retrieved = await repo.get_strategy("test_strategy_123")
        if retrieved:
            print(f"✅ Strategy retrieved: {retrieved.config.name}")
        else:
            print("❌ Strategy not found")
        
        print("🎯 Strategy repository test complete!")
    
    # No ejecutar automáticamente para evitar imports circulares
