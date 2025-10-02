#!/usr/bin/env python3
"""
FastAPI Application con integración hexagonal para Account Domain
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .account_service_integration import (
    account_service_fastapi_integration,
    get_account_service,
    account_health_check
)
from .routers import health, socket, websocket
from .middlewares.logging_middleware import LoggingMiddleware


# Crear aplicación FastAPI
app = FastAPI(
    title="Trading Bot Server v0.2 - Account Hexagonal Integration",
    description="Server con integración hexagonal para Account Domain",
    version="2.1.0-hexagonal"
)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de logging personalizado
app.add_middleware(LoggingMiddleware, logger_name="server.hexagonal.account")

# Incluir routers principales
app.include_router(health.router, tags=["health"])
app.include_router(socket.router, tags=["socket"])
app.include_router.include_router(websocket.router, tags=["websocket"])

# Importar router de Account después de definir get_account_service
from .routers.account import router as account_router

# Función helper para el router Account
async def inject_account_service():
    """Función helper para inyectar el servicio de Account"""
    return await get_account_service()

# Agregar dependencia al router Account
account_router.dependency_overrides.setdefault("account_service", inject_account_service)

# Incluir router de Account
app.include_router(account_router, tags=["account"])

@app.on_event("startup")
async def startup_event():
    """Evento de inicio de la aplicación"""
    print("🚀 Starting Server v0.2 with Account Hexagonal Integration...")
    
    # Inicializar integración de Account en background
    await account_service_fastapi_integration.initialize_background()
    
    print("✅ Server v0.2 Account Hexagonal Integration startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Evento de shutdown de la aplicación"""
    print("🛑 Shutting down Server v0.2 Account Hexagonal Integration...")
    
    # Shutdown de la integración de Account
    await account_service_fastapi_integration.shutdown()
    
    print("✅ Server v0.2 Account Hexagonal Integration shutdown complete")


@app.get("/health/account")
async def health_check_endpoint():
    """Endpoint específico de health check para Account services"""
    
    try:
        health_data = await account_health_check()
        
        # Determinar status general
        account_status = health_data.get("account_integration", {}).get("status", "unknown")
        
        if account_status == "ok":
            status_code = 200
            message = "All Account services operational"
        else:
            status_code = 503
            message = "Account services degraded"
        
        return {
            "status": "ok" if status_code == 200 else "error",
            "message": message,
            "account_integration": health_data,
            "timestamp": health_data.get("timestamp", "unknown")
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Health check failed: {str(e)}",
            "account_integration": {"status": "error", "error": str(e)}
        }


@app.get("/account/integration/status")
async def integration_status():
    """Endpoint para verificar el estado de la integración hexagonal"""
    
    try:
        health_data = await account_health_check()
        integration_status = health_data.get("account_integration", {})
        
        return {
            "integration_type": "Account Domain Hexagonal",
            "architecture": "Clean Architecture + DI Container",
            "status": integration_status.get("status", "unknown"),
            "hexagonal_available": integration_status.get("hexagonal_available", False),
            "legacy_fallback": integration_status.get("legacy_fallback_available", False),
            "services": {
                "hexagonal": "AccountApplicationService + Adapters" if integration_status.get("hexagonal_available") else "Not available",
                "legacy": "STMService (Fallback)" if integration_status.get("legacy_fallback_available") else "Not available"
            },
            "health_details": health_data,
            "timestamp": integration_status.get("timestamp", "unknown")
        }
        
    except Exception as e:
        return {
            "integration_type": "Account Domain Hexagonal",
            "status": "error",
            "error": str(e),
            "fallback_mode": True
        }


@app.get("/")
async def root():
    """Root endpoint con información de la arquitectura"""
    
    return {
        "service": "Trading Bot Server v0.2",
        "architecture": "Hexagonal Architecture + Clean Architecture",
        "version": "2.1.0-hexagonal",
        "account_integration": "Active",
        "domains": {
            "account": "Integrated with hexagonal architecture",
            "strategy": "Integrated with hexagonal architecture", 
            "trading": "Integrated with hexagonal architecture"
        },
        "endpoints": {
            "health": "/health",
            "account_health": "/health/account",
            "integration_status": "/account/integration/status",
            "account_synth": "/account/synth",
            "reset_account": "/account/synth/reset"
        },
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8201,  # Puerto diferente para testeos
        log_level="info"
    )
