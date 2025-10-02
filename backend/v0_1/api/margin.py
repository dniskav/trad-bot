from fastapi import APIRouter
from services.real_trading_manager import real_trading_manager
from utils.colored_logger import get_colored_logger

logger = get_colored_logger(__name__)
router = APIRouter()

@router.get("/margin-info")
async def get_margin_info():
    """Obtiene información detallada del margen de la cuenta"""
    try:
        if real_trading_manager.leverage <= 1:
            return {
                "status": "info",
                "message": "Margin trading no está habilitado (leverage <= 1)",
                "data": {
                    "leverage": real_trading_manager.leverage,
                    "margin_type": real_trading_manager.margin_type,
                    "margin_info": None
                }
            }
        
        margin_info = real_trading_manager.get_margin_level()
        
        if not margin_info.get('success', False):
            return {
                "status": "error",
                "message": margin_info.get('error', 'Error desconocido'),
                "data": None
            }
        
        return {
            "status": "success",
            "data": margin_info
        }
        
    except Exception as e:
        logger.error(f"Error getting margin info: {e}")
        return {
            "status": "error",
            "message": str(e),
            "data": None
        }
