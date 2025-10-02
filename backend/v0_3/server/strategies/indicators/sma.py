#!/usr/bin/env python3
"""
Simple Moving Average (SMA) Indicator
"""

from typing import List, Optional, Dict, Any
import numpy as np
from .base import BaseIndicator


class SMAIndicator(BaseIndicator):
    """Simple Moving Average indicator"""

    def __init__(self, name: str, params: Dict[str, Any]):
        super().__init__(name, params)
        self.period = params.get("period", 20)

    def calculate(self, data: List[float]) -> List[float]:
        """
        Calculate SMA values

        Args:
            data: Price data (usually closes)

        Returns:
            List of SMA values
        """
        if len(data) < self.period:
            return []

        sma_values = []
        for i in range(self.period - 1, len(data)):
            window = data[i - self.period + 1 : i + 1]
            sma = sum(window) / self.period
            sma_values.append(sma)

        return sma_values

    def get_latest(self) -> Optional[float]:
        """Get latest SMA value"""
        return self.values[-1] if self.values else None

    def validate_params(self) -> bool:
        """Validate SMA parameters"""
        if not isinstance(self.period, int) or self.period <= 0:
            self.logger.error(f"Invalid SMA period: {self.period}")
            return False
        return True
