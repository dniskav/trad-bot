from fastapi import APIRouter
from fastapi.responses import JSONResponse
from backend.shared.logger import get_logger
from ..services.stm_service import STMService

router = APIRouter(prefix="/socket", tags=["socket"])
log = get_logger("server.socket")

# Use singleton instance
stm_service = STMService()


@router.get("/logging")
async def get_socket_logging_state():
    """Get current socket logging state"""
    result = await stm_service.get_socket_logging_state()

    if "code" in result:
        return JSONResponse(
            content={"status": "error", "message": result["message"]},
            status_code=result["code"],
        )

    return JSONResponse(content=result, status_code=200)


@router.post("/logging")
async def set_socket_logging_state(payload: dict):
    """Set socket logging state"""
    result = await stm_service.set_socket_logging_state(payload)

    if "code" in result:
        return JSONResponse(
            content={"status": "error", "message": result["message"]},
            status_code=result["code"],
        )

    return JSONResponse(content=result, status_code=200)
