#!/usr/bin/env python3
"""
Position management endpoints
"""

from fastapi import APIRouter, HTTPException, Query
import os
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# These will be injected by the main server
real_trading_manager = None
trading_tracker = None
bot_registry = None
ws_manager = None


def set_dependencies(rtm, tt, br, wsm=None):
    """Set dependencies from main server"""
    global real_trading_manager, trading_tracker, bot_registry, ws_manager
    real_trading_manager = rtm
    trading_tracker = tt
    bot_registry = br
    ws_manager = wsm


@router.get("/position")
async def get_position():
    """Get current trading position"""
    return {
        "position": "None",
        "quantity": 0,
        "entry_price": None,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/position-info")
async def get_position_info():
    """Obtiene información completa de posiciones (reales y sintéticas)"""
    try:
        # Obtener precio actual con fallback
        current_price = None
        try:
            current_price = real_trading_manager.get_current_price("DOGEUSDT")
        except Exception:
            current_price = None
        if not current_price:
            try:
                # Fallback: último close de Binance vía servicio de indicadores
                from services.technical_indicators import calculate_technical_indicators

                data = calculate_technical_indicators("DOGEUSDT", "1m", 2)
                candles = data.get("candles") or []
                if candles:
                    current_price = candles[-1].get("close")
            except Exception:
                current_price = None

        # Obtener información de posiciones
        from services.position_service import get_position_info_for_frontend

        position_info = get_position_info_for_frontend(current_price)

        return position_info
    except Exception as e:
        logger.error(f"Error getting position info: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/trading/history")
async def get_trading_history(
    page: int = Query(1, ge=1), page_size: int = Query(1000, ge=1, le=10000)
):
    """Devuelve el historial completo de posiciones con paginación.

    Respuesta:
      {
        "status": "success",
        "data": { "items": [...], "total": N, "page": P, "page_size": S }
      }
    """
    try:
        if trading_tracker is None:
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Tracker no inicializado"},
            )

        # Obtener historial desde el tracker (ya usa persistence por debajo)
        try:
            history = getattr(trading_tracker, "position_history", None)
            if history is None:
                # Fallback explícito
                history = trading_tracker.persistence.get_history()
        except Exception:
            history = []

        # Filtrar solo posiciones cerradas
        try:
            history = [
                h
                for h in history
                if str(h.get("status") or "").upper() == "CLOSED"
                or bool(h.get("is_closed"))
                or (h.get("close_time") is not None)
            ]
        except Exception:
            pass

        total = len(history)
        start = (page - 1) * page_size
        end = start + page_size
        items = history[start:end]

        return {
            "status": "success",
            "data": {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
            },
        }
    except Exception as e:
        logger.error(f"Error getting trading history: {e}")
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


