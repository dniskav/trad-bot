#!/usr/bin/env python3
"""
Risk Manager
Manages risk parameters and position sizing for strategies
"""

from typing import Dict, Any, Optional, Tuple
from .models import RiskManagement, StrategySignal, SignalType
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from shared.logger import get_logger


class RiskManager:
    """Manages risk parameters and position sizing"""

    def __init__(self, risk_config: RiskManagement):
        self.risk_config = risk_config
        self.logger = get_logger("risk_manager")
        self.daily_pnl = 0.0
        self.positions_count = 0

    def apply_risk_management(
        self, signal: StrategySignal, account_balance: float
    ) -> Optional[StrategySignal]:
        """
        Apply risk management to a trading signal

        Args:
            signal: Original trading signal
            account_balance: Available account balance

        Returns:
            Modified signal with risk management applied, or None if rejected
        """
        if not self.risk_config.enabled:
            return signal

        try:
            # Check daily loss limit
            if self.daily_pnl <= -self.risk_config.max_daily_loss * account_balance:
                self.logger.warning(f"Daily loss limit reached: {self.daily_pnl:.2f}")
                return None

            # Check maximum positions
            if self.positions_count >= self.risk_config.max_positions:
                self.logger.warning(
                    f"Maximum positions reached: {self.positions_count}"
                )
                return None

            # Calculate position size
            position_size = self._calculate_position_size(account_balance)
            if position_size <= 0:
                self.logger.warning("Position size too small")
                return None

            # Calculate stop loss and take profit
            stop_loss, take_profit = self._calculate_sl_tp(
                signal.entry_price, signal.signal_type
            )

            # Create modified signal
            modified_signal = StrategySignal(
                strategy_name=signal.strategy_name,
                signal_type=signal.signal_type,
                confidence=signal.confidence,
                entry_price=signal.entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reasoning=signal.reasoning,
                metadata={
                    **signal.metadata,
                    "position_size": position_size,
                    "risk_applied": True,
                    "daily_pnl": self.daily_pnl,
                    "positions_count": self.positions_count,
                },
            )

            return modified_signal

        except Exception as e:
            self.logger.error(f"Error applying risk management: {e}")
            return None

    def _calculate_position_size(self, account_balance: float) -> float:
        """
        Calculate position size based on risk management rules

        Args:
            account_balance: Available account balance

        Returns:
            Position size in base currency
        """
        # Use percentage of available balance
        base_size = account_balance * self.risk_config.position_size

        # Adjust for daily loss (reduce size if approaching limit)
        if self.daily_pnl < 0:
            loss_ratio = abs(self.daily_pnl) / (
                self.risk_config.max_daily_loss * account_balance
            )
            if loss_ratio > 0.5:  # If we've used more than 50% of daily loss limit
                reduction_factor = 1.0 - (loss_ratio - 0.5) * 0.5  # Reduce by up to 25%
                base_size *= max(0.25, reduction_factor)  # Minimum 25% of original size

        return base_size

    def _calculate_sl_tp(
        self, entry_price: float, signal_type: SignalType
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate stop loss and take profit levels

        Args:
            entry_price: Entry price
            signal_type: Type of signal (BUY/SELL)

        Returns:
            Tuple of (stop_loss, take_profit)
        """
        if signal_type == SignalType.BUY:
            # For long positions
            stop_loss = entry_price * (1 - self.risk_config.stop_loss_pct)
            take_profit = entry_price * (1 + self.risk_config.take_profit_pct)
        elif signal_type == SignalType.SELL:
            # For short positions
            stop_loss = entry_price * (1 + self.risk_config.stop_loss_pct)
            take_profit = entry_price * (1 - self.risk_config.take_profit_pct)
        else:
            return None, None

        return stop_loss, take_profit

    def update_position_count(self, change: int):
        """
        Update the current position count

        Args:
            change: Change in position count (+1 for open, -1 for close)
        """
        self.positions_count = max(0, self.positions_count + change)
        self.logger.info(f"Position count updated: {self.positions_count}")

    def update_daily_pnl(self, pnl: float):
        """
        Update daily P&L

        Args:
            pnl: P&L change
        """
        self.daily_pnl += pnl
        self.logger.info(f"Daily P&L updated: {self.daily_pnl:.2f}")

    def reset_daily_stats(self):
        """Reset daily statistics"""
        self.daily_pnl = 0.0
        self.positions_count = 0
        self.logger.info("Daily statistics reset")

    def get_risk_status(self) -> Dict[str, Any]:
        """
        Get current risk management status

        Returns:
            Dictionary with risk status information
        """
        return {
            "daily_pnl": self.daily_pnl,
            "positions_count": self.positions_count,
            "max_positions": self.risk_config.max_positions,
            "max_daily_loss": self.risk_config.max_daily_loss,
            "position_size_pct": self.risk_config.position_size,
            "stop_loss_pct": self.risk_config.stop_loss_pct,
            "take_profit_pct": self.risk_config.take_profit_pct,
            "enabled": self.risk_config.enabled,
        }
