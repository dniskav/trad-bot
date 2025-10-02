#!/usr/bin/env python3
"""
Indicator Factory
Factory for creating technical indicators
"""

from typing import Dict, Any, Type
from .base import BaseIndicator
from .sma import SMAIndicator
from .rsi import RSIIndicator
from .macd import MACDIndicator
from .volume import VolumeIndicator
from .trend import TrendIndicator
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from shared.logger import get_logger


class IndicatorFactory:
    """Factory for creating technical indicators"""

    # Registry of available indicators
    _indicators: Dict[str, Type[BaseIndicator]] = {
        "sma": SMAIndicator,
        "rsi": RSIIndicator,
        "macd": MACDIndicator,
        "volume": VolumeIndicator,
        "trend": TrendIndicator,
    }

    def __init__(self):
        self.logger = get_logger("indicator_factory")
        self._instances: Dict[str, BaseIndicator] = {}

    def create_indicator(
        self, name: str, indicator_type: str, params: Dict[str, Any]
    ) -> BaseIndicator:
        """
        Create a new indicator instance

        Args:
            name: Unique name for the indicator
            indicator_type: Type of indicator (sma, rsi, macd, volume)
            params: Indicator parameters

        Returns:
            BaseIndicator instance

        Raises:
            ValueError: If indicator type is not supported
        """
        if indicator_type not in self._indicators:
            available = ", ".join(self._indicators.keys())
            raise ValueError(
                f"Unknown indicator type: {indicator_type}. Available: {available}"
            )

        if name in self._instances:
            self.logger.warning(
                f"Indicator '{name}' already exists, returning existing instance"
            )
            return self._instances[name]

        indicator_class = self._indicators[indicator_type]
        indicator = indicator_class(name, params)

        if not indicator.validate_params():
            raise ValueError(
                f"Invalid parameters for {indicator_type} indicator: {params}"
            )

        self._instances[name] = indicator
        self.logger.info(f"Created {indicator_type} indicator: {name}")

        return indicator

    def get_indicator(self, name: str) -> BaseIndicator:
        """
        Get an existing indicator instance

        Args:
            name: Indicator name

        Returns:
            BaseIndicator instance

        Raises:
            KeyError: If indicator doesn't exist
        """
        if name not in self._instances:
            raise KeyError(f"Indicator '{name}' not found")
        return self._instances[name]

    def get_all_indicators(self) -> Dict[str, BaseIndicator]:
        """Get all indicator instances"""
        return self._instances.copy()

    def remove_indicator(self, name: str) -> bool:
        """
        Remove an indicator instance

        Args:
            name: Indicator name

        Returns:
            True if removed, False if not found
        """
        if name in self._instances:
            del self._instances[name]
            self.logger.info(f"Removed indicator: {name}")
            return True
        return False

    def get_available_types(self) -> list:
        """Get list of available indicator types"""
        return list(self._indicators.keys())

    def register_indicator(
        self, indicator_type: str, indicator_class: Type[BaseIndicator]
    ):
        """
        Register a new indicator type

        Args:
            indicator_type: Type name
            indicator_class: Indicator class
        """
        if not issubclass(indicator_class, BaseIndicator):
            raise ValueError("Indicator class must inherit from BaseIndicator")

        self._indicators[indicator_type] = indicator_class
        self.logger.info(f"Registered new indicator type: {indicator_type}")

    def clear_all(self):
        """Clear all indicator instances"""
        self._instances.clear()
        self.logger.info("Cleared all indicator instances")