@router.post("/positions/close")
@router.post("/positions/close/")
async def close_position(payload: dict):
    """Cierra una posición activa por id para un bot dado.

    Body JSON:
      { "bot_type": "simplebot", "position_id": "<id>" }
    """
    try:
        bot_type = payload.get("bot_type")
        position_id = payload.get("position_id")
        logger.info(
            f"🛑 close_position request: bot_type={bot_type}, position_id={position_id}"
        )
        if not bot_type or not position_id:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "Faltan parámetros: bot_type y position_id",
                },
            )

        # Si es posición sintética, cerrarla desde el bot plug-and-play
        if position_id.startswith("SYNTH_"):
            try:
                # Cerrar posición sintética usando trading_tracker (fuente de verdad en PnP)
                if not trading_tracker:
                    return JSONResponse(
                        status_code=500,
                        content={
                            "status": "error",
                            "message": "Tracker no inicializado",
                        },
                    )

                bot_positions = trading_tracker.active_positions.get(bot_type, {})
                try:
                    logger.info(
                        f"🔎 Buscando en tracker: bot={bot_type} keys={list(bot_positions.keys())[:5]} total={len(bot_positions)}"
                    )
                except Exception:
                    pass

                # Permitir buscar por clave directa o por campos internos 'id'/'position_id'
                position_key = None
                active = None
                if position_id in bot_positions:
                    position_key = position_id
                    active = bot_positions[position_key]
                else:
                    for k, pos in bot_positions.items():
                        internal_id = str(pos.get("id") or "")
                        internal_position_id = str(pos.get("position_id") or "")
                        if (
                            position_id == internal_id
                            or position_id == internal_position_id
                        ):
                            position_key = k
                            active = pos
                            break

                if not active:
                    # Buscar en el bot plug-and-play directamente si no está en el tracker
                    try:
                        bot = bot_registry.get_bot(bot_type)
                        if not bot:
                            # Fallback por si el acceso directo falla
                            bot = bot_registry.get_all_bots().get(bot_type)
                    except Exception:
                        bot = None
                    if bot and getattr(bot, "synthetic_positions", None):
                        try:
                            ids_preview = [
                                str(p.get("id") or p.get("position_id"))
                                for p in bot.synthetic_positions[:5]
                            ]
                        except Exception:
                            ids_preview = []
                        logger.info(
                            f"🔎 Buscando en bot_registry[{bot_type}].synthetic_positions total={len(bot.synthetic_positions)} preview={ids_preview}"
                        )
                        for pos in bot.synthetic_positions:
                            if (
                                str(pos.get("id")) == position_id
                                or str(pos.get("position_id")) == position_id
                            ):
                                active = pos
                                position_key = (
                                    pos.get("id")
                                    or pos.get("position_id")
                                    or position_id
                                )
                                logger.info(
                                    "✅ Encontrada en bot synthetic_positions por id/position_id"
                                )
                                break
                # Búsqueda final: recorrer todos los bots plug-and-play por si el bot_type no coincide
                if not active:
                    try:
                        all_bots = bot_registry.get_all_bots()
                        logger.info(f"🔎 Escaneo global: total_bots={len(all_bots)}")
                        for name, bot in all_bots.items():
                            if name in ["conservative", "aggressive"]:
                                continue
                            if getattr(bot, "synthetic_positions", None):
                                try:
                                    ids_preview = [
                                        str(p.get("id") or p.get("position_id"))
                                        for p in bot.synthetic_positions[:5]
                                    ]
                                except Exception:
                                    ids_preview = []
                                logger.info(
                                    f"🔎 Escaneo global en bot={name} total={len(bot.synthetic_positions)} preview={ids_preview}"
                                )
                                # Log completo de todas las posiciones para debugging
                                try:
                                    all_ids = [
                                        str(p.get("id") or p.get("position_id"))
                                        for p in bot.synthetic_positions
                                    ]
                                    logger.info(
                                        f"🔍 Lista completa de IDs en {name}: {all_ids}"
                                    )
                                except Exception as e:
                                    logger.warning(
                                        f"⚠️ Error listando IDs en {name}: {e}"
                                    )
                                for pos in bot.synthetic_positions:
                                    if (
                                        str(pos.get("id")) == position_id
                                        or str(pos.get("position_id")) == position_id
                                    ):
                                        active = pos
                                        if not bot_type:
                                            bot_type = name
                                        position_key = (
                                            pos.get("id")
                                            or pos.get("position_id")
                                            or position_id
                                        )
                                        logger.info(
                                            f"✅ Encontrada en escaneo global en bot={name}"
                                        )
                                        break
                            if active:
                                break
                    except Exception:
                        pass
                if not active:
                    logger.warning(
                        f"❌ Posición sintética no encontrada: bot_type={bot_type}, position_id={position_id}"
                    )
                    # Fallback extra: buscar en vista formateada de posiciones (lo que consume el frontend)
                    try:
                        from services.position_service import (
                            get_position_info_for_frontend,
                        )

                        formatted = get_position_info_for_frontend()
                        candidates = (
                            formatted.get("active_positions", {})
                            if isinstance(formatted, dict)
                            else {}
                        )
                        found_pos = None
                        found_bot = None
                        for bname, positions in candidates.items():
                            if position_id in positions:
                                found_pos = positions[position_id]
                                found_bot = bname
                                break
                            for k, pos in positions.items():
                                pid = str(pos.get("id") or pos.get("position_id") or k)
                                if pid == position_id:
                                    found_pos = pos
                                    found_bot = bname
                                    break
                            if found_pos:
                                break
                        if found_pos:
                            logger.info(
                                f"♻️ Fallback encontró posición en formatted_positions bajo bot={found_bot}"
                            )
                            active = found_pos
                            position_key = position_id
                            if not bot_type:
                                bot_type = found_bot
                        else:
                            return JSONResponse(
                                status_code=404,
                                content={
                                    "status": "error",
                                    "message": "Posición no encontrada o ya cerrada",
                                },
                            )
                    except Exception as _e:
                        return JSONResponse(
                            status_code=404,
                            content={
                                "status": "error",
                                "message": "Posición no encontrada o ya cerrada",
                            },
                        )

                # Campos tolerantes a distintas claves
                order_id = (
                    active.get("order_id")
                    or active.get("id")
                    or active.get("position_id")
                    or position_id
                )
                entry_price = float(
                    active.get("entry_price")
                    or active.get("entry")
                    or active.get("price")
                    or 0
                )
                qty = float(active.get("quantity") or active.get("qty") or 0)
                side = active.get("side") or active.get("type") or "BUY"

                # Precio de cierre actual
                try:
                    close_price = real_trading_manager.get_current_price(
                        active.get("symbol", "DOGEUSDT")
                    )
                except Exception:
                    close_price = float(active.get("current_price", entry_price))

                # Comisiones: usar fee_rate del tracker si está disponible (solo salida)
                fee_rate = getattr(trading_tracker, "fee_rate", 0.001)
                estimated_exit_fee = close_price * qty * float(fee_rate)

                # Calcular PnL bruto/neto
                pnl_gross = (
                    (close_price - entry_price) * qty
                    if side == "BUY"
                    else (entry_price - close_price) * qty
                )
                pnl_net = pnl_gross - estimated_exit_fee

                # Actualizar historial a través del tracker
                if hasattr(trading_tracker, "close_order") and order_id:
                    trading_tracker.close_order(
                        order_id=order_id,
                        close_price=close_price,
                        fees_paid=estimated_exit_fee,
                    )

                # Remover de activas en tracker si existe
                if hasattr(trading_tracker, "remove_active_position") and position_key:
                    try:
                        trading_tracker.remove_active_position(bot_type, position_key)
                    except Exception:
                        pass
                # Remover de la lista del bot si existe allí
                try:
                    bot = bot_registry.get_bot(bot_type)
                    if bot and getattr(bot, "synthetic_positions", None):
                        bot.synthetic_positions = [
                            p
                            for p in bot.synthetic_positions
                            if str(p.get("id")) != position_id
                            and str(p.get("position_id")) != position_id
                        ]
                except Exception:
                    pass

                logger.info(
                    f"🟢 Cierre sintético OK: bot={bot_type} id={position_id} exit={close_price} pnl_net={pnl_net}"
                )
                # Notificar a clientes para refrescar historial
                try:
                    if ws_manager:
                        import json as _json

                        await ws_manager.broadcast(
                            _json.dumps(
                                {
                                    "type": "history_refresh",
                                    "timestamp": datetime.now().isoformat(),
                                }
                            )
                        )
                except Exception:
                    pass
                return {
                    "status": "success",
                    "data": {
                        "bot_type": bot_type,
                        "position_id": position_id,
                        "pnl": pnl_net,
                        "exit_price": close_price,
                    },
                }
            except Exception as e:
                logger.error(f"💥 Error closing synthetic position {position_id}: {e}")
                return JSONResponse(
                    status_code=500, content={"status": "error", "message": str(e)}
                )

        # Caso posiciones reales: usar el manager
        result = None
        if hasattr(real_trading_manager, "close_position_with_tracking"):
            result = real_trading_manager.close_position_with_tracking(
                bot_type, position_id, trading_tracker
            )
        else:
            result = real_trading_manager.close_position(position_id, bot_type)

        # Normalizar resultado (algunos métodos devuelven bool/None)
        if isinstance(result, dict):
            if result.get("success", False):
                return {
                    "status": "success",
                    "data": {
                        "bot_type": bot_type,
                        "position_id": position_id,
                        "pnl": result.get("pnl"),
                        "exit_price": result.get("exit_price"),
                    },
                }
            else:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": result.get("error", "No se pudo cerrar la posición"),
                    },
                )
        else:
            # bool/None: False indica no encontrada; True/None considerar éxito
            if result is False:
                return JSONResponse(
                    status_code=404,
                    content={
                        "status": "error",
                        "message": "Posición no encontrada o ya cerrada",
                    },
                )
            logger.info(f"🟢 Cierre real OK: bot={bot_type} id={position_id}")
            # Notificar a clientes para refrescar historial
            try:
                if ws_manager:
                    import json as _json

                    await ws_manager.broadcast(
                        _json.dumps(
                            {
                                "type": "history_refresh",
                                "timestamp": datetime.now().isoformat(),
                            }
                        )
                    )
            except Exception:
                pass
            return {
                "status": "success",
                "data": {"bot_type": bot_type, "position_id": position_id},
            }
    except Exception as e:
        logger.error(f"💥 close_position error: {e}")
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


