from datetime import datetime, timezone
from fastapi import APIRouter
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from shared.logger import get_logger

router = APIRouter(tags=["health"])
log = get_logger("server.health")


@router.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
