#!/usr/bin/env python3
"""
Metrics endpoints
"""

from fastapi import APIRouter
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

@router.get("/metrics")
async def get_metrics():
    """Obtiene métricas del sistema"""
    try:
        # Obtener datos del tracker
        tracker_data = trading_tracker.get_all_positions()
        
        return {
            "status": "success",
            "data": {
                "total_trades": len(tracker_data.get('history', [])),
                "open_positions": len(tracker_data.get('active_positions', {})),
                "account_balance": tracker_data.get('account_balance', {}),
                "statistics": tracker_data.get('statistics', {}),
                "margin_info": real_trading_manager.get_margin_level() if real_trading_manager.leverage > 1 else None
            }
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return {"status": "error", "message": str(e)}
