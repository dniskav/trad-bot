#!/usr/bin/env python3
"""
Position service - business logic for position management
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# These will be injected by the main server
real_trading_manager = None
trading_tracker = None
bot_registry = None


def set_dependencies(rtm, tt, br):
    """Set dependencies from main server"""
    global real_trading_manager, trading_tracker, bot_registry
    real_trading_manager = rtm
    trading_tracker = tt
    bot_registry = br


def get_position_info_for_frontend(current_price=None):
    """
    Obtiene información de posiciones del RealTradingManager y bots plug-and-play, formateada para el frontend
    """
    logger.info("🔍 DEBUG: get_position_info_for_frontend called")
    try:
        # Obtener posiciones del RealTradingManager
        real_positions = real_trading_manager.active_positions

        # Obtener datos del TradingTracker para historial y estadísticas
        tracker_data = trading_tracker.get_all_positions()

        # Formatear posiciones para el frontend - formato compatible con ActivePositions
        formatted_positions = {}

        # Procesar bots legacy (conservative, aggressive) - posiciones reales de Binance
        for bot_type in ["conservative", "aggressive"]:
            bot_positions = real_positions.get(bot_type, {})

            if not bot_positions:
                # No hay posiciones activas reales
                formatted_positions[bot_type] = {}
            else:
                # Formatear cada posición individualmente
                formatted_bot_positions = {}
                for position_id, position in bot_positions.items():
                    entry_price = position["entry_price"]
                    quantity = position["quantity"]

                    # Calcular PnL si tenemos precio actual
                    pnl = 0.0
                    pnl_pct = 0.0
                    if current_price and entry_price > 0:
                        if position["side"] == "BUY":
                            pnl = (current_price - entry_price) * quantity
                            pnl_pct = (
                                (current_price - entry_price) / entry_price
                            ) * 100
                        else:  # SELL
                            pnl = (entry_price - current_price) * quantity
                            pnl_pct = (
                                (entry_price - current_price) / entry_price
                            ) * 100

                    formatted_bot_positions[position_id] = {
                        "id": position_id,
                        "bot_type": bot_type,
                        "type": position["side"],
                        "entry_price": entry_price,
                        "quantity": quantity,
                        "entry_time": position["entry_time"],
                        "current_price": current_price or entry_price,
                        "pnl": pnl,
                        "pnl_pct": pnl_pct,
                        "pnl_net": pnl,
                        "pnl_net_pct": pnl_pct,
                        "timestamp": position["entry_time"],
                        "is_synthetic": False,  # Flag para posiciones reales
                        "is_plugin_bot": False,  # Flag para bots legacy
                        "bot_on": real_trading_manager.is_bot_active(bot_type),
                    }

                formatted_positions[bot_type] = formatted_bot_positions

        # Procesar bots plug-and-play (posiciones sintéticas) - SIEMPRE incluir posiciones sintéticas
        all_bots = bot_registry.get_all_bots()
        logger.info(f"🔍 DEBUG: Procesando bots: {list(all_bots.keys())}")
        for bot_name, bot in all_bots.items():
            # Saltar bots legacy
            if bot_name in ["conservative", "aggressive"]:
                continue

            # Mostrar posiciones sintéticas aunque el bot esté apagado
            if bot.config.synthetic_mode:
                logger.info(
                    f"🔍 DEBUG: Procesando bot {bot_name} (synthetic_mode: {bot.config.synthetic_mode})"
                )
                formatted_bot_positions = {}

                # Primero intentar obtener posiciones del bot activo
                if bot.synthetic_positions:
                    for position in bot.synthetic_positions:
                        if position["status"] == "open":
                            entry_price = position["entry_price"]
                            quantity = position["quantity"]
                            position_id = position["id"]

                            # Calcular PnL si tenemos precio actual
                            pnl = 0.0
                            pnl_pct = 0.0
                            if current_price and entry_price > 0:
                                if position["signal_type"] == "BUY":
                                    pnl = (current_price - entry_price) * quantity
                                    pnl_pct = (
                                        (current_price - entry_price) / entry_price
                                    ) * 100
                                else:  # SELL
                                    pnl = (entry_price - current_price) * quantity
                                    pnl_pct = (
                                        (entry_price - current_price) / entry_price
                                    ) * 100

                            formatted_bot_positions[position_id] = {
                                "id": position_id,
                                "bot_type": bot_name,
                                "type": position["signal_type"],
                                "entry_price": entry_price,
                                "quantity": quantity,
                                "entry_time": position["timestamp"],
                                "current_price": current_price or entry_price,
                                "pnl": pnl,
                                "pnl_pct": pnl_pct,
                                "pnl_net": pnl,
                                "pnl_net_pct": pnl_pct,
                                "timestamp": position["timestamp"],
                                "is_synthetic": True,  # Flag para posiciones sintéticas
                                "is_plugin_bot": True,  # Flag para bots plug-and-play
                                "bot_on": bot.is_active,
                                "stop_loss": position.get("stop_loss"),
                                "take_profit": position.get("take_profit"),
                            }

                # SIEMPRE buscar en el historial para posiciones sintéticas abiertas
                if tracker_data.get("history"):
                    logger.info(
                        f"🔍 DEBUG: Buscando en historial para {bot_name}, historial length: {len(tracker_data['history'])}"
                    )
                    for order_record in tracker_data["history"]:
                        if (
                            order_record.get("bot_type") == bot_name
                            and order_record.get("status") == "OPEN"
                            and order_record.get("is_synthetic", False)
                        ):

                            entry_price = order_record.get("entry_price", 0)
                            quantity = order_record.get("quantity", 0)
                            position_id = order_record.get("id", "")

                            logger.info(
                                f"🔍 DEBUG: Encontrada posición abierta para {bot_name}: {position_id}"
                            )

                            # Calcular PnL si tenemos precio actual
                            pnl = 0.0
                            pnl_pct = 0.0
                            if current_price and entry_price > 0:
                                if order_record.get("type") == "BUY":
                                    pnl = (current_price - entry_price) * quantity
                                    pnl_pct = (
                                        (current_price - entry_price) / entry_price
                                    ) * 100
                                else:  # SELL
                                    pnl = (entry_price - current_price) * quantity
                                    pnl_pct = (
                                        (entry_price - current_price) / entry_price
                                    ) * 100

                            if position_id:  # Solo agregar si tiene ID válido
                                formatted_bot_positions[position_id] = {
                                    "id": position_id,
                                    "bot_type": bot_name,
                                    "type": order_record.get("type", ""),
                                    "entry_price": entry_price,
                                    "quantity": quantity,
                                    "entry_time": order_record.get("entry_time", ""),
                                    "current_price": current_price or entry_price,
                                    "pnl": pnl,
                                    "pnl_pct": pnl_pct,
                                    "pnl_net": pnl,
                                    "pnl_net_pct": pnl_pct,
                                    "timestamp": order_record.get("entry_time", ""),
                                    "is_synthetic": True,  # Flag para posiciones sintéticas
                                    "is_plugin_bot": True,  # Flag para bots plug-and-play
                                    "bot_on": bot.is_active,
                                    "stop_loss": order_record.get("stop_loss"),
                                    "take_profit": order_record.get("take_profit"),
                                }

                # SIEMPRE incluir las posiciones sintéticas encontradas
                if formatted_bot_positions:
                    formatted_positions[bot_name] = formatted_bot_positions
                    logger.info(
                        f"🔍 DEBUG: Agregadas {len(formatted_bot_positions)} posiciones para {bot_name}"
                    )
                else:
                    logger.info(
                        f"🔍 DEBUG: No se encontraron posiciones para {bot_name}"
                    )

        # Fallback adicional: si no hay posiciones formateadas aún, leer snapshot desde tracker/persistencia
        try:
            snapshot_active = {}
            if hasattr(trading_tracker, "active_positions"):
                snapshot_active = trading_tracker.active_positions or {}
            # Merge con snapshot de persistencia si existe
            if hasattr(trading_tracker, "persistence") and trading_tracker.persistence:
                snap_fs = trading_tracker.persistence.get_active_positions() or {}
                # Unir ambos (memoria tiene prioridad)
                for bname, positions in (snap_fs or {}).items():
                    if bname not in snapshot_active:
                        snapshot_active[bname] = positions
                    else:
                        for pid, pos in (positions or {}).items():
                            snapshot_active[bname].setdefault(pid, pos)

            # Formatear snapshot bruto al formato esperado por el frontend
            for bot_name, positions in (snapshot_active or {}).items():
                if not isinstance(positions, dict):
                    continue
                formatted_bot_positions = formatted_positions.get(bot_name, {})
                for pid, pos in positions.items():
                    entry_price = float(pos.get("entry_price") or pos.get("entry") or 0)
                    quantity = float(pos.get("quantity") or pos.get("qty") or 0)
                    side = str(
                        pos.get("type") or pos.get("signal_type") or "BUY"
                    ).upper()
                    cp = float(pos.get("current_price") or entry_price)
                    pnl = 0.0
                    pnl_pct = 0.0
                    if current_price and entry_price > 0:
                        if side == "BUY":
                            pnl = (current_price - entry_price) * quantity
                            pnl_pct = (
                                (current_price - entry_price) / entry_price
                            ) * 100
                        else:
                            pnl = (entry_price - current_price) * quantity
                            pnl_pct = (
                                (entry_price - current_price) / entry_price
                            ) * 100
                    formatted_bot_positions[str(pid)] = {
                        "id": str(pid),
                        "bot_type": bot_name,
                        "type": side,
                        "entry_price": entry_price,
                        "quantity": quantity,
                        "entry_time": pos.get("entry_time")
                        or pos.get("timestamp")
                        or "",
                        "current_price": current_price or cp,
                        "pnl": pnl,
                        "pnl_pct": pnl_pct,
                        "pnl_net": pnl,
                        "pnl_net_pct": pnl_pct,
                        "timestamp": pos.get("entry_time")
                        or pos.get("timestamp")
                        or "",
                        "is_synthetic": bool(pos.get("is_synthetic")),
                        "is_plugin_bot": bool(pos.get("is_plugin_bot")),
                        "bot_on": bool(pos.get("bot_on")),
                        "status": pos.get("status"),
                    }
                if formatted_bot_positions:
                    formatted_positions[bot_name] = formatted_bot_positions
        except Exception as _e:
            pass

        # Convertir historial de órdenes al formato esperado por el frontend
        formatted_history = []
        if tracker_data.get("history"):
            for order_record in tracker_data["history"]:
                formatted_history.append(format_order_for_frontend(order_record))

        # Construir bot_status completo incluyendo bots plug-and-play
        complete_bot_status = trading_tracker.bot_status.copy()

        # Agregar estado de bots plug-and-play
        all_bots = bot_registry.get_all_bots()
        for bot_name, bot in all_bots.items():
            # Saltar bots legacy
            if bot_name in ["conservative", "aggressive"]:
                continue

            # Serializar last_signal si es un objeto complejo
            last_signal_val = getattr(bot, "last_signal", None)
            try:
                if last_signal_val is not None and not isinstance(
                    last_signal_val, (dict, str, int, float, bool)
                ):
                    # Extraer atributos comunes de TradingSignal o similares
                    last_signal_val = {
                        "signal_type": str(getattr(last_signal_val, "signal_type", "")),
                        "confidence": float(
                            getattr(last_signal_val, "confidence", 0.0)
                        ),
                        "entry_price": float(
                            getattr(last_signal_val, "entry_price", 0.0)
                        ),
                        "stop_loss": getattr(last_signal_val, "stop_loss", None),
                        "take_profit": getattr(last_signal_val, "take_profit", None),
                        "reasoning": getattr(last_signal_val, "reasoning", ""),
                        "metadata": getattr(last_signal_val, "metadata", {}),
                    }
            except Exception:
                last_signal_val = None

            complete_bot_status[bot_name] = {
                "is_active": getattr(bot, "is_active", False),
                "synthetic_mode": (
                    getattr(bot.config, "synthetic_mode", False)
                    if hasattr(bot, "config")
                    else False
                ),
                "last_signal": last_signal_val,
                "uptime": getattr(bot, "uptime", 0),
                "start_time": getattr(bot, "start_time", None),
                "positions_count": len(getattr(bot, "synthetic_positions", [])),
                "synthetic_balance": getattr(bot, "synthetic_balance", None),
            }

        # Construir balances separados: real (Binance) y sintético (tracker)
        account_balance_synthetic = tracker_data.get("account_balance", {}) or {}
        # Asegurar campos completos para synthetic
        if account_balance_synthetic is not None:
            doge_price = account_balance_synthetic.get("doge_price")
            if not doge_price:
                try:
                    doge_price = real_trading_manager.get_current_price("DOGEUSDT")
                except Exception:
                    doge_price = 0.0
            usdt_bal = float(account_balance_synthetic.get("usdt_balance", 0.0))
            doge_bal = float(account_balance_synthetic.get("doge_balance", 0.0))
            total_usdt = usdt_bal + (doge_bal * float(doge_price or 0.0))
            account_balance_synthetic.setdefault("usdt_balance", usdt_bal)
            account_balance_synthetic.setdefault("doge_balance", doge_bal)
            account_balance_synthetic.setdefault("doge_price", doge_price or 0.0)
            account_balance_synthetic.setdefault("total_balance_usdt", total_usdt)

        account_balance_real = {}
        try:
            # Obtener balances en vivo del gestor real
            rb = real_trading_manager.get_account_balance() or {}
            usdt_real = float(rb.get("USDT", 0.0))
            doge_real = float(rb.get("DOGE", 0.0))
            # Precio actual de DOGE para conversión
            try:
                doge_price = real_trading_manager.get_current_price("DOGEUSDT")
            except Exception:
                doge_price = 0.0
            if not doge_price:
                # Fallback a indicadores si no hay precio directo
                try:
                    from services.technical_indicators import (
                        calculate_technical_indicators,
                    )

                    data = calculate_technical_indicators("DOGEUSDT", "1m", 2)
                    candles = data.get("candles") or []
                    if candles:
                        doge_price = candles[-1].get("close") or 0.0
                except Exception:
                    doge_price = 0.0
            total_real_usdt = usdt_real + (doge_real * doge_price)
            account_balance_real = {
                "initial_balance": 0.0,  # no trackeado históricamente para real
                "current_balance": total_real_usdt,
                "total_pnl": 0.0,  # desconocido para real (no trackeado)
                "balance_change_pct": 0.0,
                "is_profitable": False,
                "usdt_balance": usdt_real,
                "doge_balance": doge_real,
                "total_balance_usdt": total_real_usdt,
                "doge_price": doge_price,
            }
        except Exception:
            account_balance_real = {}

        return {
            "active_positions": formatted_positions,
            "history": formatted_history,
            "statistics": tracker_data.get("statistics", {}),
            "account_balance": account_balance_synthetic,
            "account_balance_real": account_balance_real,
            "account_balance_synthetic": account_balance_synthetic,
            "bot_status": complete_bot_status,
            "margin_info": (
                real_trading_manager.get_margin_level()
                if real_trading_manager.leverage > 1
                else None
            ),
            "accounts_snapshot": {
                "real": trading_tracker.persistence.get_account_real(),
                "synthetic": trading_tracker.persistence.get_account_synth(),
            },
        }
    except Exception as e:
        logger.error(f"Error in get_position_info_for_frontend: {e}")
        # Return empty data structure to prevent WebSocket crashes
        return {
            "active_positions": {},
            "history": [],
            "statistics": {},
            "account_balance": {},
            "bot_status": {},
            "margin_info": None,
        }


def format_order_for_frontend(order_record):
    """Formatea un registro de orden para el frontend"""
    status = order_record.get("status", "UNKNOWN")

    return {
        "id": order_record.get("order_id", ""),
        "bot_type": order_record.get("bot_type", ""),
        "type": order_record.get("side", ""),
        "entry_price": order_record.get("entry_price", 0),
        "quantity": order_record.get("quantity", 0),
        "entry_time": order_record.get("entry_time", ""),
        "current_price": order_record.get("current_price", 0),
        "pnl": order_record.get("pnl", 0),
        "pnl_pct": order_record.get("pnl_percentage", 0),
        "pnl_net": order_record.get("net_pnl", 0),
        "pnl_net_pct": order_record.get(
            "pnl_percentage", 0
        ),  # Usar el mismo valor por ahora
        "timestamp": order_record.get("entry_time", ""),
        "close_price": order_record.get("close_price"),
        "close_time": order_record.get("close_time"),
        "duration_minutes": order_record.get("duration_minutes", 0),
        "fees_paid": order_record.get("fees_paid", 0),
        "status": status,
        "is_closed": status
        not in ["OPEN", "UPDATED"],  # Campo para identificar si está cerrada
        "duration_minutes": order_record.get("duration_minutes", 0),
        "is_synthetic": order_record.get(
            "is_synthetic", False
        ),  # Flag para posiciones sintéticas
        "is_plugin_bot": order_record.get(
            "is_plugin_bot", False
        ),  # Flag para bots plug-and-play
    }
