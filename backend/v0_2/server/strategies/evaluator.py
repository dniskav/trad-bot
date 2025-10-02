#!/usr/bin/env python3
"""
Signal Evaluator
Evaluates trading signals based on strategy conditions
"""

from typing import List, Dict, Any, Optional
from .models import SignalCondition, SignalConfig, SignalType, StrategySignal
from .indicators import IndicatorFactory
from backend.shared.logger import get_logger


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
                result = self._evaluate_condition(condition, market_data, signal_config.signal_type)
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

            # If conditions are not met, emit a HOLD with explanation so UI can show "por qué"
            if len(conditions_met) > 0:
                hold_reason = " | ".join(reasoning_parts)
                return StrategySignal(
                    strategy_name=market_data.get("strategy_name", "unknown"),
                    signal_type=SignalType.HOLD,
                    confidence=0.0,
                    entry_price=market_data.get("current_price", 0.0),
                    reasoning=hold_reason,
                    metadata={
                        "conditions_met": sum(1 for m in conditions_met if m),
                        "total_conditions": len(signal_config.conditions),
                        "market_data": market_data,
                    },
                )

            return None

        except Exception as e:
            self.logger.error(f"Error evaluating signal: {e}")
            return None

    def _evaluate_condition(
        self, condition: SignalCondition, market_data: Dict[str, Any], signal_type: SignalType
    ) -> Dict[str, Any]:
        """
        Evaluate a single condition

        Args:
            condition: Condition to evaluate
            market_data: Current market data
            signal_type: The signal type (BUY/SELL) this condition is for

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

            # Generate detailed reasoning based on indicator type and condition
            reasoning = self._generate_detailed_reasoning(condition, indicator_value, comparison_value, market_data, signal_type)

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

    def _generate_detailed_reasoning(
        self, condition: SignalCondition, indicator_value: float, comparison_value: float, market_data: Dict[str, Any], signal_type: SignalType
    ) -> str:
        """
        Generate detailed reasoning for different indicator types and conditions
        
        Args:
            condition: Signal condition being evaluated
            indicator_value: Current indicator value
            comparison_value: Value being compared against
            market_data: Current market data
            signal_type: The signal type (BUY/SELL) this condition is for
            
        Returns:
            Detailed reasoning string
        """
        ind = condition.indicator.lower()
        current_price = market_data.get("current_price", 0.0)
        
        if ind.startswith("rsi"):
            return self._rsi_reasoning(condition, indicator_value, comparison_value, signal_type)
        elif ind.startswith("price_trend") or ind.startswith("trend"):
            return self._trend_reasoning(indicator_value, market_data)
        elif ind.startswith("macd"):
            return self._macd_reasoning(condition, indicator_value, comparison_value, market_data, signal_type)
        elif ind.startswith("sma"):
            return self._sma_reasoning(condition, indicator_value, comparison_value, market_data, signal_type)
        elif ind.startswith("volume"):
            return self._volume_reasoning(condition, indicator_value, comparison_value)
        else:
            return f"{condition.indicator}: {indicator_value:.4f} {condition.operator} {comparison_value:.4f}"

    def _rsi_reasoning(self, condition: SignalCondition, indicator_value: float, comparison_value: float, signal_type: SignalType) -> str:
        """Generate RSI-specific reasoning"""
        # Determine RSI label
        try:
            parts = condition.indicator.split("_")
            label = f"RSI ({parts[1]})" if len(parts) > 1 and parts[1].isdigit() else "RSI"
        except Exception:
            label = "RSI"
            
        # Determine RSI interpretation
        if indicator_value > 70:
            interpretation = "zona de sobrecompra"
        elif indicator_value < 30:
            interpretation = "zona de sobreventa"
        elif indicator_value >= 50:
            interpretation = "tendencia alcista"
        else:
            interpretation = "tendencia bajista"
            
        if signal_type.value == "BUY":
            if indicator_value >= comparison_value:
                return f"{label}: {indicator_value:.2f} ✅ En {interpretation} (requiere < {comparison_value})"
            else:
                return f"{label}: {indicator_value:.2f} ❌ NO en {interpretation} (requiere < {comparison_value})"
        else:  # SELL
            if indicator_value <= comparison_value:
                return f"{label}: {indicator_value:.2f} ✅ En {interpretation} (requiere > {comparison_value})"
            else:
                return f"{label}: {indicator_value:.2f} ❌ NO en {interpretation} (requiere > {comparison_value})"

    def _trend_reasoning(self, indicator_value: float, market_data: Dict[str, Any]) -> str:
        """Generate trend-specific reasoning"""
        prev = market_data.get("prev_price")
        current_price = market_data.get("current_price", 0.0)
        
        if prev is not None:
            pct = ((indicator_value) * 100.0) if abs(indicator_value) < 1 else indicator_value
            direction = "alcista" if indicator_value > 0 else "bajista"
            return f"📈 Tendencia {direction}: {pct:.2f}% ({prev:.5f} → {current_price:.5f})"
        else:
            return f"📈 Tendencia: {indicator_value:.4f}"

    def _macd_reasoning(self, condition: SignalCondition, indicator_value, comparison_value: float, market_data: Dict[str, Any], signal_type: SignalType) -> str:
        """Generate MACD-specific reasoning"""
        h_prev = market_data.get("macd_hist_prev")
        h_now = market_data.get("macd_hist")
        
        if h_prev is not None and h_now is not None:
            histogram_direction = "crece" if h_now > h_prev else "decrece"
            momentum = "🥺 Momentum bajista" if h_now < h_prev < 0 else "🚀 Momentum alcista" if h_now > h_prev > 0 else "😐 Momentum débil"
            return f"MACD: {indicator_value:.6f} | Histograma {histogram_direction} | {momentum}"
        else:
            if signal_type.value == "BUY":
                signal_condition = "positivo" if indicator_value >= comparison_value else "negativo"
                return f"MACD: {indicator_value:.6f} ❌ Momentum {signal_condition} (require >= {comparison_value})"
            else:
                signal_condition = "negativo" if indicator_value <= comparison_value else "positivo"  
                return f"MACD: {indicator_value:.6f} ❌ Momentum {signal_condition} (require <= {comparison_value})"

    def _sma_reasoning(self, condition: SignalCondition, indicator_value: float, comparison_value: float, market_data: Dict[str, Any], signal_type: SignalType) -> str:
        """Generate SMA-specific reasoning with detailed analysis"""
        try:
            parts = condition.indicator.split("_")
            if len(parts) > 1 and parts[1].isdigit():
                label = f"SMA ({parts[1]})"
                period = int(parts[1])
            elif len(parts) > 1 and parts[1].lower() in ("fast", "slow"):
                label = "Media rápida" if parts[1].lower() == "fast" else "Media lenta"
                period = 8 if parts[1].lower() == "fast" else 21  # Default periods
            else:
                label = "SMA"
                period = 20
        except Exception:
            label = "SMA"
            period = 20
            
        current_price = market_data.get("current_price", 0.0)
        
        # Calculate slopes and trends
        try:
            indicator = self.indicator_factory.get_indicator(condition.indicator)
            if hasattr(indicator, 'values') and len(indicator.values) >= 3:
                sma_values = indicator.values[-3:]  # Last 3 SMA values
                slope = "alcista" if sma_values[-1] > sma_values[-2] else "bajista"
                trend_strength = abs(sma_values[-1] - sma_values[-2]) / sma_values[-2] * 100
                
                if condition.operator == ">":
                    # SMA Fast > SMA Slow (crossover)
                    if indicator_value > comparison_value:
                        return f"✅ {label} ({indicator_value:.4f}) > Referencia ({comparison_value:.4f}) - Cruce alcista"
                    else:
                        gap = ((comparison_value - indicator_value) / comparison_value) * 100
                        return f"❌ {label} ({indicator_value:.4f}) NO supera referencia ({comparison_value:.4f}) - Falta {gap:.1f}% para cruce"
                        
                elif condition.operator == "<":
                    # SMA Fast < SMA Slow (bearish crossover)
                    if indicator_value < comparison_value:
                        return f"✅ {label} ({indicator_value:.4f}) < Referencia ({comparison_value:.4f}) - Cruce bajista"
                    else:
                        gap = ((indicator_value - comparison_value) / comparison_value) * 100
                        return f"❌ {label} ({indicator_value:.4f}) NO por debajo de referencia ({comparison_value:.4f}) - Sobrepasada por {gap:.1f}%"
                else:
                    # Single SMA condition
                    if signal_type.value == "BUY":
                        target_text = "precio" if comparison_value == current_price else f"{comparison_value:.4f}"
                        return f"❌ {label} ({indicator_value:.4f}) NO supera precio ({target_text}) - Pendiente {slope}, fuerza: {trend_strength:.1f}%"
                    else:
                        target_text = "precio" if comparison_value == current_price else f"{comparison_value:.4f}"
                        return f"❌ {label} ({indicator_value:.4f}) NO por debajo de precio ({target_text}) - Pendiente {slope}, fuerza: {trend_strength:.1f}%"
            else:
                # Fallback when no historical data available
                return f"{label}: {indicator_value:.4f} {condition.operator} {comparison_value:.4f}"
        except Exception:
            return f"{label}: {indicator_value:.4f} {condition.operator} {comparison_value:.4f}"

    def _volume_reasoning(self, condition: SignalCondition, indicator_value: float, comparison_value: float) -> str:
        """Generate volume-specific reasoning"""
        if "ratio" in condition.indicator:
            if indicator_value > comparison_value:
                volume_strength = "HIGH" if indicator_value > 1.5 else "MEDIUM"
                return f"📈 Volumen {volume_strength}: {indicator_value:.2f}x promedio ✅"
            else:
                volume_strength = "LOW" if indicator_value < 0.8 else "NORMAL"
                return f"📉 Volumen {volume_strength}: {indicator_value:.2f}x promedio (requiere {comparison_value}x)"
        elif "ma" in condition.indicator:
            return f"📊 Volumen promedio: {indicator_value:.0f} (umbral: {comparison_value:.0f})"
        else:
            return f"📊 Volumen: {indicator_value:.0f} {condition.operator} {comparison_value:.0f}"

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
