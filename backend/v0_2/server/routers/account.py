from fastapi import APIRouter
from fastapi.responses import JSONResponse
from backend.shared.logger import get_logger
from ..services.stm_service import STMService

router = APIRouter(prefix="/account", tags=["account"])
log = get_logger("server.account")

# Use singleton instance
stm_service = STMService()


@router.get("/synth")
async def get_account_synth():
    """Get synthetic account data from STM"""
    try:
        result = await stm_service.get_account_synth()

        if "code" in result:
            return JSONResponse(
                content={"status": "error", "message": result["message"]},
                status_code=result["code"],
            )

        return JSONResponse(content=result, status_code=200)
    except Exception as e:
        log.error(f"Error getting account synth: {e}")
        return JSONResponse(
            content={"status": "error", "message": "Internal server error"},
            status_code=500,
        )


@router.post("/synth/reset")
async def reset_account_synth():
    """Reset synthetic account via STM"""
    try:
        result = await stm_service.reset_account_synth()

        if "code" in result:
            return JSONResponse(
                content={"status": "error", "message": result["message"]},
                status_code=result["code"],
            )

        return JSONResponse(content=result, status_code=200)
    except Exception as e:
        log.error(f"Error resetting account synth: {e}")
        return JSONResponse(
            content={"status": "error", "message": "Internal server error"},
            status_code=500,
        )
