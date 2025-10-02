import asyncio
from typing import Dict, List, Optional, Callable
from datetime import datetime, timezone
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from shared.logger import get_logger
from .position_service import PositionService

log = get_logger("stm.price_monitor")

# Callback type for price updates
PriceUpdateCallback = Callable[[str, float], None]


class PriceMonitor:
    """Monitors price changes and triggers SL/TP execution"""

    def __init__(self, position_service: PositionService):
        self.position_service = position_service
        self.current_prices: Dict[str, float] = {}
        self.monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

    def _to_float(self, value) -> Optional[float]:
        """Safely convert to float; returns None if not parseable."""
        try:
            if value is None:
                return None
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                v = value.strip()
                if v == "" or v.lower() in ("none", "null", "nan"):
                    return None
                return float(v)
        except Exception:
            log.warning(f"Non-numeric value where float expected: {value!r}")
            return None

    def update_price(self, symbol: str, price: float) -> None:
        """Update current price for a symbol"""
        self.current_prices[symbol] = price

    async def start_monitoring(self) -> None:
        """Start the price monitoring loop"""
        if self.monitoring:
            return

        self.monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        log.info("🔍 Price monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop the price monitoring loop"""
        self.monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        log.info("🔍 Price monitoring stopped")

    async def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while self.monitoring:
            try:
                await self._check_sl_tp_triggers()
                await asyncio.sleep(1)  # Check every second
            except Exception as e:
                log.error(f"Error in price monitoring loop: {e}")
                await asyncio.sleep(5)  # Wait longer on error

    async def _check_sl_tp_triggers(self) -> None:
        """Check if any SL/TP conditions are met"""
        try:
            # Get all open positions
            positions = await self.position_service.get_positions(status="open")

            for position_data in positions:
                await self._check_position_triggers(position_data)

        except Exception as e:
            log.error(f"Error checking SL/TP triggers: {e}")

    async def _check_position_triggers(self, position_data: Dict) -> None:
        """Check SL/TP triggers for a specific position"""
        try:
            log.debug(
                f"Checking triggers for position_data type: {type(position_data)}, value: {position_data}"
            )
            if isinstance(position_data, str):
                log.error(f"Position data is string instead of dict: {position_data}")
                return
            symbol = position_data["symbol"]
            current_price = self.current_prices.get(symbol)

            if current_price is None:
                return  # No price data available

            position_id = position_data["positionId"]
            side = position_data["side"]
            stop_loss_price = self._to_float(position_data.get("stopLossPrice"))
            take_profit_price = self._to_float(position_data.get("takeProfitPrice"))

            # Check if position is still open
            if position_data.get("status") != "open":
                return

            # Check Stop Loss trigger
            if stop_loss_price is not None:
                sl_price = stop_loss_price
                if self._should_trigger_sl(side, current_price, sl_price):
                    await self._execute_stop_loss(position_id, current_price)
                    return  # Stop checking after SL execution

            # Check Take Profit trigger
            if take_profit_price is not None:
                tp_price = take_profit_price
                if self._should_trigger_tp(side, current_price, tp_price):
                    await self._execute_take_profit(position_id, current_price)
                    return  # Stop checking after TP execution

        except Exception as e:
            log.error(f"Error checking position triggers: {e}")

    def _should_trigger_sl(
        self, side: str, current_price: float, sl_price: float
    ) -> bool:
        """Check if Stop Loss should be triggered"""
        if side == "BUY":
            # For long positions, SL triggers when price goes below SL
            return current_price <= sl_price
        else:  # SELL
            # For short positions, SL triggers when price goes above SL
            return current_price >= sl_price

    def _should_trigger_tp(
        self, side: str, current_price: float, tp_price: float
    ) -> bool:
        """Check if Take Profit should be triggered"""
        if side == "BUY":
            # For long positions, TP triggers when price goes above TP
            return current_price >= tp_price
        else:  # SELL
            # For short positions, TP triggers when price goes below TP
            return current_price <= tp_price

    async def _execute_stop_loss(self, position_id: str, current_price: float) -> None:
        """Execute Stop Loss order"""
        try:
            log.info(
                f"🛑 Stop Loss triggered for position {position_id} at price {current_price}"
            )

            # Create close request
            from ..models.position import ClosePositionRequest

            close_request = ClosePositionRequest(
                positionId=position_id, reason="stop_loss"
            )

            # Execute close order
            result = await self.position_service.close_position(close_request)

            if result.success:
                log.info(
                    f"✅ Stop Loss executed successfully for position {position_id}"
                )
            else:
                log.error(
                    f"❌ Failed to execute Stop Loss for position {position_id}: {result.message}"
                )

        except Exception as e:
            log.error(f"Error executing Stop Loss for position {position_id}: {e}")

    async def _execute_take_profit(
        self, position_id: str, current_price: float
    ) -> None:
        """Execute Take Profit order"""
        try:
            log.info(
                f"🎯 Take Profit triggered for position {position_id} at price {current_price}"
            )

            # Create close request
            from ..models.position import ClosePositionRequest

            close_request = ClosePositionRequest(
                positionId=position_id, reason="take_profit"
            )

            # Execute close order
            result = await self.position_service.close_position(close_request)

            if result.success:
                log.info(
                    f"✅ Take Profit executed successfully for position {position_id}"
                )
            else:
                log.error(
                    f"❌ Failed to execute Take Profit for position {position_id}: {result.message}"
                )

        except Exception as e:
            log.error(f"Error executing Take Profit for position {position_id}: {e}")
