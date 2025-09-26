import asyncio
from typing import Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from backend.shared.logger import get_logger
from ..services.websocket_manager import WebSocketManager
from ..services.stm_service import STMService

router = APIRouter(tags=["websocket"])
log = get_logger("server.websocket")

# Use singleton instances
ws_manager = WebSocketManager()
stm_service = STMService()

# In-memory cache to log PnL changes only when they actually change
_last_pnl_by_position: Dict[str, float] = {}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data broadcasting"""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; we don't expect incoming messages
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@router.post("/ws/notify")
async def notify_websocket_clients(request: Request):
    """Receive notifications from STM and broadcast to WebSocket clients"""
    try:
        data = await request.json()
        log.info(f"Received notification: {data.get('type')}")

        # Broadcast to all connected WebSocket clients
        await ws_manager.broadcast(data)

        # On position-related events, fetch open positions and log PnL changes
        if data.get("type") == "position_change":
            try:
                resp = await stm_service.get_positions(status="open")
                positions = resp.get("positions", []) or []

                for p in positions:
                    pid = p.get("positionId")
                    pnl = p.get("pnl")
                    if pid is None or pnl is None:
                        continue

                    last = _last_pnl_by_position.get(pid)
                    # Log only when PnL actually changes (allow tiny epsilon)
                    if last is None or abs(float(pnl) - float(last)) > 1e-8:
                        _last_pnl_by_position[pid] = float(pnl)
                        log.info(f"PNL change | position={pid} pnl={float(pnl):.8f}")
            except Exception as e:
                log.warning(f"Failed logging PnL changes: {e}")

        return {"success": True, "message": "Notification broadcasted"}
    except Exception as e:
        log.error(f"Error processing notification: {e}")
        return {"success": False, "error": str(e)}
