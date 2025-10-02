#!/usr/bin/env python3
"""
Relative Strength Index (RSI) Indicator
"""

from typing import List, Optional, Dict, Any
import numpy as np
from .base import BaseIndicator


class RSIIndicator(BaseIndicator):
    """Relative Strength Index indicator"""

    def __init__(self, name: str, params: Dict[str, Any]):
        super().__init__(name, params)
        self.period = params.get("period", 14)

    def calculate(self, data: List[float]) -> List[float]:
        """
        Calculate RSI values

        Args:
            data: Price data (usually closes)

        Returns:
            List of RSI values
        """
        if len(data) < self.period + 1:
            return []

        # Calculate price changes
        deltas = [data[i] - data[i - 1] for i in range(1, len(data))]

        # Separate gains and losses
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]

        rsi_values = []

        # Calculate initial average gain and loss
        avg_gain = sum(gains[: self.period]) / self.period
        avg_loss = sum(losses[: self.period]) / self.period

        # Calculate RSI for the first period
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        rsi_values.append(rsi)

        # Calculate RSI for remaining periods using smoothed averages
        for i in range(self.period, len(deltas)):
            avg_gain = (avg_gain * (self.period - 1) + gains[i]) / self.period
            avg_loss = (avg_loss * (self.period - 1) + losses[i]) / self.period

            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            rsi_values.append(rsi)

        return rsi_values

    def get_latest(self) -> Optional[float]:
        """Get latest RSI value"""
        return self.values[-1] if self.values else None

    def validate_params(self) -> bool:
        """Validate RSI parameters"""
        if not isinstance(self.period, int) or self.period <= 0:
            self.logger.error(f"Invalid RSI period: {self.period}")
            return False
        return True
