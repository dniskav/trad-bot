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
from ..models.position import OrderResponse
from backend.shared.logger import get_logger
from backend.shared.settings import env_str

log = get_logger("strategy_service")


class StrategyService:
    """Service for managing trading strategies"""

    def __init__(self):
        self.logger = log
        self.strategy_engine = None  # Will be initialized with binance_service
        self.stm_service = STMService()
        self.binance_service = None  # Will be injected
        self.is_initialized = False
        self.ws_manager = WebSocketManager()

    async def initialize(self, binance_service: BinanceService):
        """Initialize the strategy service with dependencies"""
        if self.is_initialized:
            return

        self.binance_service = binance_service

        # Inject strategy service into binance service for WebSocket data forwarding
        self.binance_service.strategy_service = self

        # Initialize strategy engine with binance service
        self.strategy_engine = StrategyEngine(
            config_dir=env_str(
                "STRATEGY_CONFIG_DIR", "backend/v0_2/server/strategies/configs"
            ),
            binance_service=binance_service,
        )

        # Set trade execution callback
        self.strategy_engine.set_trade_execution_callback(self.execute_trade_signal)

        await self.strategy_engine.start()

        # Subscribe to WebSocket events for real-time data
        await self._subscribe_to_websocket_events()

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
            # Ignore HOLD signals
            if getattr(signal, "signal_type", None) is None:
                return False
            if signal.signal_type.value not in ("BUY", "SELL"):
                return False

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
            # Determine symbol and ensure minimum notional by converting USDT -> qty
            symbol = (
                signal.metadata.get("symbol")
                or env_str("SERVER_SYMBOL", "DOGEUSDT").upper()
            )

            # Get current reference price
            price: float = 0.0
            try:
                if self.strategy_engine and self.strategy_engine.market_data.get(
                    "current_price"
                ):
                    price = float(
                        self.strategy_engine.market_data.get("current_price") or 0
                    )
                elif getattr(self.strategy_engine, "historical_klines", None):
                    last = self.strategy_engine.historical_klines[-1]
                    price = float(last[4])  # close
            except Exception:
                price = 0.0

            # Guard: if price missing, do not execute
            if price <= 0:
                self.logger.error(
                    "Price not available to compute min notional quantity"
                )
                return False

            # Fetch min notional and compute minimum quantity
            try:
                min_notional = await self.stm_service.get_min_notional(symbol)
            except Exception:
                min_notional = 1.0

            # Position size from metadata (usdt budget) if provided; otherwise use min_notional
            usdt_target = float(signal.metadata.get("position_size") or min_notional)
            # Ensure at least min notional
            notional = max(usdt_target, float(min_notional))
            quantity = max(notional / price, 0.0)

            # Convert strategy signal to STM order format
            order_data = {
                "botId": signal.strategy_name,  # Add botId for tracking
                "strategy": signal.strategy_name,  # Add strategy name
                "symbol": symbol,
                "side": signal.signal_type.value,
                "type": "MARKET",
                "quantity": str(quantity),
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

            # Debug: Log SL/TP values being sent
            self.logger.info(
                f"Sending order with SL: {signal.stop_loss}, TP: {signal.take_profit}"
            )
            if signal.stop_loss is None or signal.take_profit is None:
                self.logger.warning(
                    f"SL/TP is None - SL: {signal.stop_loss}, TP: {signal.take_profit}"
                )

            # Execute order through server endpoint (which orchestrates SL/TP)
            import aiohttp

            try:
                self.logger.info(
                    f"Creating position via server endpoint: {order_data['symbol']}, {order_data['side']}, {order_data['quantity']}"
                )

                # Use server endpoint instead of direct STM call
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "http://localhost:8200/positions/open",
                        json=order_data,
                        timeout=10,
                    ) as response:
                        response_data = await response.json()
                        result = OrderResponse(**response_data)
            except Exception as e:
                self.logger.error(f"Error creating OpenPositionRequest: {e}")
                self.logger.error(f"Order data: {order_data}")
                return False

            if result and result.success:
                # Apply SL/TP after position is opened (like Swagger does)
                position_id = result.positionId
                if position_id and (signal.stop_loss or signal.take_profit):
                    self.logger.info(f"Setting SL/TP for position {position_id}")

                    # Set stop loss if provided
                    if signal.stop_loss:
                        sl_result = await self.stm_service.set_stop_loss(
                            position_id, str(signal.stop_loss)
                        )
                        self.logger.info(f"SL result: {sl_result}")

                    # Set take profit if provided
                    if signal.take_profit:
                        tp_result = await self.stm_service.set_take_profit(
                            position_id, str(signal.take_profit)
                        )
                        self.logger.info(f"TP result: {tp_result}")
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

    async def _subscribe_to_websocket_events(self):
        """Subscribe to WebSocket events for real-time market data"""
        try:
            # Create a custom WebSocket manager for strategy engine
            # This will listen to Binance WebSocket events and forward them to strategy engine
            self.logger.info("🔌 Subscribing to WebSocket events for real-time data")

            # Start a background task to listen for WebSocket events
            asyncio.create_task(self._websocket_event_listener())

        except Exception as e:
            self.logger.error(f"Error subscribing to WebSocket events: {e}")

    async def _websocket_event_listener(self):
        """Listen for WebSocket events and forward to strategy engine"""
        try:
            # This is a simplified approach - in a real implementation,
            # you'd want to use a proper event bus or message queue
            # For now, we'll use a polling approach to check for new data

            while self.is_initialized:
                try:
                    # Check if we have new WebSocket data from Binance service
                    # This is a placeholder - the actual implementation would
                    # use a proper event subscription mechanism
                    await asyncio.sleep(1)  # Poll every second

                except Exception as e:
                    self.logger.error(f"Error in WebSocket event listener: {e}")
                    await asyncio.sleep(5)  # Wait longer on error

        except Exception as e:
            self.logger.error(f"WebSocket event listener stopped: {e}")

    def handle_websocket_kline_data(self, kline_data: dict):
        """Handle kline data from WebSocket and forward to strategy engine"""
        try:
            if self.strategy_engine and self.is_initialized:
                self.strategy_engine.update_market_data_from_websocket(kline_data)
        except Exception as e:
            self.logger.error(f"Error handling WebSocket kline data: {e}")

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
        return Path(
            env_str(
                "STRATEGY_LOADED_FILE",
                "backend/v0_2/server/strategies/configs/.loaded.json",
            )
        )

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
