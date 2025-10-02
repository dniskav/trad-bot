from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from shared.logger import get_logger
from ..services.stm_service import STMService

router = APIRouter(prefix="/account", tags=["account"])
log = get_logger("server.account")


# Función helper para obtener el servicio de Account apropiado
async def get_account_service():
    """Obtener servicio de Account (hexagonal o legacy como fallback)"""

    # Intentar usar integración hexagonal si está disponible
    try:
        from ..account_service_integration import (
            get_account_service as hexagonal_service,
        )

        service = await hexagonal_service()

        # Verificar si es el servicio hexagonal
        if hasattr(service, "account_service"):
            log.info("Using Account Hexagonal Service")
            return service
        else:
            log.info("Using Account Legacy Service (via adapter)")
            return service

    except Exception as e:
        log.warning(f"Hexagonal service not available, using legacy: {e}")
        # Fallback a servicio legacy
        return STMService()


# Estado de los endpoints para logging
account_endpoint_status = {"service_type": "unknown", "last_check": "never"}


@router.get("/synth")
async def get_account_synth(account_service=Depends(get_account_service)):
    """Get synthetic account data (hexagonal or legacy)"""

    try:
        # Actualizar estado del endpoint
        service_name = type(account_service).__name__
        account_endpoint_status["service_type"] = service_name
        account_endpoint_status["last_check"] = "now"

        log.info(f"Account service used: {service_name}")

        # Call method - hexagonal service has account_service attribute
        if hasattr(account_service, "account_service"):
            result = await account_service.get_account_synth()
        else:
            # Legacy service
            result = await account_service.get_account_synth()

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
async def reset_account_synth(account_service=Depends(get_account_service)):
    """Reset synthetic account (hexagonal or legacy)"""

    try:
        # Actualizar estado del endpoint
        service_name = type(account_service).__name__
        log.info(f"Account reset service used: {service_name}")

        # Call method - hexagonal service has account_service attribute
        if hasattr(account_service, "account_service"):
            result = await account_service.reset_account_synth()
        else:
            # Legacy service
            result = await account_service.reset_account_synth()

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


@router.get("/status")
async def get_account_status():
    """Get account service status and integration info"""

    try:
        return JSONResponse(
            content={
                "endpoint_status": account_endpoint_status,
                "integration_types": ["hexagonal", "legacy"],
                "fallback_available": True,
                "timestamp": "now",
            },
            status_code=200,
        )

    except Exception as e:
        log.error(f"Error getting account status: {e}")
        return JSONResponse(
            content={"status": "error", "message": "Internal server error"},
            status_code=500,
        )
