#!/usr/bin/env python3
"""
Trading endpoints
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# These will be injected by the main server
trading_tracker = None


def set_dependencies(tt):
    """Set dependencies from main server"""
    global trading_tracker
    trading_tracker = tt


@router.get("/trading/status")
async def get_trading_status():
    """Obtiene el estado del trading"""
    try:
        if not trading_tracker:
            return JSONResponse(
                {"error": "Trading tracker no inicializado"}, status_code=500
            )

        tracker_data = trading_tracker.get_all_positions()

        return {
            "status": "success",
            "data": {
                "total_trades": len(tracker_data.get("history", [])),
                "open_positions": len(tracker_data.get("active_positions", {})),
                "account_balance": tracker_data.get("account_balance", {}),
                "statistics": tracker_data.get("statistics", {}),
            },
        }
    except Exception as e:
        logger.error(f"Error getting trading status: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/trading/history-legacy")
async def get_trading_history_legacy(page: int = 1, page_size: int = 100):
    """[LEGACY] Historia antigua. Usa /api/trading/history del módulo positions."""
    try:
        return JSONResponse(
            {
                "status": "error",
                "message": "Este endpoint es legacy. Usa /api/trading/history",
            },
            status_code=410,
        )
    except Exception as e:
        logger.error(f"Error (legacy history): {e}")
        return {"status": "error", "message": str(e)}


@router.post("/trading/persist")
async def persist_trading_data():
    """Fuerza la persistencia de datos de trading"""
    try:
        if not trading_tracker:
            return JSONResponse(
                {"error": "Trading tracker no inicializado"}, status_code=500
            )

        trading_tracker.save_history()

        return {"status": "success", "message": "Datos persistidos correctamente"}
    except Exception as e:
        logger.error(f"Error persisting trading data: {e}")
        return {"status": "error", "message": str(e)}
