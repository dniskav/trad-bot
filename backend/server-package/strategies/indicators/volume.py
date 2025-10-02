#!/usr/bin/env python3
"""
Volume-based Indicators
"""

from typing import List, Optional, Dict, Any
import numpy as np
from .base import BaseIndicator


class VolumeIndicator(BaseIndicator):
    """Volume-based indicators (Volume MA, Volume Ratio, etc.)"""

    def __init__(self, name: str, params: Dict[str, Any]):
        super().__init__(name, params)
        self.type = params.get("type", "volume_ma")  # volume_ma, volume_ratio
        self.period = params.get("period", 20)

    def calculate(self, data: List[float]) -> List[float]:
        """
        Calculate volume-based indicator values

        Args:
            data: Volume data

        Returns:
            List of calculated values
        """
        if len(data) < self.period:
            return []

        if self.type == "volume_ma":
            return self._calculate_volume_ma(data)
        elif self.type == "volume_ratio":
            return self._calculate_volume_ratio(data)
        else:
            self.logger.error(f"Unknown volume indicator type: {self.type}")
            return []

    def _calculate_volume_ma(self, data: List[float]) -> List[float]:
        """Calculate Volume Moving Average"""
        ma_values = []
        for i in range(self.period - 1, len(data)):
            window = data[i - self.period + 1 : i + 1]
            ma = sum(window) / self.period
            ma_values.append(ma)
        return ma_values

    def _calculate_volume_ratio(self, data: List[float]) -> List[float]:
        """Calculate Volume Ratio (current volume / average volume)"""
        if len(data) < self.period + 1:
            return []

        ratio_values = []
        for i in range(self.period, len(data)):
            current_volume = data[i]
            avg_volume = sum(data[i - self.period : i]) / self.period
            ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            ratio_values.append(ratio)
        return ratio_values

    def get_latest(self) -> Optional[float]:
        """Get latest volume indicator value"""
        return self.values[-1] if self.values else None

    def validate_params(self) -> bool:
        """Validate volume indicator parameters"""
        if not isinstance(self.period, int) or self.period <= 0:
            self.logger.error(f"Invalid volume indicator period: {self.period}")
            return False
        if self.type not in ["volume_ma", "volume_ratio"]:
            self.logger.error(f"Invalid volume indicator type: {self.type}")
            return False
        return True