# Alias removido - el router ya se monta con prefijo /api


@router.get("/positions/diag")
async def positions_diag(
    bot: str = Query(..., description="Nombre del bot"),
    position_id: str = Query(..., description="ID de la posición"),
):
    """Diagnóstico combinado de active_positions e historial para un bot/position_id.

    Uso: /api/positions/diag?bot=simplebot&position_id=synthetic_1
    """
    try:
        if trading_tracker is None:
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Tracker no inicializado"},
            )

        active_entry = None
        try:
            active_entry = (trading_tracker.active_positions.get(bot, {}) or {}).get(
                position_id
            )
        except Exception:
            active_entry = None

        # Snapshot en disco (para detectar desincronización memoria/archivo)
        active_entry_fs = None
        try:
            if hasattr(trading_tracker, "persistence") and trading_tracker.persistence:
                snapshot = trading_tracker.persistence.get_active_positions() or {}
                active_entry_fs = (snapshot.get(bot, {}) or {}).get(position_id)
        except Exception:
            active_entry_fs = None

        history_entry = None
        try:
            history = getattr(trading_tracker, "position_history", []) or []
            for rec in reversed(history):
                pid = str(
                    rec.get("position_id") or rec.get("id") or rec.get("order_id") or ""
                )
                if pid == position_id:
                    history_entry = rec
                    break
        except Exception:
            history_entry = None

        return {
            "status": "success",
            "data": {
                "bot": bot,
                "position_id": position_id,
                "active": active_entry,
                "active_snapshot": active_entry_fs,
                "history": history_entry,
            },
        }
    except Exception as e:
        logger.error(f"Error en positions_diag: {e}")
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


