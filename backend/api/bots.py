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
