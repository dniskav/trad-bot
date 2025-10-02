#!/usr/bin/env python3
"""
Base Indicator Class
Abstract base class for all technical indicators
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import numpy as np
from backend.shared.logger import get_logger


class BaseIndicator(ABC):
    """Abstract base class for technical indicators"""

    def __init__(self, name: str, params: Dict[str, Any]):
        self.name = name
        self.params = params
        self.logger = get_logger(f"indicator.{name}")
        self.values: List[float] = []
        self.enabled = True

    @abstractmethod
    def calculate(self, data: List[float]) -> List[float]:
        """
        Calculate indicator values

        Args:
            data: Input data (usually closes, volumes, etc.)

        Returns:
            List of calculated indicator values
        """
        pass

    @abstractmethod
    def get_latest(self) -> Optional[float]:
        """
        Get the latest calculated value

        Returns:
            Latest indicator value or None if not calculated
        """
        pass

    def update(self, data: List[float]) -> List[float]:
        """
        Update indicator with new data

        Args:
            data: New input data

        Returns:
            Updated indicator values
        """
        if not self.enabled:
            return []

        self.values = self.calculate(data)
        return self.values

    def validate_params(self) -> bool:
        """
        Validate indicator parameters

        Returns:
            True if parameters are valid
        """
        return True

    def get_info(self) -> Dict[str, Any]:
        """
        Get indicator information

        Returns:
            Dictionary with indicator info
        """
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "params": self.params,
            "enabled": self.enabled,
            "values_count": len(self.values),
            "latest_value": self.get_latest(),
        }
