#!/usr/bin/env python3
"""
MACD (Moving Average Convergence Divergence) Indicator
"""

from typing import List, Optional, Tuple, Dict, Any
import numpy as np
from .base import BaseIndicator


class MACDIndicator(BaseIndicator):
    """MACD indicator with signal line and histogram"""

    def __init__(self, name: str, params: Dict[str, Any]):
        super().__init__(name, params)
        self.fast_period = params.get("fast_period", 12)
        self.slow_period = params.get("slow_period", 26)
        self.signal_period = params.get("signal_period", 9)

    def calculate(self, data: List[float]) -> List[float]:
        """
        Calculate MACD values

        Args:
            data: Price data (usually closes)

        Returns:
            List of MACD line values
        """
        if len(data) < self.slow_period:
            return []

        # Calculate EMAs
        ema_fast = self._calculate_ema(data, self.fast_period)
        ema_slow = self._calculate_ema(data, self.slow_period)

        # Align EMAs (take the longer one's length)
        min_length = min(len(ema_fast), len(ema_slow))
        ema_fast = ema_fast[-min_length:]
        ema_slow = ema_slow[-min_length:]

        # Calculate MACD line
        macd_line = [fast - slow for fast, slow in zip(ema_fast, ema_slow)]

        # Calculate signal line (EMA of MACD)
        if len(macd_line) >= self.signal_period:
            signal_line = self._calculate_ema(macd_line, self.signal_period)
            # Align lengths
            min_length = min(len(macd_line), len(signal_line))
            macd_line = macd_line[-min_length:]
            signal_line = signal_line[-min_length:]

            # Store additional data
            self.signal_line = signal_line
            self.histogram = [
                macd - signal for macd, signal in zip(macd_line, signal_line)
            ]
        else:
            self.signal_line = []
            self.histogram = []

        return macd_line

    def _calculate_ema(self, data: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average"""
        if len(data) < period:
            return []

        ema_values = []
        multiplier = 2 / (period + 1)

        # First EMA is SMA
        ema = sum(data[:period]) / period
        ema_values.append(ema)

        # Calculate subsequent EMAs
        for i in range(period, len(data)):
            ema = (data[i] * multiplier) + (ema * (1 - multiplier))
            ema_values.append(ema)

        return ema_values

    def get_latest(self) -> Optional[float]:
        """Get latest MACD value"""
        return self.values[-1] if self.values else None

    def get_signal_line(self) -> List[float]:
        """Get signal line values"""
        return getattr(self, "signal_line", [])

    def get_histogram(self) -> List[float]:
        """Get histogram values"""
        return getattr(self, "histogram", [])

    def validate_params(self) -> bool:
        """Validate MACD parameters"""
        if not all(
            isinstance(p, int) and p > 0
            for p in [self.fast_period, self.slow_period, self.signal_period]
        ):
            self.logger.error(
                f"Invalid MACD periods: {self.fast_period}, {self.slow_period}, {self.signal_period}"
            )
            return False
        if self.fast_period >= self.slow_period:
            self.logger.error(f"Fast period must be less than slow period")
            return False
        return True
