#!/usr/bin/env python3
"""
Signal Evaluator
Evaluates trading signals based on strategy conditions
"""

from typing import List, Dict, Any, Optional
from .models import SignalCondition, SignalConfig, SignalType, StrategySignal
from .indicators import IndicatorFactory
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from shared.logger import get_logger


class SignalEvaluator:
    """Evaluates trading signals based on strategy conditions"""

    def __init__(self, indicator_factory: IndicatorFactory):
        self.indicator_factory = indicator_factory
        self.logger = get_logger("signal_evaluator")

    def evaluate_signal(
        self, signal_config: SignalConfig, market_data: Dict[str, Any]
    ) -> Optional[StrategySignal]:
        """
        Evaluate a trading signal based on conditions

        Args:
            signal_config: Signal configuration
            market_data: Current market data

        Returns:
            StrategySignal if conditions are met, None otherwise
        """
        if not signal_config.enabled:
            return None

        try:
            # Evaluate all conditions
            conditions_met = []
            reasoning_parts = []

            for condition in signal_config.conditions:
                result = self._evaluate_condition(condition, market_data)
                conditions_met.append(result["met"])
                reasoning_parts.append(result["reasoning"])

            # Check if all conditions are met (AND logic by default)
            all_met = all(conditions_met)

            if all_met and len(conditions_met) > 0:
                confidence = self._calculate_confidence(
                    conditions_met, signal_config.conditions
                )

                if confidence >= signal_config.confidence:
                    reasoning = " | ".join(reasoning_parts)

                    return StrategySignal(
                        strategy_name=market_data.get("strategy_name", "unknown"),
                        signal_type=signal_config.signal_type,
                        confidence=confidence,
                        entry_price=market_data.get("current_price", 0.0),
                        reasoning=reasoning,
                        metadata={
                            "conditions_met": len(conditions_met),
                            "total_conditions": len(signal_config.conditions),
                            "market_data": market_data,
                        },
                    )

            return None

        except Exception as e:
            self.logger.error(f"Error evaluating signal: {e}")
            return None

    def _evaluate_condition(
        self, condition: SignalCondition, market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate a single condition

        Args:
            condition: Condition to evaluate
            market_data: Current market data

        Returns:
            Dictionary with 'met' boolean and 'reasoning' string
        """
        try:
            # Get indicator value
            indicator = self.indicator_factory.get_indicator(condition.indicator)
            indicator_value = indicator.get_latest()

            if indicator_value is None:
                return {
                    "met": False,
                    "reasoning": f"{condition.indicator} not available",
                }

            # Get comparison value
            if isinstance(condition.value, str):
                # Reference to another indicator
                if condition.value.startswith("indicator:"):
                    ref_indicator_name = condition.value.replace("indicator:", "")
                    ref_indicator = self.indicator_factory.get_indicator(
                        ref_indicator_name
                    )
                    comparison_value = ref_indicator.get_latest()
                    if comparison_value is None:
                        return {
                            "met": False,
                            "reasoning": f"Reference indicator {ref_indicator_name} not available",
                        }
                else:
                    # Direct value
                    comparison_value = float(condition.value)
            else:
                comparison_value = float(condition.value)

            # Evaluate condition
            met = self._compare_values(
                indicator_value, condition.operator, comparison_value
            )

            reasoning = f"{condition.indicator}({indicator_value:.4f}) {condition.operator} {comparison_value:.4f}"

            return {"met": met, "reasoning": reasoning}

        except Exception as e:
            self.logger.error(f"Error evaluating condition: {e}")
            return {"met": False, "reasoning": f"Error: {str(e)}"}

    def _compare_values(self, value1: float, operator: str, value2: float) -> bool:
        """
        Compare two values using the specified operator

        Args:
            value1: First value
            operator: Comparison operator
            value2: Second value

        Returns:
            True if condition is met
        """
        if operator == ">":
            return value1 > value2
        elif operator == "<":
            return value1 < value2
        elif operator == ">=":
            return value1 >= value2
        elif operator == "<=":
            return value1 <= value2
        elif operator == "==":
            return abs(value1 - value2) < 1e-10  # Float comparison
        elif operator == "!=":
            return abs(value1 - value2) >= 1e-10
        else:
            self.logger.error(f"Unknown operator: {operator}")
            return False

    def _calculate_confidence(
        self, conditions_met: List[bool], conditions: List[SignalCondition]
    ) -> float:
        """
        Calculate signal confidence based on met conditions

        Args:
            conditions_met: List of boolean results
            conditions: List of conditions

        Returns:
            Confidence value between 0.0 and 1.0
        """
        if not conditions_met:
            return 0.0

        # Simple confidence calculation: percentage of conditions met
        met_count = sum(conditions_met)
        total_count = len(conditions_met)

        base_confidence = met_count / total_count

        # Adjust confidence based on condition complexity
        # More conditions = higher confidence when all are met
        complexity_factor = min(1.0, total_count / 3.0)  # Cap at 3 conditions

        return min(1.0, base_confidence * (0.5 + 0.5 * complexity_factor))
