from fastapi import APIRouter
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from shared.logger import get_logger

router = APIRouter(prefix="/socket", tags=["socket"])
log = get_logger("stm.socket")

# Global logging state
SOCKET_LOG_ENABLED = False
BINANCE_LOG_ENABLED = False


@router.get("/logging")
async def get_socket_logging_state():
    """Get current socket logging configuration"""
    return {
        "enabled": SOCKET_LOG_ENABLED,
        "binance_enabled": BINANCE_LOG_ENABLED,
    }


@router.post("/logging")
async def set_socket_logging_state(payload: dict):
    """Configure socket logging settings"""
    global SOCKET_LOG_ENABLED, BINANCE_LOG_ENABLED
    enabled = payload.get("enabled")
    scope = str(payload.get("scope", "all")).lower()  # all | binance

    if not isinstance(enabled, bool):
        return {"status": "error", "message": "'enabled' must be boolean"}

    if scope == "binance":
        BINANCE_LOG_ENABLED = enabled
        log.info(f"🛠️  Binance socket logging: {'on' if enabled else 'off'}")
    else:
        SOCKET_LOG_ENABLED = enabled
        log.info(f"🛠️  General socket logging: {'on' if enabled else 'off'}")

    return {
        "status": "ok",
        "enabled": SOCKET_LOG_ENABLED,
        "binance_enabled": BINANCE_LOG_ENABLED,
        "scope": scope,
    }
