#!/usr/bin/env python3
"""
Strategy Service
Service layer for strategy management and execution
"""

import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path

from ..strategies import StrategyEngine, StrategyInstance
from ..services.websocket_manager import WebSocketManager
from ..services.stm_service import STMService
from ..services.binance_service import BinanceService
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from shared.logger import get_logger
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from shared.settings import env_str

log = get_logger("strategy_service")


class StrategyService:
    """Service for managing trading strategies"""

    def __init__(self):
        self.logger = log
        self.strategy_engine = StrategyEngine(
            config_dir=env_str(
                "STRATEGY_CONFIG_DIR", "backend/v0_2/server/strategies/configs"
            )
        )
        self.stm_service = STMService()
        self.binance_service = None  # Will be injected
        self.is_initialized = False
        self.ws_manager = WebSocketManager()

    async def initialize(self, binance_service: BinanceService):
        """Initialize the strategy service with dependencies"""
        if self.is_initialized:
            return

        self.binance_service = binance_service

        # Set trade execution callback
        self.strategy_engine.set_trade_execution_callback(self.execute_trade_signal)

        await self.strategy_engine.start()

        # Load previously loaded strategies from persistence (but keep them STOPPED)
        try:
            loaded_names = self._read_loaded_names()
            if loaded_names:
                self.logger.info(f"Autoloading strategies (stopped): {loaded_names}")
                for name in loaded_names:
                    await self.strategy_engine.load_strategy_by_name(name)
        except Exception as e:
            self.logger.warning(f"Error autoloading strategies: {e}")
        self.is_initialized = True
        self.logger.info("✅ Strategy Service initialized")

    async def shutdown(self):
        """Shutdown the strategy service"""
        if not self.is_initialized:
            return

        await self.strategy_engine.stop()
        self.is_initialized = False
        self.logger.info("🛑 Strategy Service shutdown")

    def get_all_strategies(self) -> Dict[str, StrategyInstance]:
        """Get all strategy instances"""
        return self.strategy_engine.get_strategies()

    def get_strategy(self, name: str) -> Optional[StrategyInstance]:
        """Get a specific strategy instance"""
        return self.strategy_engine.get_strategy(name)

    async def start_strategy(self, name: str) -> bool:
        """Start a strategy"""
        started = await self.strategy_engine.start_strategy(name)
        if started:
            await self._broadcast_strategy_event("strategy_started", name)
        return started

    async def stop_strategy(self, name: str) -> bool:
        """Stop a strategy"""
        stopped = await self.strategy_engine.stop_strategy(name)
        if stopped:
            await self._broadcast_strategy_event("strategy_stopped", name)
        return stopped

    async def reload_strategy(self, name: str) -> bool:
        """Reload a strategy configuration"""
        return await self.strategy_engine.reload_strategy(name)

    def get_strategy_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Get strategy configuration as dictionary"""
        strategy = self.get_strategy(name)
        if not strategy:
            return None

        config = strategy.config
        return {
            "name": config.name,
            "description": config.description,
            "version": config.version,
            "author": config.author,
            "symbol": config.symbol,
            "interval": config.interval,
            "enabled": config.enabled,
            "indicators": [
                {
                    "name": ind.name,
                    "type": ind.type,
                    "params": ind.params,
                    "enabled": ind.enabled,
                }
                for ind in config.indicators
            ],
            "signals": [
                {
                    "signal_type": sig.signal_type.value,
                    "conditions": [
                        {
                            "indicator": cond.indicator,
                            "operator": cond.operator,
                            "value": cond.value,
                            "logic": cond.logic,
                        }
                        for cond in sig.conditions
                    ],
                    "confidence": sig.confidence,
                    "enabled": sig.enabled,
                }
                for sig in config.signals
            ],
            "risk_management": {
                "stop_loss_pct": config.risk_management.stop_loss_pct,
                "take_profit_pct": config.risk_management.take_profit_pct,
                "max_positions": config.risk_management.max_positions,
                "position_size": config.risk_management.position_size,
                "max_daily_loss": config.risk_management.max_daily_loss,
                "enabled": config.risk_management.enabled,
            },
            "custom_params": config.custom_params,
        }

    def get_strategy_performance(self, name: str) -> Optional[Dict[str, Any]]:
        """Get strategy performance metrics"""
        strategy = self.get_strategy(name)
        if not strategy:
            return None

        return {
            "strategy_name": name,
            "status": strategy.status.value,
            "started_at": (
                strategy.started_at.isoformat() if strategy.started_at else None
            ),
            "last_updated": strategy.last_updated.isoformat(),
            "last_signal": (
                strategy.last_signal.__dict__ if strategy.last_signal else None
            ),
            "positions_count": len(strategy.positions),
            "performance": strategy.performance,
        }

    async def execute_trade_signal(self, signal) -> bool:
        """
        Execute a trade signal through STM

        Args:
            signal: StrategySignal object

        Returns:
            bool: True if trade was executed successfully
        """
        try:
            # Broadcast strategy signal to clients (pre-execution)
            try:
                await self.ws_manager.broadcast(
                    {
                        "channel": "strategies",
                        "type": "strategy_signal",
                        "name": getattr(signal, "strategy_name", "unknown"),
                        "signal": {
                            "signal_type": signal.signal_type.value,
                            "confidence": signal.confidence,
                            "reasoning": getattr(signal, "reasoning", None),
                        },
                    }
                )
            except Exception as _:
                pass
            # Convert strategy signal to STM order format
            order_data = {
                "symbol": signal.metadata.get("symbol", "DOGEUSDT"),
                "side": signal.signal_type.value,
                "type": "MARKET",
                "quantity": str(signal.metadata.get("position_size", 0.5)),
                "leverage": 1,
                "isIsolated": False,
                "stopLoss": {
                    "price": str(signal.stop_loss) if signal.stop_loss else None,
                    "type": "STOP_MARKET",
                },
                "takeProfit": {
                    "price": str(signal.take_profit) if signal.take_profit else None,
                    "type": "LIMIT",
                },
            }

            # Execute order through STM
            result = await self.stm_service.open_position(order_data)

            if result and result.get("success"):
                self.logger.info(
                    f"✅ Trade executed: {signal.signal_type.value} at {signal.entry_price}"
                )
                # Optionally broadcast executed
                try:
                    await self.ws_manager.broadcast(
                        {
                            "channel": "strategies",
                            "type": "strategy_executed",
                            "name": getattr(signal, "strategy_name", "unknown"),
                            "result": {"success": True},
                        }
                    )
                except Exception:
                    pass
                return True
            else:
                self.logger.error(f"❌ Trade execution failed: {result}")
                return False

        except Exception as e:
            self.logger.error(f"Error executing trade signal: {e}")
            return False

    async def get_market_data(self) -> Dict[str, Any]:
        """Get current market data for strategy execution"""
        try:
            if not self.binance_service:
                return {}

            # Get current price and volume data
            # This would integrate with your Binance service
            market_data = {
                "current_price": 0.08,  # Placeholder
                "volume": 1000000,  # Placeholder
                "timestamp": "2024-01-01T00:00:00Z",  # Placeholder
            }

            return market_data

        except Exception as e:
            self.logger.error(f"Error getting market data: {e}")
            return {}

    def get_available_indicators(self) -> List[str]:
        """Get list of available technical indicators"""
        return self.strategy_engine.indicator_factory.get_available_types()

    async def load_strategy(self, strategy_name: str) -> bool:
        """Load a strategy by name"""
        loaded = await self.strategy_engine.load_strategy_by_name(strategy_name)
        if loaded:
            await self._broadcast_strategy_event("strategy_loaded", strategy_name)
            self._persist_loaded_names()
        return loaded
    
    async def unload_strategy(self, strategy_name: str) -> bool:
        """Unload a strategy by name"""
        unloaded = await self.strategy_engine.unload_strategy(strategy_name)
        if unloaded:
            await self._broadcast_strategy_event("strategy_unloaded", strategy_name)
            self._persist_loaded_names()
        return unloaded
    
    def get_available_configs(self) -> List[str]:
        """Get list of available strategy config files"""
        return self.strategy_engine.get_available_configs()

    def get_strategy_status(self) -> Dict[str, Any]:
        """Get overall strategy engine status"""
        strategies = self.get_all_strategies()
        active_count = sum(1 for s in strategies.values() if s.status.value == "ACTIVE")

        return {
            "total_strategies": len(strategies),
            "active_strategies": active_count,
            "inactive_strategies": len(strategies) - active_count,
            "engine_running": self.strategy_engine.is_running,
            "initialized": self.is_initialized,
            "available_configs": self.get_available_configs(),
        }

    async def _broadcast_strategy_event(self, event_type: str, name: str) -> None:
        """Broadcast strategy lifecycle events over WS"""
        try:
            instance = self.get_strategy(name)
            status = instance.status.value if instance else "UNKNOWN"
            payload = {
                "type": event_type,
                "name": name,
                "status": status,
            }
            await self.ws_manager.broadcast({"channel": "strategies", **payload})
        except Exception as e:
            self.logger.warning(f"WS broadcast error ({event_type} {name}): {e}")

    # ---------- Persistence of loaded strategy names ----------
    def _loaded_file_path(self) -> Path:
        return Path(env_str("STRATEGY_LOADED_FILE", "backend/v0_2/server/strategies/configs/.loaded.json"))

    def _read_loaded_names(self) -> List[str]:
        p = self._loaded_file_path()
        if not p.exists():
            return []
        try:
            import json
            return json.loads(p.read_text())
        except Exception:
            return []

    def _persist_loaded_names(self) -> None:
        try:
            import json
            names = list(self.strategy_engine.get_strategies().keys())
            p = self._loaded_file_path()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(names))
        except Exception as e:
            self.logger.warning(f"Could not persist loaded strategies: {e}")
