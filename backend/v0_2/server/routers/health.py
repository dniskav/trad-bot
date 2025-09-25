from datetime import datetime, timezone
from fastapi import APIRouter
from backend.shared.logger import get_logger

router = APIRouter(tags=["health"])
log = get_logger("server.health")


@router.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
