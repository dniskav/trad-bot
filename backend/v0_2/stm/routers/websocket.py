from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.shared.logger import get_logger
from ..services.websocket_service import WebSocketService

router = APIRouter(tags=["websocket"])
log = get_logger("stm.websocket")
ws_service = WebSocketService()


@router.post("/ws/test")
async def ws_send_test(payload: Optional[dict] = None):
    """Send a test message via WebSocket to all connected clients"""
    return await ws_service.send_test_message(payload)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time data

    **Messages sent by server:**
    - stm_hello: {"type": "stm_hello", "timestamp": "2024-01-01T00:00:00"}
    - stm_heartbeat: {"type": "stm_heartbeat", "timestamp": "2024-01-01T00:00:00"}
    - account_synth: {"type": "account_synth", "data": {...}}

    **Messages received from client:**
    - ping: {"type": "ping"} -> responds with pong
    """
    await ws_service.handle_connection(websocket)
