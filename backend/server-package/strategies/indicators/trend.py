#!/usr/bin/env python3
"""
Price Trend Indicator
Calculates price trend and momentum over a lookback period
"""

from typing import List, Optional, Dict, Any
import numpy as np
from .base import BaseIndicator


class TrendIndicator(BaseIndicator):
    """Price trend indicator for momentum analysis"""
    
    def __init__(self, name: str, params: Dict[str, Any]):
        super().__init__(name, params)
        self.lookback_periods = params.get("lookback_periods", 3)
        self.min_price_change = params.get("min_price_change", 0.001)
        
    def calculate(self, data: List[float]) -> List[float]:
        """
        Calculate trend values
        
        Args:
            data: Price data (usually closes)
            
        Returns:
            List of trend values (price change percentage)
        """
        if len(data) < self.lookback_periods:
            return []
            
        trend_values = []
        
        for i in range(self.lookback_periods - 1, len(data)):
            # Get the lookback window
            window = data[i - self.lookback_periods + 1:i + 1]
            
            # Calculate price change percentage
            price_change = (window[-1] - window[0]) / window[0]
            trend_values.append(price_change)
            
        return trend_values
    
    def get_latest(self) -> Optional[float]:
        """Get latest trend value"""
        return self.values[-1] if self.values else None
    
    def get_trend_direction(self) -> Optional[str]:
        """Get trend direction based on latest value"""
        if not self.values:
            return None
            
        latest_trend = self.values[-1]
        
        if latest_trend > self.min_price_change:
            return "UP"
        elif latest_trend < -self.min_price_change:
            return "DOWN"
        else:
            return "SIDEWAYS"
    
    def get_confidence(self) -> float:
        """Get confidence based on trend strength"""
        if not self.values:
            return 0.0
            
        latest_trend = abs(self.values[-1])
        return min(0.8, latest_trend / self.min_price_change * 0.3)
    
    def validate_params(self) -> bool:
        """Validate trend indicator parameters"""
        if not isinstance(self.lookback_periods, int) or self.lookback_periods <= 0:
            self.logger.error(f"Invalid lookback periods: {self.lookback_periods}")
            return False
        if not isinstance(self.min_price_change, (int, float)) or self.min_price_change <= 0:
            self.logger.error(f"Invalid min price change: {self.min_price_change}")
            return False
        return True
