import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.shared.logger import get_logger
from services.websocket_manager import WebSocketManager

router = APIRouter(tags=["websocket"])
log = get_logger("server.websocket")

# Use singleton instance
ws_manager = WebSocketManager()


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
