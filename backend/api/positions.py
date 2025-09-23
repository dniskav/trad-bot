#!/usr/bin/env python3
"""
Position management endpoints
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

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

@router.get("/position")
async def get_position():
    """Get current trading position"""
    return {
        "position": "None",
        "quantity": 0,
        "entry_price": None,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/position-info")
async def get_position_info():
    """Obtiene información completa de posiciones (reales y sintéticas)"""
    try:
        # Obtener precio actual
        current_price = None
        try:
            current_price = real_trading_manager.get_current_price('DOGEUSDT')
        except:
            pass
        
        # Obtener información de posiciones
        from services.position_service import get_position_info_for_frontend
        position_info = get_position_info_for_frontend(current_price)
        
        return position_info
    except Exception as e:
        logger.error(f"Error getting position info: {e}")
        return {"status": "error", "message": str(e)}

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
        logger.info(f"🛑 close_position request: bot_type={bot_type}, position_id={position_id}")
        if not bot_type or not position_id:
            return JSONResponse(status_code=400, content={
                "status": "error",
                "message": "Faltan parámetros: bot_type y position_id"
            })

        # Si es posición sintética, cerrarla desde el bot plug-and-play
        if position_id.startswith('SYNTH_'):
            try:
                # Cerrar posición sintética usando trading_tracker (fuente de verdad en PnP)
                if not trading_tracker:
                    return JSONResponse(status_code=500, content={"status": "error", "message": "Tracker no inicializado"})

                bot_positions = trading_tracker.active_positions.get(bot_type, {})
                try:
                    logger.info(f"🔎 Buscando en tracker: bot={bot_type} keys={list(bot_positions.keys())[:5]} total={len(bot_positions)}")
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
                        internal_id = str(pos.get('id') or '')
                        internal_position_id = str(pos.get('position_id') or '')
                        if position_id == internal_id or position_id == internal_position_id:
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
                    if bot and getattr(bot, 'synthetic_positions', None):
                        try:
                            ids_preview = [str(p.get('id') or p.get('position_id')) for p in bot.synthetic_positions[:5]]
                        except Exception:
                            ids_preview = []
                        logger.info(f"🔎 Buscando en bot_registry[{bot_type}].synthetic_positions total={len(bot.synthetic_positions)} preview={ids_preview}")
                        for pos in bot.synthetic_positions:
                            if str(pos.get('id')) == position_id or str(pos.get('position_id')) == position_id:
                                active = pos
                                position_key = pos.get('id') or pos.get('position_id') or position_id
                                logger.info("✅ Encontrada en bot synthetic_positions por id/position_id")
                                break
                # Búsqueda final: recorrer todos los bots plug-and-play por si el bot_type no coincide
                if not active:
                    try:
                        all_bots = bot_registry.get_all_bots()
                        logger.info(f"🔎 Escaneo global: total_bots={len(all_bots)}")
                        for name, bot in all_bots.items():
                            if name in ['conservative', 'aggressive']:
                                continue
                            if getattr(bot, 'synthetic_positions', None):
                                try:
                                    ids_preview = [str(p.get('id') or p.get('position_id')) for p in bot.synthetic_positions[:5]]
                                except Exception:
                                    ids_preview = []
                                logger.info(f"🔎 Escaneo global en bot={name} total={len(bot.synthetic_positions)} preview={ids_preview}")
                                # Log completo de todas las posiciones para debugging
                                try:
                                    all_ids = [str(p.get('id') or p.get('position_id')) for p in bot.synthetic_positions]
                                    logger.info(f"🔍 Lista completa de IDs en {name}: {all_ids}")
                                except Exception as e:
                                    logger.warning(f"⚠️ Error listando IDs en {name}: {e}")
                                for pos in bot.synthetic_positions:
                                    if str(pos.get('id')) == position_id or str(pos.get('position_id')) == position_id:
                                        active = pos
                                        if not bot_type:
                                            bot_type = name
                                        position_key = pos.get('id') or pos.get('position_id') or position_id
                                        logger.info(f"✅ Encontrada en escaneo global en bot={name}")
                                        break
                            if active:
                                break
                    except Exception:
                        pass
                if not active:
                    logger.warning(f"❌ Posición sintética no encontrada: bot_type={bot_type}, position_id={position_id}")
                    # Fallback extra: buscar en vista formateada de posiciones (lo que consume el frontend)
                    try:
                        from services.position_service import get_position_info_for_frontend
                        formatted = get_position_info_for_frontend()
                        candidates = formatted.get('active_positions', {}) if isinstance(formatted, dict) else {}
                        found_pos = None
                        found_bot = None
                        for bname, positions in candidates.items():
                            if position_id in positions:
                                found_pos = positions[position_id]
                                found_bot = bname
                                break
                            for k, pos in positions.items():
                                pid = str(pos.get('id') or pos.get('position_id') or k)
                                if pid == position_id:
                                    found_pos = pos
                                    found_bot = bname
                                    break
                            if found_pos:
                                break
                        if found_pos:
                            logger.info(f"♻️ Fallback encontró posición en formatted_positions bajo bot={found_bot}")
                            active = found_pos
                            position_key = position_id
                            if not bot_type:
                                bot_type = found_bot
                        else:
                            return JSONResponse(status_code=404, content={
                                "status": "error",
                                "message": "Posición no encontrada o ya cerrada"
                            })
                    except Exception as _e:
                        return JSONResponse(status_code=404, content={
                            "status": "error",
                            "message": "Posición no encontrada o ya cerrada"
                        })

                # Campos tolerantes a distintas claves
                order_id = active.get('order_id') or active.get('id') or active.get('position_id') or position_id
                entry_price = float(active.get('entry_price') or active.get('entry') or active.get('price') or 0)
                qty = float(active.get('quantity') or active.get('qty') or 0)
                side = active.get('side') or active.get('type') or 'BUY'

                # Precio de cierre actual
                try:
                    close_price = real_trading_manager.get_current_price(active.get('symbol', 'DOGEUSDT'))
                except Exception:
                    close_price = float(active.get('current_price', entry_price))

                # Comisiones: usar fee_rate del tracker si está disponible (solo salida)
                fee_rate = getattr(trading_tracker, 'fee_rate', 0.001)
                estimated_exit_fee = close_price * qty * float(fee_rate)

                # Calcular PnL bruto/neto
                pnl_gross = (close_price - entry_price) * qty if side == 'BUY' else (entry_price - close_price) * qty
                pnl_net = pnl_gross - estimated_exit_fee

                # Actualizar historial a través del tracker
                if hasattr(trading_tracker, 'close_order') and order_id:
                    trading_tracker.close_order(order_id=order_id, close_price=close_price, fees_paid=estimated_exit_fee)

                # Remover de activas en tracker si existe
                if hasattr(trading_tracker, 'remove_active_position') and position_key:
                    try:
                        trading_tracker.remove_active_position(bot_type, position_key)
                    except Exception:
                        pass
                # Remover de la lista del bot si existe allí
                try:
                    bot = bot_registry.get_bot(bot_type)
                    if bot and getattr(bot, 'synthetic_positions', None):
                        bot.synthetic_positions = [p for p in bot.synthetic_positions if str(p.get('id')) != position_id and str(p.get('position_id')) != position_id]
                except Exception:
                    pass

                logger.info(f"🟢 Cierre sintético OK: bot={bot_type} id={position_id} exit={close_price} pnl_net={pnl_net}")
                return {"status": "success", "data": {"bot_type": bot_type, "position_id": position_id, "pnl": pnl_net, "exit_price": close_price}}
            except Exception as e:
                logger.error(f"💥 Error closing synthetic position {position_id}: {e}")
                return JSONResponse(status_code=500, content={
                    "status": "error",
                    "message": str(e)
                })

        # Caso posiciones reales: usar el manager
        result = None
        if hasattr(real_trading_manager, 'close_position_with_tracking'):
            result = real_trading_manager.close_position_with_tracking(bot_type, position_id, trading_tracker)
        else:
            result = real_trading_manager.close_position(position_id, bot_type)

        # Normalizar resultado (algunos métodos devuelven bool/None)
        if isinstance(result, dict):
            if result.get('success', False):
                return {
                    "status": "success",
                    "data": {
                        "bot_type": bot_type,
                        "position_id": position_id,
                        "pnl": result.get("pnl"),
                        "exit_price": result.get("exit_price")
                    }
                }
            else:
                return JSONResponse(status_code=400, content={
                    "status": "error",
                    "message": result.get('error', 'No se pudo cerrar la posición')
                })
        else:
            # bool/None: False indica no encontrada; True/None considerar éxito
            if result is False:
                return JSONResponse(status_code=404, content={
                    "status": "error",
                    "message": "Posición no encontrada o ya cerrada"
                })
            logger.info(f"🟢 Cierre real OK: bot={bot_type} id={position_id}")
            return {"status": "success", "data": {"bot_type": bot_type, "position_id": position_id}}
    except Exception as e:
        logger.error(f"💥 close_position error: {e}")
        return JSONResponse(status_code=500, content={
            "status": "error",
            "message": str(e)
        })

# Alias removido - el router ya se monta con prefijo /api