@router.post("/positions/reconcile")
async def reconcile_positions():
    """Ejecuta una pasada de reconciliación SL/TP sobre la capa de persistencia.

    - Lee active_positions e history desde persistencia
    - Evalúa SL/TP con el precio actual
    - Marca posiciones como cerradas en active_positions (persistencia)
    - Actualiza el historial con close_price/close_time/close_reason y status
    """
    try:
        if trading_tracker is None:
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Tracker no inicializado"},
            )

        # Precio actual con fallback
        current_price = None
        try:
            current_price = real_trading_manager.get_current_price("DOGEUSDT")
        except Exception:
            current_price = None
        if not current_price:
            try:
                from services.technical_indicators import calculate_technical_indicators

                data = calculate_technical_indicators("DOGEUSDT", "1m", 2)
                candles = data.get("candles") or []
                if candles:
                    current_price = candles[-1].get("close")
            except Exception:
                pass
        if not current_price:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "No se pudo obtener precio actual",
                },
            )

        # Leer snapshots
        snapshot_active = trading_tracker.persistence.get_active_positions() or {}
        snapshot_history = trading_tracker.persistence.get_history() or []

        # Configuración reconciliador
        RECON_VEN_LIM = int(os.getenv("RECON_VEN_LIM", "2000"))  # velas máx
        RECON_BUFFER = float(os.getenv("RECON_BUFFER", "0.0002"))  # 0.02%
        RECON_POLICY = os.getenv("RECON_POLICY", "wick").lower()  # 'wick' o 'close'

        closed_count = 0
        closed_map = {}  # position_id -> {reason, close_price}

        # Recorre todos los bots
        for bot_name, positions in list(snapshot_active.items()):
            if not isinstance(positions, dict):
                continue
            for position_id, pos in list(positions.items()):
                try:
                    stype = str(pos.get("signal_type") or pos.get("type") or "").upper()
                    sl = pos.get("stop_loss")
                    tp = pos.get("take_profit")
                    reason = None
                    close_price = None

                    # 1) Detección con precio actual (útil si no hay velas)
                    def check_current():
                        nonlocal reason, close_price
                        if stype == "BUY":
                            if sl and current_price <= sl * (1 + RECON_BUFFER):
                                reason = "Stop Loss"
                                close_price = sl
                            elif tp and current_price >= tp * (1 - RECON_BUFFER):
                                reason = "Take Profit"
                                close_price = tp
                        elif stype == "SELL":
                            if sl and current_price >= sl * (1 - RECON_BUFFER):
                                reason = "Stop Loss"
                                close_price = sl
                            elif tp and current_price <= tp * (1 + RECON_BUFFER):
                                reason = "Take Profit"
                                close_price = tp

                    check_current()

                    # 2) Detección histórica si no se decidió con el precio actual
                    if reason is None:
                        try:
                            from services.technical_indicators import (
                                get_klines_from_binance,
                            )

                            kl = get_klines_from_binance(
                                "DOGEUSDT", "1m", RECON_VEN_LIM
                            )
                            if kl:
                                # klines de Binance formato por función -> ya transformada? Asumimos [ [openTime, open, high, low, close, volume, ...], .. ]
                                highs = []
                                lows = []
                                closes = []
                                for k in kl:
                                    # admitir dict o lista
                                    if isinstance(k, dict):
                                        highs.append(float(k.get("high")))
                                        lows.append(float(k.get("low")))
                                        closes.append(float(k.get("close")))
                                    else:
                                        highs.append(float(k[2]))
                                        lows.append(float(k[3]))
                                        closes.append(float(k[4]))

                                if RECON_POLICY == "close":
                                    hi = max(closes)
                                    lo = min(closes)
                                else:
                                    hi = max(highs)
                                    lo = min(lows)

                                if stype == "BUY":
                                    if sl and lo <= sl * (1 + RECON_BUFFER):
                                        reason = "Stop Loss"
                                        close_price = sl
                                    elif tp and hi >= tp * (1 - RECON_BUFFER):
                                        reason = "Take Profit"
                                        close_price = tp
                                elif stype == "SELL":
                                    if sl and hi >= sl * (1 - RECON_BUFFER):
                                        reason = "Stop Loss"
                                        close_price = sl
                                    elif tp and lo <= tp * (1 + RECON_BUFFER):
                                        reason = "Take Profit"
                                        close_price = tp
                        except Exception as _e:
                            pass

                    if reason and close_price is not None:
                        # Actualizar active_positions snapshot
                        updated = dict(pos)
                        updated.update(
                            {
                                "status": "closed",
                                "is_closed": True,
                                "close_reason": reason,
                                "close_price": float(close_price),
                                "close_time": datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                            }
                        )
                        snapshot_active[bot_name][position_id] = updated
                        closed_map[position_id] = {
                            "reason": reason,
                            "close_price": float(close_price),
                        }

                        # Actualizar historial (match por position_id)
                        for rec in reversed(snapshot_history):
                            pid = str(
                                rec.get("position_id")
                                or rec.get("id")
                                or rec.get("order_id")
                                or ""
                            )
                            if pid == position_id:
                                rec["close_price"] = float(close_price)
                                rec["close_time"] = datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                )
                                rec["close_reason"] = reason
                                rec["status"] = "CLOSED"
                                # Calcular pnl si falta
                                try:
                                    entry = float(
                                        rec.get("entry_price")
                                        or updated.get("entry_price")
                                        or 0
                                    )
                                    qty = float(
                                        rec.get("quantity")
                                        or updated.get("quantity")
                                        or 0
                                    )
                                    if stype == "BUY":
                                        pnl = (float(close_price) - entry) * qty
                                    else:
                                        pnl = (entry - float(close_price)) * qty
                                    rec["pnl"] = pnl
                                    rec["net_pnl"] = pnl
                                except Exception:
                                    pass
                                break
                        closed_count += 1
                except Exception as e:
                    logger.error(f"Error reconciliando {bot_name} {position_id}: {e}")

        # Segunda pasada: asegurar que cualquier posición marcada cerrada en active_positions quede cerrada en history
        if closed_map:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for idx, rec in enumerate(snapshot_history):
                pid = str(
                    rec.get("position_id") or rec.get("id") or rec.get("order_id") or ""
                )
                if pid in closed_map and (
                    not rec.get("close_time") or rec.get("status") != "CLOSED"
                ):
                    info = closed_map[pid]
                    rec["close_time"] = rec.get("close_time") or now_str
                    rec["close_price"] = rec.get("close_price") or info["close_price"]
                    rec["close_reason"] = rec.get("close_reason") or info["reason"]
                    rec["status"] = "CLOSED"
                    # completar pnl si falta
                    try:
                        entry = float(rec.get("entry_price") or 0)
                        qty = float(rec.get("quantity") or 0)
                        cp = float(rec.get("close_price") or 0)
                        side = str(rec.get("side") or "").upper()
                        if side == "BUY":
                            pnl = (cp - entry) * qty
                        else:
                            pnl = (entry - cp) * qty
                        if rec.get("pnl") is None:
                            rec["pnl"] = pnl
                        if rec.get("net_pnl") is None:
                            rec["net_pnl"] = pnl
                    except Exception:
                        pass

        # Persistir cambios
        trading_tracker.persistence.set_active_positions(snapshot_active)
        trading_tracker.persistence.set_history(snapshot_history)

        return {"status": "success", "data": {"closed": closed_count}}
    except Exception as e:
        logger.error(f"Error en reconcile_positions: {e}")
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )
