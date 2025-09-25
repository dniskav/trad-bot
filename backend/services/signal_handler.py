#!/usr/bin/env python3
"""
Manejador automático de señales de bots
Responsabilidad: Convertir señales en acciones de trading y persistencia
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from .bot_interface import TradingSignal, SignalType
from .trading_tracker import TradingTracker
from .real_trading_manager import RealTradingManager
from .close_utils import close_synth_position
from utils.colored_logger import get_colored_logger

logger = get_colored_logger(__name__)


class SignalHandler:
    """
    Manejador automático de señales de bots
    Convierte señales BUY/SELL/HOLD en acciones de trading y persistencia
    """

    def __init__(
        self, trading_tracker: TradingTracker, real_trading_manager: RealTradingManager
    ):
        self.trading_tracker = trading_tracker
        self.real_trading_manager = real_trading_manager
        self.logger = logger

    def handle_signal(self, signal: TradingSignal) -> Dict[str, Any]:
        """
        Maneja una señal de bot automáticamente

        Args:
            signal: Señal generada por el bot

        Returns:
            Dict con resultado de la acción
        """
        try:
            bot_name = signal.bot_name
            signal_type = signal.signal_type
            current_price = signal.entry_price
            confidence = signal.confidence

            self.logger.info(
                f"🤖 Procesando señal de {bot_name}: {signal_type.value} a ${current_price:.5f} (confianza: {confidence:.1%})"
            )

            # Determinar acción basada en la señal
            if signal_type == SignalType.BUY:
                return self._handle_buy_signal(signal)
            elif signal_type == SignalType.SELL:
                return self._handle_sell_signal(signal)
            elif signal_type == SignalType.HOLD:
                return self._handle_hold_signal(signal)
            else:
                return {
                    "status": "error",
                    "message": f"Señal no reconocida: {signal_type}",
                }

        except Exception as e:
            self.logger.error(f"❌ Error manejando señal: {e}")
            return {"status": "error", "message": str(e)}

    def _handle_buy_signal(self, signal: TradingSignal) -> Dict[str, Any]:
        """Maneja señal de compra"""
        bot_name = signal.bot_name
        current_price = signal.entry_price
        confidence = signal.confidence

        # Calcular cantidad basada en confianza y balance disponible
        quantity = self._calculate_position_size(
            bot_name, current_price, confidence, "BUY"
        )

        if quantity <= 0:
            return {
                "status": "skipped",
                "message": "No hay balance suficiente para abrir posición",
            }

        # Abrir posición usando el sistema existente
        try:
            # Usar el método existente del trading_tracker
            self.trading_tracker.update_position(
                bot_type=bot_name,
                signal="BUY",
                current_price=current_price,
                quantity=quantity,
            )

            self.logger.info(
                f"✅ Posición BUY abierta para {bot_name}: {quantity:.4f} DOGE a ${current_price:.5f}"
            )

            return {
                "status": "success",
                "action": "position_opened",
                "bot_name": bot_name,
                "signal_type": "BUY",
                "quantity": quantity,
                "entry_price": current_price,
                "confidence": confidence,
            }

        except Exception as e:
            self.logger.error(f"❌ Error abriendo posición BUY para {bot_name}: {e}")
            return {"status": "error", "message": str(e)}

    def _handle_sell_signal(self, signal: TradingSignal) -> Dict[str, Any]:
        """Maneja señal de venta"""
        bot_name = signal.bot_name
        current_price = signal.entry_price
        confidence = signal.confidence

        # Calcular cantidad basada en confianza y balance disponible
        quantity = self._calculate_position_size(
            bot_name, current_price, confidence, "SELL"
        )

        if quantity <= 0:
            return {
                "status": "skipped",
                "message": "No hay balance suficiente para abrir posición",
            }

        # Abrir posición usando el sistema existente
        try:
            # Usar el método existente del trading_tracker
            self.trading_tracker.update_position(
                bot_type=bot_name,
                signal="SELL",
                current_price=current_price,
                quantity=quantity,
            )

            self.logger.info(
                f"✅ Posición SELL abierta para {bot_name}: {quantity:.4f} DOGE a ${current_price:.5f}"
            )

            return {
                "status": "success",
                "action": "position_opened",
                "bot_name": bot_name,
                "signal_type": "SELL",
                "quantity": quantity,
                "entry_price": current_price,
                "confidence": confidence,
            }

        except Exception as e:
            self.logger.error(f"❌ Error abriendo posición SELL para {bot_name}: {e}")
            return {"status": "error", "message": str(e)}

    def _handle_hold_signal(self, signal: TradingSignal) -> Dict[str, Any]:
        """Maneja señal de mantener"""
        bot_name = signal.bot_name

        # Verificar si hay posiciones abiertas para cerrar
        active_positions = self.trading_tracker.active_positions.get(bot_name, {})

        if not active_positions:
            return {
                "status": "skipped",
                "message": "No hay posiciones abiertas para cerrar",
            }

        # Cerrar todas las posiciones abiertas
        closed_count = 0
        errors = []

        for position_id, position in active_positions.items():
            try:
                # Usar utilidades existentes para cerrar posición
                result = close_synth_position(
                    trading_tracker=self.trading_tracker,
                    real_trading_manager=self.real_trading_manager,
                    bot_registry=None,  # No necesario para cierre
                    bot_type=bot_name,
                    position_id=position_id,
                    current_price=signal.entry_price,
                    reason="HOLD Signal",
                )

                if result.get("status") == "success":
                    closed_count += 1
                    self.logger.info(
                        f"✅ Posición cerrada por señal HOLD: {position_id}"
                    )
                else:
                    errors.append(
                        f"{position_id}: {result.get('message', 'Error desconocido')}"
                    )

            except Exception as e:
                error_msg = f"Error cerrando {position_id}: {str(e)}"
                errors.append(error_msg)
                self.logger.error(f"❌ {error_msg}")

        if closed_count > 0:
            self.logger.info(
                f"✅ {closed_count} posiciones cerradas por señal HOLD de {bot_name}"
            )

        return {
            "status": "success",
            "action": "positions_closed",
            "bot_name": bot_name,
            "closed_count": closed_count,
            "errors": errors,
        }

    def _calculate_position_size(
        self, bot_name: str, current_price: float, confidence: float, signal_type: str
    ) -> float:
        """
        Calcula el tamaño de posición basado en confianza y balance disponible

        Args:
            bot_name: Nombre del bot
            current_price: Precio actual
            confidence: Confianza de la señal (0.0 - 1.0)
            signal_type: Tipo de señal (BUY/SELL)

        Returns:
            Cantidad a operar
        """
        try:
            # Obtener balance disponible
            account_synth = self.trading_tracker.persistence.get_account_synth() or {}

            if signal_type == "BUY":
                # Para BUY, usar USDT disponible
                usdt_available = float(account_synth.get("usdt_balance", 0.0))
                max_position_value = (
                    usdt_available * confidence
                )  # Usar confianza como multiplicador
                quantity = max_position_value / current_price
            else:  # SELL
                # Para SELL, usar DOGE disponible
                doge_available = float(account_synth.get("doge_balance", 0.0))
                quantity = (
                    doge_available * confidence
                )  # Usar confianza como multiplicador

            # Limitar a máximo $10 por posición (configuración actual)
            max_value = 10.0
            max_quantity = max_value / current_price

            return min(quantity, max_quantity)

        except Exception as e:
            self.logger.error(f"❌ Error calculando tamaño de posición: {e}")
            return 0.0
