#!/usr/bin/env python3
"""
Signal Evaluator Service Implementation
Implementación de ISignalEvaluator como servicio independiente
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from ...domain.models.strategy import (
    SignalConfig,
    SignalCondition,
    StrategySignal,
    SignalType,
    SignalGenerationResult,
    SignalStrength,
)
from ...domain.models.position import Money
from ...domain.ports.strategy_ports import ISignalEvaluator


class SignalEvaluatorService:
    """Servicio de evaluación de señales independiente"""

    def __init__(self):
        self.evaluation_cache: Dict[str, Any] = {}
        self.cache_ttl_seconds = 30

    async def evaluate_signals(
        self,
        signal_configs: List[SignalConfig],
        indicators_data: Dict[str, Any],
        market_data: Dict[str, Any],
    ) -> SignalGenerationResult:
        """Evaluar lista de configuraciones de señal"""

        processing_start = datetime.now()

        for signal_config in signal_configs:
            if not signal_config.enabled:
                continue

            signal_result = await self._evaluate_single_signal(
                signal_config, indicators_data, market_data
            )

            if signal_result:
                processing_time = (
                    datetime.now() - processing_start
                ).total_seconds() * 1000
                signal_result.processing_time_ms = processing_time
                return signal_result

        # Si no se generó ninguna señal
        processing_time = (datetime.now() - processing_start).total_seconds() * 1000
        return SignalGenerationResult(
            signal=None,
            indicators_data=indicators_data,
            conditions_evaluated={},
            reasoning_parts=[],
            confidence_calculation={},
            errors=[],
            processing_time_ms=processing_time,
        )

    async def evaluate_single_signal(
        self,
        signal_config: SignalConfig,
        indicators_data: Dict[str, Any],
        market_data: Dict[str, Any],
    ) -> Optional[StrategySignal]:
        """Evaluar una sola configuración de señal"""

        result = await self._evaluate_single_signal(
            signal_config, indicators_data, market_data
        )
        return result.signal if result else None

    async def _evaluate_single_signal(
        self,
        signal_config: SignalConfig,
        indicators_data: Dict[str, Any],
        market_data: Dict[str, Any],
    ) -> Optional[SignalGenerationResult]:
        """Evaluar una sola señal interna"""

        try:
            conditions_evaluated = {}
            reasoning_parts = []
            errors = []

            # Evaluar todas las condiciones
            conditions_met = []

            for condition in signal_config.conditions:
                if not condition.enabled:
                    continue

                condition_result = await self._evaluate_condition(
                    condition, indicators_data, market_data
                )

                condition_key = (
                    f"{condition.indicator}_{condition.operator}_{condition.value}"
                )
                conditions_evaluated[condition_key] = condition_result["met"]

                conditions_met.append(condition_result["met"])
                reasoning_parts.append(condition_result["reasoning"])

            # Verificar si todas las condiciones se cumplen según la lógica
            if signal_config.logic_type == "AND":
                all_conditions_met = len(conditions_evaluated) > 0 and all(
                    conditions_evaluated.values()
                )
            elif signal_config.logic_type == "OR":
                all_conditions_met = len(conditions_evaluated) > 0 and any(
                    conditions_evaluated.values()
                )
            else:
                all_conditions_met = len(conditions_evaluated) > 0 and all(
                    conditions_evaluated.values()
                )

            if not all_conditions_met:
                return SignalGenerationResult(
                    signal=None,
                    indicators_data=indicators_data,
                    conditions_evaluated=conditions_evaluated,
                    reasoning_parts=reasoning_parts,
                    confidence_calculation={},
                    errors=errors,
                    processing_time_ms=0,
                )

            # Calcular confianza
            confidence_calculation = await self._calculate_confidence(
                indicators_data, signal_config, conditions_evaluated
            )

            confidence = confidence_calculation.get("final_confidence", 0.0)

            # Verificar confianza mínima
            if confidence < signal_config.min_confidence:
                errors.append(
                    f"Confidence {confidence:.2f} below minimum {signal_config.min_confidence}"
                )
                return SignalGenerationResult(
                    signal=None,
                    indicators_data=indicators_data,
                    conditions_evaluated=conditions_evaluated,
                    reasoning_parts=reasoning_parts,
                    confidence_calculation=confidence_calculation,
                    errors=errors,
                    processing_time_ms=0,
                )

            # Crear señal
            signal = await self._create_signal(
                signal_config, confidence, reasoning_parts, market_data, indicators_data
            )

            return SignalGenerationResult(
                signal=signal,
                indicators_data=indicators_data,
                conditions_evaluated=conditions_evaluated,
                reasoning_parts=reasoning_parts,
                confidence_calculation=confidence_calculation,
                errors=errors,
                processing_time_ms=0,
            )

        except Exception as e:
            return SignalGenerationResult(
                signal=None,
                indicators_data=indicators_data,
                conditions_evaluated={},
                reasoning_parts=[],
                confidence_calculation={},
                errors=[f"Signal evaluation error: {str(e)}"],
                processing_time_ms=0,
            )

    async def _evaluate_condition(
        self,
        condition: SignalCondition,
        indicators_data: Dict[str, Any],
        market_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluar una condición específica"""

        try:
            # Obtener valor del indicador
            indicator_value = indicators_data.get(condition.indicator)

            if indicator_value is None:
                return {
                    "met": False,
                    "reasoning": f"Indicator {condition.indicator} not found in data",
                }

            # Extraer el valor numérico según el tipo de indicador
            actual_value = self._extract_indicator_value(indicator_value)

            if actual_value is None:
                return {
                    "met": False,
                    "reasoning": f"Cannot extract value from indicator {condition.indicator}",
                }

            # Evaluar condición según operador
            met = self._evaluate_operator(
                actual_value, condition.operator, condition.value
            )

            reasoning = f"{condition.indicator} ({actual_value:.4f}) {condition.operator} {condition.value}: {met}"

            return {"met": met, "reasoning": reasoning}

        except Exception as e:
            return {"met": False, "reasoning": f"Error evaluating condition: {str(e)}"}

    def _extract_indicator_value(
        self, indicator_data: Dict[str, Any]
    ) -> Optional[float]:
        """Extraer valor numérico del dato del indicador"""

        # Diferentes campos que pueden contener el valor
        value_fields = ["value", "rsi", "macd_line", "histogram", "price"]

        for field in value_fields:
            if field in indicator_data and indicator_data[field] is not None:
                try:
                    return float(indicator_data[field])
                except (ValueError, TypeError):
                    continue

        # Si es un valor directo
        if isinstance(indicator_data, (int, float)):
            return float(indicator_data)

        return None

    def _evaluate_operator(
        self, actual_value: float, operator: str, target_value: Any
    ) -> bool:
        """Evaluar operador comparando valor actual con objetivo"""

        try:
            target_val = float(target_value)

            if operator == ">":
                return actual_value > target_val
            elif operator == "<":
                return actual_value < target_val
            elif operator == ">=":
                return actual_value >= target_val
            elif operator == "<=":
                return actual_value <= target_val
            elif operator == "==":
                return abs(actual_value - target_val) < 0.1  # Tolerancia
            else:
                return False

        except (ValueError, TypeError):
            return False

    async def _calculate_confidence(
        self,
        indicators_data: Dict[str, Any],
        signal_config: SignalConfig,
        conditions_evaluated: Dict[str, bool],
    ) -> Dict[str, Any]:
        """Calcular nivel de confianza de la señal"""

        confidence_calculation = {}

        # Base confidence basada en número de condiciones cumplidas
        total_conditions = len(conditions_evaluated)
        met_conditions = sum(1 for met in conditions_evaluated.values() if met)

        base_confidence = (
            met_conditions / total_conditions if total_conditions > 0 else 0
        )

        confidence_calculation["base_confidence"] = base_confidence
        confidence_calculation["conditions_met"] = met_conditions
        confidence_calculation["total_conditions"] = total_conditions

        # Ajustar según fuerza de los indicadores
        indicator_strengths = []

        for indicator_name, indicator_data in indicators_data.items():
            if indicator_data and "error" not in indicator_data:
                strength = self._get_indicator_strength(indicator_data)
                indicator_strengths.append(strength)

        if indicator_strengths:
            avg_strength = sum(indicator_strengths) / len(indicator_strengths)
            confidence_calculation["indicator_avg_strength"] = avg_strength

            # Ajustar confianza según fuerza promedio
            strength_multiplier = 0.8 + (avg_strength * 0.4)  # 0.8 - 1.2
            final_confidence = base_confidence * strength_multiplier
        else:
            final_confidence = base_confidence
            confidence_calculation["indicator_avg_strength"] = 0

        # Limitar entre 0 y 1
        final_confidence = max(0, min(1, final_confidence))

        confidence_calculation["final_confidence"] = final_confidence

        return confidence_calculation

    def _get_indicator_strength(self, indicator_data: Dict[str, Any]) -> float:
        """Determinar fuerza de un indicador específico"""

        indicator_type = indicator_data.get("type", "").upper()

        if indicator_type == "RSI":
            rsi_value = indicator_data.get("value", 50)
            # RSI más extremos indica mayor fuerza
            strength = abs(rsi_value - 50) / 50
            return min(strength, 1.0)

        elif indicator_type == "MACD":
            histogram = abs(indicator_data.get("histogram", 0))
            # Histograma más grande indica mayor fuerza
            return min(histogram * 10, 1.0) if histogram else 0.5

        elif indicator_type == "SMA":
            trend = indicator_data.get("trend", "neutral")
            if trend == "bullish" or trend == "bearish":
                return 0.8
            return 0.5

        elif indicator_type == "VOLUME":
            status = indicator_data.get("status", "normal")
            if status == "high":
                return 1.0
            elif status == "low":
                return 0.3
            return 0.6

        elif indicator_type == "TREND":
            strength_val = indicator_data.get("strength", 0)
            return min(strength_val, 1.0)

        return 0.5  # Default neutral strength

    async def _create_signal(
        self,
        signal_config: SignalConfig,
        confidence: float,
        reasoning_parts: List[str],
        market_data: Dict[str, Any],
        indicators_data: Dict[str, Any],
    ) -> StrategySignal:
        """Crear señal de trading"""

        from ...domain.models.position import Money
        from decimal import Decimal

        # Obtener precio actual del mercado
        current_price = market_data.get(
            "current_price", market_data.get("price", 100.0)
        )
        price_money = Money.from_float(current_price)

        # Determinar fuerza de señal basada en confianza
        signal_strength = self._determine_signal_strength(confidence)

        # Crear reasoning completo
        reasoning = " | ".join(reasoning_parts)

        # Crear metadata adicional
        metadata = {
            "confidence_breakdown": {k: v for k, v in indicators_data.items()},
            "market_conditions": {
                "price": current_price,
                "volume": market_data.get("volume", 0),
                "timestamp": datetime.now().isoformat(),
            },
            "signal_config": signal_config.name,
        }

        signal = StrategySignal(
            strategy_id=f"signal_{signal_config.name}",
            signal_type=signal_config.signal_type,
            confidence=Decimal(str(confidence)),
            entry_price=price_money,
            reasoning=reasoning,
            metadata=metadata,
            signal_strength=signal_strength,
        )

        return signal

    def _determine_signal_strength(self, confidence: float) -> SignalStrength:
        """Determinar fuerza de señal basada en confianza"""

        if confidence >= 0.9:
            return SignalStrength.VERY_STRONG
        elif confidence >= 0.7:
            return SignalStrength.STRONG
        elif confidence >= 0.5:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK

    async def validate_signal_config(self, signal_config: SignalConfig) -> List[str]:
        """Validar configuración de señal"""

        errors = []

        if not signal_config.name:
            errors.append("Signal name is required")

        if not signal_config.conditions:
            errors.append("At least one condition is required")

        if signal_config.logic_type not in ["AND", "OR"]:
            errors.append("Logic type must be 'AND' or 'OR'")

        if not (0 <= signal_config.min_confidence <= 1):
            errors.append("Min confidence must be between 0 and 1")

        # Validar condiciones individuales
        for condition in signal_config.conditions:
            if not condition.indicator:
                errors.append("All conditions must specify an indicator")

            if not condition.operator:
                errors.append("All conditions must specify an operator")

        return errors

    def get_evaluation_cache_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del cache de evaluación"""

        return {
            "cache_size": len(self.evaluation_cache),
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "cache_keys": list(self.evaluation_cache.keys()),
        }

    def clear_evaluation_cache(self):
        """Limpiar cache de evaluación"""

        self.evaluation_cache.clear()


class AdvancedSignalEvaluatorService(SignalEvaluatorService):
    """Servicio avanzado con características adicionales"""

    def __init__(self):
        super().__init__()
        self.evaluation_history: List[Dict[str, Any]] = []
        self.success_rate_tracking = {}

    async def evaluate_signals_with_history(
        self,
        signal_configs: List[SignalConfig],
        indicators_data: Dict[str, Any],
        market_data: Dict[str, Any],
    ) -> SignalGenerationResult:
        """Evaluar señales guardando historial"""

        result = await super().evaluate_signals(
            signal_configs, indicators_data, market_data
        )

        # Guardar en historial
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "signal_configs": [cfg.name for cfg in signal_configs],
            "had_signal": result.signal is not None,
            "confidence": float(result.signal.confidence) if result.signal else 0,
            "processing_time_ms": result.processing_time_ms,
            "conditions_count": len(result.conditions_evaluated),
        }

        self.evaluation_history.append(history_entry)

        # Mantener solo últimas 1000 evaluaciones
        if len(self.evaluation_history) > 1000:
            self.evaluation_history = self.evaluation_history[-1000:]

        return result

    def get_success_rate(self, signal_name: str = None) -> Dict[str, float]:
        """Obtener tasa de éxito de señales"""

        if not self.evaluation_history:
            return {"overall": 0.0}

        relevant_history = self.evaluation_history

        if signal_name:
            # Filtrar por nombre de señal específica (simplificado)
            relevant_history = [
                entry
                for entry in self.evaluation_history
                if signal_name in entry.get("signal_configs", [])
            ]

        if not relevant_history:
            return {"overall": 0.0}

        total_evaluations = len(relevant_history)
        successful_signals = sum(1 for entry in relevant_history if entry["had_signal"])

        success_rate = (
            successful_signals / total_evaluations if total_evaluations > 0 else 0
        )

        return {
            "success_rate": success_rate,
            "total_evaluations": total_evaluations,
            "successful_signals": successful_signals,
        }
