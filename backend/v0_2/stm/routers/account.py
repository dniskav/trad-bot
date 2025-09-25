from fastapi import APIRouter
from backend.shared.logger import get_logger
from ..services.account_service import AccountService

router = APIRouter(prefix="/account", tags=["account"])
log = get_logger("stm.account")
account_service = AccountService()


@router.get("/synth")
async def get_account_synth():
    """Get synthetic account balance"""
    return await account_service.get_account()


@router.post("/synth/reset")
async def reset_account_synth():
    """Reset synthetic account to default values (500 USDT + 500 DOGE equivalent)"""
    return await account_service.reset_account()
