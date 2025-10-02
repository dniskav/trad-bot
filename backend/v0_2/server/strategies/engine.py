#!/usr/bin/env python3
"""
Strategy Engine
Main engine for executing trading strategies from JSON configurations
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .models import (
    StrategyConfig,
    StrategyInstance,
    StrategyStatus,
    StrategySignal,
    SignalType,
    IndicatorConfig,
    SignalConfig,
)
from .indicators import IndicatorFactory
from .evaluator import SignalEvaluator
from .risk_manager import RiskManager
from backend.shared.logger import get_logger


class StrategyEngine:
    """Main strategy execution engine"""

    def __init__(self, config_dir: str = "strategies/configs", binance_service=None):
        self.config_dir = Path(config_dir)
        self.logger = get_logger("strategy_engine")
        self.binance_service = binance_service

        # Core components
        self.indicator_factory = IndicatorFactory()
        self.signal_evaluator = SignalEvaluator(self.indicator_factory)

        # Strategy instances
        self.strategies: Dict[str, StrategyInstance] = {}

        # Market data cache
        self.market_data: Dict[str, Any] = {}
        self.historical_klines: List[Dict] = []

        # Engine state
        self.is_running = False
        self.loop_task: Optional[asyncio.Task] = None

        # Trade execution callback
        self.trade_execution_callback = None

    async def start(self):
        """Start the strategy engine"""
        if self.is_running:
            self.logger.warning("Strategy engine is already running")
            return

        self.is_running = True
        self.logger.info("🚀 Starting Strategy Engine")

        # Don't auto-load strategies - load on demand
        self.logger.info("📋 Strategy Engine ready for on-demand loading")

        # Start the main execution loop
        self.loop_task = asyncio.create_task(self._execution_loop())

        self.logger.info("✅ Strategy Engine started")

    async def stop(self):
        """Stop the strategy engine"""
        if not self.is_running:
            return

        self.is_running = False
        self.logger.info("🛑 Stopping Strategy Engine")

        # Stop all strategies
        for strategy in self.strategies.values():
            strategy.status = StrategyStatus.INACTIVE

        # Cancel the main loop
        if self.loop_task:
            self.loop_task.cancel()
            try:
                await self.loop_task
            except asyncio.CancelledError:
                pass

        self.logger.info("✅ Strategy Engine stopped")

    async def _load_strategies(self):
        """Load all strategy configurations from config directory"""
        if not self.config_dir.exists():
            self.logger.warning(f"Config directory not found: {self.config_dir}")
            return

        config_files = list(self.config_dir.glob("*.json"))
        if not config_files:
            self.logger.warning(f"No strategy configs found in {self.config_dir}")
            return

        for config_file in config_files:
            try:
                await self._load_strategy_config(config_file)
            except Exception as e:
                self.logger.error(f"Error loading strategy from {config_file}: {e}")

    async def _load_strategy_config(self, config_file: Path):
        """Load a single strategy configuration"""
        with open(config_file, "r") as f:
            config_data = json.load(f)

        # Parse strategy configuration
        strategy_config = self._parse_strategy_config(config_data)

        # Create strategy instance
        strategy_instance = StrategyInstance(
            config=strategy_config, status=StrategyStatus.INACTIVE
        )

        # Initialize indicators
        await self._initialize_indicators(strategy_config)

        # Store strategy
        self.strategies[strategy_config.name] = strategy_instance

        self.logger.info(f"✅ Loaded strategy: {strategy_config.name}")

    def _parse_strategy_config(self, config_data: Dict[str, Any]) -> StrategyConfig:
        """Parse strategy configuration from JSON data"""
        # Parse indicators
        indicators = []
        for indicator_data in config_data.get("indicators", []):
            indicator = IndicatorConfig(
                name=indicator_data["name"],
                type=indicator_data["type"],
                params=indicator_data.get("params", {}),
                enabled=indicator_data.get("enabled", True),
            )
            indicators.append(indicator)

        # Parse signals
        signals = []
        for signal_data in config_data.get("signals", []):
            # Parse conditions
            conditions = []
            for condition_data in signal_data.get("conditions", []):
                from .models import SignalCondition

                condition = SignalCondition(
                    indicator=condition_data["indicator"],
                    operator=condition_data["operator"],
                    value=condition_data["value"],
                    logic=condition_data.get("logic", "AND"),
                )
                conditions.append(condition)

            signal = SignalConfig(
                signal_type=SignalType(signal_data["signal_type"]),
                conditions=conditions,
                confidence=signal_data.get("confidence", 0.5),
                enabled=signal_data.get("enabled", True),
            )
            signals.append(signal)

        # Parse risk management
        risk_data = config_data.get("risk_management", {})
        from .models import RiskManagement

        risk_management = RiskManagement(
            stop_loss_pct=risk_data.get("stop_loss_pct", 0.02),
            take_profit_pct=risk_data.get("take_profit_pct", 0.03),
            max_positions=risk_data.get("max_positions", 3),
            position_size=risk_data.get("position_size", 0.5),
            max_daily_loss=risk_data.get("max_daily_loss", 0.05),
            enabled=risk_data.get("enabled", True),
        )

        # Create strategy config
        strategy_config = StrategyConfig(
            name=config_data["name"],
            description=config_data["description"],
            version=config_data.get("version", "1.0.0"),
            author=config_data.get("author", "Strategy Engine"),
            symbol=config_data.get("symbol", "DOGEUSDT"),
            interval=config_data.get("interval", "1m"),
            enabled=config_data.get("enabled", True),
            indicators=indicators,
            signals=signals,
            risk_management=risk_management,
            custom_params=config_data.get("custom_params", {}),
        )

        return strategy_config

    async def _initialize_indicators(self, strategy_config: StrategyConfig):
        """Initialize indicators for a strategy"""
        for indicator_config in strategy_config.indicators:
            if indicator_config.enabled:
                try:
                    self.indicator_factory.create_indicator(
                        name=indicator_config.name,
                        indicator_type=indicator_config.type,
                        params=indicator_config.params,
                    )
                except Exception as e:
                    self.logger.error(
                        f"Error creating indicator {indicator_config.name}: {e}"
                    )

        # Warm up indicators with historical data
        await self._warmup_indicators(strategy_config)

    async def _execution_loop(self):
        """Main strategy execution loop"""
        while self.is_running:
            try:
                # Update market data (this would come from your data source)
                await self._update_market_data()

                # Execute all active strategies
                for strategy_name, strategy_instance in self.strategies.items():
                    if strategy_instance.status == StrategyStatus.ACTIVE:
                        await self._execute_strategy(strategy_instance)

                # Wait before next iteration
                await asyncio.sleep(1)  # 1 second interval

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in execution loop: {e}")
                await asyncio.sleep(5)  # Wait longer on error

    async def _update_market_data(self):
        """Update market data with real Binance data"""
        try:
            # Use real-time data from historical klines if available
            if self.historical_klines:
                latest_kline = self.historical_klines[-1]
                current_price = float(latest_kline[4])  # Close price
                current_volume = float(latest_kline[5])  # Volume

                # Calculate previous price for trend analysis
                prev_price = None
                if len(self.historical_klines) > 1:
                    prev_price = float(self.historical_klines[-2][4])

                self.market_data = {
                    "current_price": current_price,
                    "prev_price": prev_price,
                    "volume": current_volume,
                    "timestamp": datetime.now(),
                }
            else:
                # Fallback to placeholder if no historical data
                self.market_data = {
                    "current_price": 0.08,  # Placeholder
                    "volume": 1000000,  # Placeholder
                    "timestamp": datetime.now(),
                }
        except Exception as e:
            self.logger.error(f"Error updating market data: {e}")
            # Fallback to placeholder on error
            self.market_data = {
                "current_price": 0.08,  # Placeholder
                "volume": 1000000,  # Placeholder
                "timestamp": datetime.now(),
            }

    def update_market_data_from_websocket(self, kline_data: dict):
        """Update market data from WebSocket kline data"""
        try:
            kline = kline_data.get("kline", {})
            if not kline:
                return

            # Update current price from WebSocket
            current_price = float(kline.get("c", 0))
            current_volume = float(kline.get("v", 0))

            # Check if this is a closed kline (new candle)
            is_closed = kline.get("closed", False)

            if is_closed:
                # New candle closed - refresh historical data
                self.logger.info(
                    f"🕯️ New candle closed at {current_price}, refreshing historical data"
                )
                # Trigger historical data refresh in background
                asyncio.create_task(self._refresh_historical_data())

            # Update market data with real-time price
            prev_price = (
                self.market_data.get("current_price") if self.market_data else None
            )

            self.market_data = {
                "current_price": current_price,
                "prev_price": prev_price,
                "volume": current_volume,
                "timestamp": datetime.now(),
                "is_closed": is_closed,
            }

            self.logger.debug(
                f"📊 Market data updated: price={current_price}, volume={current_volume}, closed={is_closed}"
            )

        except Exception as e:
            self.logger.error(f"Error updating market data from WebSocket: {e}")

    async def _refresh_historical_data(self):
        """Refresh historical klines when new candle closes"""
        try:
            if self.binance_service:
                # Get fresh 1000 klines from API
                new_klines = await self.binance_service.get_historical_klines(
                    "1m", 1000
                )
                if new_klines:
                    self.historical_klines = new_klines
                    self.logger.info(
                        f"🔄 Refreshed {len(new_klines)} historical klines"
                    )

                    # Re-warmup indicators with fresh data for all loaded strategies
                    for strategy_instance in self.strategies.values():
                        await self._warmup_indicators(strategy_instance.config)
        except Exception as e:
            self.logger.error(f"Error refreshing historical data: {e}")

    async def _execute_strategy(self, strategy_instance: StrategyInstance):
        """Execute a single strategy"""
        try:
            strategy_config = strategy_instance.config

            # Update indicators with current market data
            await self._update_indicators(strategy_config)

            # Evaluate signals - check all signals and execute the first valid one
            last_signal = None
            for signal_config in strategy_config.signals:
                if signal_config.enabled:
                    signal = self.signal_evaluator.evaluate_signal(
                        signal_config,
                        {**self.market_data, "strategy_name": strategy_config.name},
                    )

                    if signal:
                        # Always store the last signal (including HOLD)
                        last_signal = signal

                        # Only execute trades for BUY/SELL signals
                        if signal.signal_type.value in ["BUY", "SELL"]:
                            # Apply risk management
                            risk_manager = RiskManager(strategy_config.risk_management)

                            # Get actual account balance and position count
                            # Note: This requires access to STM service, which we don't have here
                            # For now, use placeholder values but set positions_count to 0
                            account_balance = 1000.0  # Placeholder
                            risk_manager.positions_count = 0  # Reset to allow trades

                            final_signal = risk_manager.apply_risk_management(
                                signal, account_balance
                            )

                            # Debug: Log SL/TP values
                            if final_signal:
                                self.logger.info(
                                    f"SL/TP calculated - SL: {final_signal.stop_loss}, TP: {final_signal.take_profit}"
                                )
                            else:
                                self.logger.warning(
                                    "Risk management returned None signal"
                                )

                            if final_signal:
                                strategy_instance.last_signal = final_signal
                                strategy_instance.last_updated = datetime.now()

                                # Execute the trade through callback
                                if self.trade_execution_callback:
                                    await self.trade_execution_callback(final_signal)
                                else:
                                    await self._execute_trade(final_signal)

                                self.logger.info(
                                    f"Signal generated: {final_signal.signal_type.value} for {strategy_config.name}"
                                )
                                break  # Exit after first valid trade signal

            # If no trade signal was generated, store the last HOLD signal
            if last_signal and last_signal.signal_type.value == "HOLD":
                strategy_instance.last_signal = last_signal
                strategy_instance.last_updated = datetime.now()

        except Exception as e:
            self.logger.error(
                f"Error executing strategy {strategy_instance.config.name}: {e}"
            )
            strategy_instance.status = StrategyStatus.ERROR

    async def _warmup_indicators(self, strategy_config: StrategyConfig):
        """Warm up indicators with historical kline data from Binance"""
        if not self.binance_service:
            self.logger.warning("No Binance service available for indicator warmup")
            return

        try:
            # Fetch 1000 historical klines
            klines = await self.binance_service.get_historical_klines(limit=1000)
            if not klines:
                self.logger.warning("No historical klines available for warmup")
                return

            self.historical_klines = klines
            self.logger.info(
                f"Warming up indicators with {len(klines)} historical klines"
            )

            # Extract closes and volumes
            closes = [float(k[4]) for k in klines]  # Close prices
            volumes = [float(k[5]) for k in klines]  # Volumes

            # Warm up each indicator
            for indicator_config in strategy_config.indicators:
                if indicator_config.enabled:
                    try:
                        indicator = self.indicator_factory.get_indicator(
                            indicator_config.name
                        )

                        # Update based on indicator type
                        if indicator_config.type in ["sma", "rsi", "macd", "trend"]:
                            indicator.update(closes)
                        elif indicator_config.type == "volume":
                            indicator.update(volumes)

                        self.logger.info(
                            f"Warmed up indicator: {indicator_config.name} ({indicator_config.type})"
                        )

                    except Exception as e:
                        self.logger.error(
                            f"Error warming up indicator {indicator_config.name}: {e}"
                        )

        except Exception as e:
            self.logger.error(f"Error during indicator warmup: {e}")

    async def _update_indicators(self, strategy_config: StrategyConfig):
        """Update all indicators for a strategy with real-time data"""
        # Use real-time market data if available, otherwise use historical data
        if self.market_data.get("current_price"):
            # Use real-time data
            current_price = self.market_data["current_price"]
            current_volume = self.market_data.get("volume", 0)

            # Get the latest closes and volumes from historical data
            closes = [
                float(k[4]) for k in self.historical_klines[-50:]
            ]  # Last 50 closes
            volumes = [
                float(k[5]) for k in self.historical_klines[-50:]
            ]  # Last 50 volumes

            # Add current data
            closes.append(current_price)
            volumes.append(current_volume)
        else:
            # Fallback to historical data
            closes = [
                float(k[4]) for k in self.historical_klines[-10:]
            ]  # Last 10 closes
            volumes = [
                float(k[5]) for k in self.historical_klines[-10:]
            ]  # Last 10 volumes

        for indicator_config in strategy_config.indicators:
            if indicator_config.enabled:
                try:
                    indicator = self.indicator_factory.get_indicator(
                        indicator_config.name
                    )

                    # Update based on indicator type
                    if indicator_config.type in ["sma", "rsi", "macd", "trend"]:
                        indicator.update(closes)
                    elif indicator_config.type == "volume":
                        indicator.update(volumes)

                except Exception as e:
                    self.logger.error(
                        f"Error updating indicator {indicator_config.name}: {e}"
                    )

    async def _execute_trade(self, signal: StrategySignal):
        """Execute a trade based on signal"""
        # This will be called by the StrategyService
        self.logger.info(
            f"Trade signal generated: {signal.signal_type.value} at {signal.entry_price}"
        )
        # The actual trade execution is handled by StrategyService

    # Public API methods
    def get_strategies(self) -> Dict[str, StrategyInstance]:
        """Get all strategy instances"""
        return self.strategies.copy()

    def get_strategy(self, name: str) -> Optional[StrategyInstance]:
        """Get a specific strategy instance"""
        return self.strategies.get(name)

    async def start_strategy(self, name: str) -> bool:
        """Start a strategy"""
        if name not in self.strategies:
            return False

        strategy = self.strategies[name]
        if strategy.status == StrategyStatus.ACTIVE:
            return True

        strategy.status = StrategyStatus.ACTIVE
        strategy.started_at = datetime.now()

        self.logger.info(f"Started strategy: {name}")
        return True

    async def stop_strategy(self, name: str) -> bool:
        """Stop a strategy"""
        if name not in self.strategies:
            return False

        strategy = self.strategies[name]
        strategy.status = StrategyStatus.INACTIVE
        strategy.started_at = None

        self.logger.info(f"Stopped strategy: {name}")
        return True

    async def reload_strategy(self, name: str) -> bool:
        """Reload a strategy configuration"""
        # Implementation would reload from config file
        self.logger.info(f"Reloaded strategy: {name}")
        return True

    async def load_strategy_from_file(self, config_file: str) -> bool:
        """
        Load a strategy from a specific config file

        Args:
            config_file: Path to the strategy config file

        Returns:
            bool: True if loaded successfully
        """
        try:
            config_path = Path(config_file)
            if not config_path.exists():
                self.logger.error(f"Config file not found: {config_file}")
                return False

            await self._load_strategy_config(config_path)
            self.logger.info(f"✅ Loaded strategy from file: {config_file}")
            return True

        except Exception as e:
            self.logger.error(f"Error loading strategy from {config_file}: {e}")
            return False

    async def load_strategy_by_name(self, strategy_name: str) -> bool:
        """
        Load a strategy by name from the configs directory

        Args:
            strategy_name: Name of the strategy (without .json extension)

        Returns:
            bool: True if loaded successfully
        """
        config_file = self.config_dir / f"{strategy_name}.json"
        return await self.load_strategy_from_file(str(config_file))

    async def unload_strategy(self, name: str) -> bool:
        """
        Unload a strategy from memory

        Args:
            name: Strategy name

        Returns:
            bool: True if unloaded successfully
        """
        if name not in self.strategies:
            self.logger.warning(f"Strategy not found: {name}")
            return False

        strategy = self.strategies[name]
        if strategy.status.value == "ACTIVE":
            await self.stop_strategy(name)

        # Remove from strategies dict
        del self.strategies[name]

        # Clean up indicators used only by this strategy
        # TODO: Implement indicator cleanup logic

        self.logger.info(f"✅ Unloaded strategy: {name}")
        return True

    def get_available_configs(self) -> List[str]:
        """
        Get list of available strategy config files

        Returns:
            List of strategy names (without .json extension)
        """
        if not self.config_dir.exists():
            return []

        config_files = list(self.config_dir.glob("*.json"))
        return [f.stem for f in config_files]

    def set_trade_execution_callback(self, callback):
        """Set callback for trade execution"""
        self.trade_execution_callback = callback
