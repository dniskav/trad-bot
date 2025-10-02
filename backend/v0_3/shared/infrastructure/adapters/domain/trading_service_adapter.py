#!/usr/bin/env python3
"""
Trading Service Adapter
Adaptador para conectar routers de trading con el nuevo TradingApplicationService
"""

import asyncio
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from ..application.services.trading_service import TradingApplicationService


class TradingServiceAdapter:
    """
    Adapter que adapta el TradingApplicationService a las interfaces esperadas por los routers legacy
    Este adapter mantiene compatibilidad con la API existente mientras usa la nueva arquitectura
    """

    def __init__(self, trading_application_service: TradingApplicationService):
        self.trading_service = trading_application_service

    # === POSITION MANAGEMENT ===

    async def open_position(self, req_data: Dict[str, Any]) -> Dict[str, Any]:
        """Abrir posición usando el nuevo servicio"""
        
        try:
            # Extraer datos de la request
            symbol = req_data.get("symbol")
            side = req_data.get("side", "BUY")
            quantity = float(req_data.get("quantity", 0))
            order_type = req_data.get("orderType", "MARKET")
            price = req_data.get("price")
            leverage = int(req_data.get("leverage", 1))
            client_order_id = req_data.get("clientOrderId") or str(uuid.uuid4())
            
            stop_loss = req_data.get("stopLoss", {}).get("price") if req_data.get("stopLoss") else None
            take_profit = req_data.get("takeProfit", {}).get("price") if req_data.get("takeProfit") else None
            
            # Validar datos requeridos
            if not symbol or not quantity or quantity <= 0:
                return {
                    "success": False,
                    "message": "Invalid symbol or quantity",
                    "errorCode": "INVALID_PARAMS"
                }
            
            # Crear orden usando el nuevo servicio
            result = await self.trading_service.open_position(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                price=price,
                leverage=leverage,
                stop_loss=stop_loss,
                take_profit=take_profit,
                client_order_id=client_order_id
            )
            
            # Convertir resultado a formato legacy compatible
            if result.get("success"):
                position_data = result.get("position", {})
                
                legacy_response = {
                    "success": True,
                    "positionId": position_data.get("position_id"),
                    "clientOrderId": client_order_id,
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "orderType": order_type,
                    "price": position_data.get("entry_price"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "OPENED"
                }
                
                return legacy_response
            else:
                return {
                    "success": False,
                    "message": result.get("error", "Failed to open position"),
                    "errorCode": result.get("error_code", "TRADING_ERROR")
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error: {str(e)}",
                "errorCode": "INTERNAL_ERROR"
            }

    async def close_position(self, position_id: str, reason: str = "MANUAL") -> Dict[str, Any]:
        """Cerrar posición usando el nuevo servicio"""
        
        try:
            # Cerrar posición usando el nuevo servicio
            result = await self.trading_service.close_position(
                position_id=position_id,
                reason=reason
            )
            
            # Convertir resultado a formato legacy compatible
            if result.get("success"):
                position_data = result.get("position", {})
                
                legacy_response = {
                    "success": True,
                    "positionId": position_id,
                    "status": "CLOSED",
                    "closePrice": position_data.get("close_price"),
                    "pnl": position_data.get("realized_pnl"),
                    "closeTime": datetime.now(timezone.utc).isoformat(),
                    "reason": reason
                }
                
                return legacy_response
            else:
                return {
                    "success": False,
                    "message": result.get("error", "Failed to close position"),
                    "errorCode": result.get("error_code", "CLOSE_ERROR")
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error: {str(e)}",
                "errorCode": "INTERNAL_ERROR"
            }

    async def get_positions(self, status: Optional[str] = None, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Obtener posiciones usando el nuevo servicio"""
        
        try:
            # Obtener posiciones usando el nuevo servicio
            result = await self.trading_service.get_positions(
                status=status,
                symbol=symbol
            )
            
            # Convertir resultado a formato legacy compatible
            if result.get("success"):
                positions = result.get("positions", [])
                
                legacy_response = {
                    "success": True,
                    "positions": positions,
                    "total": len(positions),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                return legacy_response
            else:
                return {
                    "success": False,
                    "message": result.get("error", "Failed to get positions"),
                    "positions": [],
                    "total": 0
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error: {str(e)}",
                "positions": [],
                "total": 0
            }

    async def set_stop_loss(self, position_id: str, price: float) -> Dict[str, Any]:
        """Establecer stop loss usando el nuevo servicio"""
        
        try:
            result = await self.trading_service.modify_position(
                position_id=position_id,
                stop_loss=price
            )
            
            if result.get("success"):
                return {
                    "success": True,
                    "positionId": position_id,
                    "stopLoss": price,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                return {
                    "success": False,
                    "message": result.get("error", "Failed to set stop loss"),
                    "errorCode": result.get("error_code", "SL_ERROR")
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error: {str(e)}",
                "errorCode": "INTERNAL_ERROR"
            }

    async def set_take_profit(self, position_id: str, price: float) -> Dict[str, Any]:
        """Establecer take profit usando el nuevo servicio"""
        
        try:
            result = await self.trading_service.modify_position(
                position_id=position_id,
                take_profit=price
            )
            
            if result.get("success"):
                return {
                    "success": True,
                    "positionId": position_id,
                    "takeProfit": price,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                return {
                    "success": False,
                    "message": result.get("error", "Failed to set take profit"),
                    "errorCode": result.get("error_code", "TP_ERROR")
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error: {str(e)}",
                "errorCode": "INTERNAL_ERROR"
            }

    # === FEES MANAGEMENT ===

    async def get_fees(self, symbol: str) -> Dict[str, Any]:
        """Obtener comisiones usando el nuevo servicio"""
        
        try:
            # Obtener comisiones usando el nuevo servicio
            result = await self.trading_service.get_commission_rates(symbol=symbol)
            
            # Convertir resultado a formato legacy compatible
            if result.get("success"):
                fees_data = result.get("fees", {})
                
                legacy_response = {
                    "symbol": symbol,
                    "makerCommission": str(fees_data.get("maker", "0.001")),
                    "takerCommission": str(fees_data.get("taker", "0.001")),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                return legacy_response
            else:
                # Fallback a valores por defecto
                return {
                    "symbol": symbol,
                    "makerCommission": "0.001",
                    "takerCommission": "0.001",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "note": "Using default fees"
                }
                
        except Exception as e:
            # Fallback a valores por defecto
            return {
                "symbol": symbol,
                "makerCommission": "0.001",
                "takerCommission": "0.001",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": f"Fallback to defaults: {str(e)}"
            }

    # === ORDER MANAGEMENT ===

    async def get_orders(self, symbol: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
        """Obtener órdenes usando el nuevo servicio"""
        
        try:
            result = await self.trading_service.get_orders(
                symbol=symbol,
                status=status
            )
            
            if result.get("success"):
                orders = result.get("orders", [])
                
                legacy_response = {
                    "success": True,
                    "orders": orders,
                    "total": len(orders),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                return legacy_response
            else:
                return {
                    "success": False,
                    "message": result.get("error", "Failed to get orders"),
                    "orders": [],
                    "total": 0
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error: {str(e)}",
                "orders": [],
                "total": 0
            }

    # === MARKET DATA ===

    async def get_ticker_price(self, symbol: str) -> Dict[str, Any]:
        """Obtener precio actual usando el nuevo servicio"""
        
        try:
            result = await self.trading_service.get_current_price(symbol=symbol)
            
            if result.get("success"):
                price_data = result.get("price", {})
                
                legacy_response = {
                    "symbol": symbol,
                    "price": str(price_data.get("price", "0")),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                return legacy_response
            else:
                return {
                    "symbol": symbol,
                    "price": "0",
                    "error": result.get("error", "Price not available"),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            return {
                "symbol": symbol,
                "price": "0",
                "error": f"Price error: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    # === UTILITY METHODS ===

    async def health_check(self) -> Dict[str, Any]:
        """Health check del servicio de trading"""
        
        try:
            # Verificar conectividad básica
            test_result = await self.trading_service.get_positions(status="open", limit=1)
            
            if test_result.get("success"):
                return {
                    "status": "healthy",
                    "trading_service": "operational",
                    "backend_dependencies": "connected",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                return {
                    "status": "degraded",
                    "trading_service": "data_access_issues",
                    "backend_dependencies": "unknown",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            return {
                "status": "error",
                "trading_service": "offline",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def get_adapter_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del adapter"""
        
        return {
            "adapter_type": "TradingServiceAdapter",
            "target_service": "TradingApplicationService",
            "status": "active",
            "compatibility_mode": "legacy_trading_format",
            "created_at": datetime.now(timezone.utc).isoformat()
        }


class TradingServiceIntegration:
    """
    Clase para integrar el nuevo Trading Domain con el sistema legacy
    """
    
    def __init__(self):
        self.trading_adapter: Optional[TradingServiceAdapter] = None
        self.initialized = False

    async def initialize(self):
        """Inicializar la integración Trading"""
        
        if self.initialized:
            return

        try:
            print("🔧 Initializing Trading Service Integration...")

            # Resolver TradingApplicationService del DI Container
            from ..infrastructure.di_configuration import create_production_container

            container = create_production_container()

            from ..application.services.trading_service import TradingApplicationService

            trading_service = await container.resolve_service(TradingApplicationService)

            if not trading_service:
                raise Exception(
                    "Failed to resolve TradingApplicationService from DI Container"
                )

            print(
                f"✅ TradingApplicationService resolved: {type(trading_service).__name__}"
            )

            # Crear adapter
            self.trading_adapter = TradingServiceAdapter(trading_service)

            print("✅ TradingServiceAdapter created")

            self.initialized = True
            print("✅ Trading Service Integration initialized successfully")

        except Exception as e:
            print(f"❌ Error initializing Trading Service Integration: {e}")
            print("⚠️ Will use fallback STM Service")
            self.initialized = False

    def get_trading_service_adapter(self):
        """Obtener adapter para usar con los routers"""
        
        if not self.initialized or not self.trading_adapter:
            raise Exception("Trading Service Integration not initialized")

        return self.trading_adapter

    async def health_check(self) -> Dict[str, Any]:
        """Health check de la integración Trading"""
        
        try:
            if not self.initialized or not self.trading_adapter:
                return {
                    "status": "error",
                    "message": "Trading Service Integration not initialized",
                    "fallback_available": True,
                }

            # Ejecutar health check del adapter
            adapter_health = await self.trading_adapter.health_check()

            return {
                "status": "ok",
                "integration_initialized": self.initialized,
                "adapter_health": adapter_health,
                "fallback_available": True,  # Siempre disponible STM service
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Health check failed: {str(e)}",
                "fallback_available": True,
            }


# Instancia global para integración
trading_service_integration = TradingServiceIntegration()
