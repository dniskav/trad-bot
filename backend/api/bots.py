#!/usr/bin/env python3
"""
Bot management endpoints
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# These will be injected by the main server
real_trading_manager = None
trading_tracker = None

def set_dependencies(rtm, tt):
    """Set dependencies from main server"""
    global real_trading_manager, trading_tracker
    real_trading_manager = rtm
    trading_tracker = tt

@router.post("/bot/{bot_type}/activate")
async def activate_bot(bot_type: str):
    """Activa un bot específico"""
    try:
        if bot_type not in ['conservative', 'aggressive']:
            return {"status": "error", "message": "Tipo de bot inválido"}
        
        success = real_trading_manager.activate_bot(bot_type, trading_tracker)
        if success:
            return {"status": "success", "message": f"Bot {bot_type} activado"}
        else:
            return {"status": "error", "message": f"Error activando bot {bot_type}"}
    except Exception as e:
        logger.error(f"Error activating bot {bot_type}: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/bot/{bot_type}/deactivate")
async def deactivate_bot(bot_type: str):
    """Desactiva un bot específico y cierra sus posiciones"""
    try:
        if bot_type not in ['conservative', 'aggressive']:
            return {"status": "error", "message": "Tipo de bot inválido"}
        
        success = real_trading_manager.deactivate_bot(bot_type, trading_tracker)
        if success:
            return {"status": "success", "message": f"Bot {bot_type} desactivado"}
        else:
            return {"status": "error", "message": f"Error desactivando bot {bot_type}"}
    except Exception as e:
        logger.error(f"Error deactivating bot {bot_type}: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/bots")
async def get_bots():
    """Obtiene información de todos los bots disponibles"""
    try:
        from services.bot_registry import bot_registry
        
        # Obtener bots del registry
        all_bots = bot_registry.get_all_bots()
        
        # Formatear información de bots para el frontend
        bots_info = []
        for bot_name, bot in all_bots.items():
            bot_info = {
                "name": bot_name,
                "display_name": get_bot_display_name(bot_name),
                "is_active": getattr(bot, 'is_active', False),
                "synthetic_mode": getattr(bot.config, 'synthetic_mode', False) if hasattr(bot, 'config') else False,
                "positions_open": len(getattr(bot, 'synthetic_positions', [])),
                "uptime": getattr(bot, 'uptime', 0),
                "start_time": getattr(bot, 'start_time', None),
                "last_signal": getattr(bot, 'last_signal', None)
            }
            bots_info.append(bot_info)
        
        return {
            "status": "success",
            "data": bots_info
        }
        
    except Exception as e:
        logger.error(f"Error getting bots info: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/bots/process-info")
async def get_process_info():
    """Obtiene información de procesos de bots"""
    try:
        from services.bot_registry import bot_registry
        
        # Obtener información de procesos
        all_bots = bot_registry.get_all_bots()
        process_info = []
        
        for bot_name, bot in all_bots.items():
            info = {
                "name": bot_name,
                "pid": getattr(bot, 'pid', None),
                "is_running": getattr(bot, 'is_active', False),
                "start_time": getattr(bot, 'start_time', None),
                "uptime": getattr(bot, 'uptime', 0),
                "memory_usage": getattr(bot, 'memory_usage', 0),
                "cpu_usage": getattr(bot, 'cpu_usage', 0)
            }
            process_info.append(info)
        
        return {
            "status": "success",
            "data": process_info
        }
        
    except Exception as e:
        logger.error(f"Error getting process info: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/{bot_name}/start")
async def start_plugin_bot(bot_name: str, synthetic_mode: bool = True):
    """Inicia un bot plug-and-play"""
    try:
        from services.bot_registry import get_bot_registry
        registry = get_bot_registry()
        
        # Configurar modo sintético antes de iniciar
        bot = registry.get_bot(bot_name)
        if bot:
            bot.config.synthetic_mode = synthetic_mode
            logger.info(f"🤖 Configurando {bot_name} en modo {'sintético' if synthetic_mode else 'real'}")
        
        success = registry.start_bot(bot_name)
        if success:
            mode_text = "sintético" if synthetic_mode else "real"
            logger.info(f"✅ Bot {bot_name} iniciado correctamente en modo {mode_text}")
            return {"status": "success", "message": f"Bot {bot_name} iniciado correctamente en modo {mode_text}"}
        else:
            logger.error(f"❌ Error iniciando bot {bot_name}")
            return {"status": "error", "message": f"Error iniciando bot {bot_name}"}
    except Exception as e:
        logger.error(f"❌ Error starting bot {bot_name}: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/{bot_name}/stop")
async def stop_plugin_bot(bot_name: str):
    """Detiene un bot plug-and-play"""
    try:
        from services.bot_registry import get_bot_registry
        registry = get_bot_registry()
        
        success = registry.stop_bot(bot_name)
        if success:
            logger.info(f"🛑 Bot {bot_name} detenido correctamente")
            return {"status": "success", "message": f"Bot {bot_name} detenido correctamente"}
        else:
            logger.error(f"❌ Error deteniendo bot {bot_name}")
            return {"status": "error", "message": f"Error deteniendo bot {bot_name}"}
    except Exception as e:
        logger.error(f"❌ Error stopping bot {bot_name}: {e}")
        return {"status": "error", "message": str(e)}

def get_bot_display_name(bot_name: str) -> str:
    """Obtiene el nombre de visualización del bot"""
    display_names = {
        'conservative': 'Bot Conservador',
        'aggressive': 'Bot Agresivo',
        'simplebot': 'Simple Bot',
        'rsibot': 'RSI Bot',
        'macdbot': 'MACD Bot'
    }
    return display_names.get(bot_name, bot_name.title())
