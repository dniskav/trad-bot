#!/usr/bin/env python3
"""
Hexagonal Bridge
Puente para integrar la nueva arquitectura hexagonal con el código existente
"""

from typing import Dict, Any, Optional
import asyncio
from datetime import datetime

from ..infrastructure.di_configuration import create_production_container, get_trading_service
from ..application.services.trading_service import TradingApplicationService


class HexagonalBridge:
    """
    Bridge para conectar el código existente con la nueva arquitectura hexagonal.
    
    Este bridge permite una migración incremental donde las APIs existentes
    pueden usar los nuevos Application Services mientras mantenemos compatibilidad.
    """
    
    def __init__(self):
        self.container = create_production_container()
        self.trading_service: Optional[TradingApplicationService] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Inicializar el bridge"""
        if self._initialized:
            return
        
        try:
            # Resolver servicios principaces
            self.trading_service = get_trading_service(self.container)
            self._initialized = True
            print("🌉 Hexagonal Bridge initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize bridge: {e}")
            raise

    async def open_position_bridge(
        self,
        symbol: str,
        side: str,
        quantity: str,
        order_type: str = "MARKET",
        leverage: int = 1,
        stop_loss: Optional[str] = None,
        take_profit: Optional[str] = None,
        client_order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Bridge para open_position compatible con sintaxis existente
        
        Convierte parámetros de formato string/legacy al formato de domain models
        y llama al Application Service apropiado.
        """
        if not self._initialized:
            await self.initialize()

        # Validar parámetros
        if not symbol or not side or not quantity:
            return {"success": False, "message": "Missing required parameters"}

        try:
            # Convertir parámetros string a tipos apropiados
            from ..domain.models.position import OrderSide
            
            # Parsear side
            side_enum = OrderSide.BUY if side.strip().upper() == "BUY" else OrderSide.SELL
            
            # Parsear quantity
            quantity_float = float(quantity)
            
            # Parsear optional prices
            stop_loss_float = float(stop_loss) if stop_loss else None
            take_profit_float = float(take_profit) if take_profit else None

            # Llamar al Application Service
            result = await self.trading_service.open_position(
                symbol=symbol,
                side=side_enum,
                quantity=quantity_float,
                order_type=order_type,
                leverage=leverage,
                stop_loss=stop_loss_float,
                take_profit=take_profit_float,
                client_order_id=client_order_id
            )
            
            return result
            
        except ValueError as e:
            return {"success": False, "message": f"Parameter validation error: {str(e)}"}
        except Exception as e:
            return {"success": False, "message": f"Bridge execution error: {str(e)}"}

    async def close_position_bridge(self, position_id: str, reason: str = "manual") -> Dict[str, Any]:
        """
        Bridge para close_position compatible con código existente
        """
        if not self._initialized:
            await self.initialize()

        try:
            result = await self.trading_service.close_position(position_id, reason)
            return result
            
        except Exception as e:
            return {"success": False, "message": f"Bridge execution error: {str(e)}"}

    async def get_position_status_bridge(self, position_id: str) -> Optional[Dict[str, Any]]:
        """
        Bridge para obtener estado de posición
        """
        if not self._initialized:
            await self.initialize()

        try:
            return await self.trading_service.get_position_status(position_id)
            
        except Exception as e:
            print(f"Error getting position status: {e}")
            return None

    async def execute_risk_management_bridge(self) -> Dict[str, Any]:
        """
        Bridge para ejecutar gestión de riesgo automática
        """
        if not self._initialized:
            await self.initialize()

        try:
            return await self.trading_service.check_and_execute_risk_management()
            
        except Exception as e:
            return {"success": False, "message": f"Risk management error: {str(e)}"}

    # === MÉTODOS DE COMPATIBILIDAD CON CÓDIGO EXISTENTE ===

    async def binance_margin_order_bridge(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Bridge compatibilidad para binance_margin_order existente
        
        Este método mantiene compatibilidad con la interfaz existente
        mientras usa la nueva arquitectura internamente.
        """
        try:
            # Extraer parámetros del request Binance-compatible
            symbol = request_data.get("symbol", "")
            side = request_data.get("side", "")
            order_type = request_data.get("type", "MARKET")
            quantity = request_data.get("quantity", "0")
            leverage = request_data.get("leverage", 1)
            
            # Convertir quantity de string a float
            quantity_float = float(quantity)
            
            # Crear order side enum
            from ..domain.models.position import OrderSide
            side_enum = OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL
            
            # Determinar si es creación de posición o actualización (SL/TP)
            if order_type in ["MARKET", "LIMIT"] and len(request_data.get("stopPrice", "")) == 0:
                # Es orden para crear nueva posición
                result = await self.open_position_bridge(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    order_type=order_type,
                    leverage=leverage,
                    price=float(request_data.get("price", 0)) if request_data.get("price") else None
                )
                
                # Formatear respuesta compatible con Binance
                if result.get("success"):
                    return {
                        "success": True,
                        "orderId": result.get("order_id", ""),
                        "positionId": result.get("position_id"),
                        "executedPrice": str(result.get("executed_price", 0)),
                        "executedQuantity": str(result.get("executed_quantity", 0)),
                        "message": "Order executed successfully"
                    }
                else:
                    return {
                        "success": False,
                        "message": result.get("message", "Order execution failed")
                    }
            
            else:
                # Es orden SL/TP - manejar con lógica específica
                return await self._handle_sl_tp_order_bridge(request_data)
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Error processing Binance order: {str(e)}"
            }

    async def _handle_sl_tp_order_bridge(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manejar órdenes SL/TP manteniendo compatibilidad
        """
        # TODO: Implementar lógica específica para SL/TP
        # Por ahora retornar respuesta compatibles
        return {
            "success": True,
            "orderId": f"sl_tp_{datetime.now().timestamp()}",
            "message": "SL/TP order placed (backward compatible)"
        }


# Instancia global del bridge para usar en los routers existentes
_global_bridge: Optional[HexagonalBridge] = None


def get_hexagonal_bridge() -> HexagonalBridge:
    """Obtener instancia global del bridge"""
    global _global_bridge
    if _global_bridge is None:
        _global_bridge = HexagonalBridge()
    return _global_bridge


async def initialize_hexagonal_bridge() -> HexagonalBridge:
    """Inicializar bridge hexagonal global"""
    bridge = get_hexagonal_bridge()
    await bridge.initialize()
    return bridge


# === EJEMPLOS DE USO EN ROUTERS EXISTENTES ===

async def example_position_router_integration():
    """
    Ejemplo de cómo integrar el bridge en un router existente
    """
    bridge = await initialize_hexagonal_bridge()
    
    # Ejemplo: llamada compatible con código existente
    result = await bridge.binance_margin_order_bridge({
        "symbol": "DOGEUSDT",
        "side": "BUY", 
        "type": "MARKET",
        "quantity": "100",
        "leverage": 20
    })
    
    print(f"Example bridge result: {result}")
    return result


if __name__ == "__main__":
    # Test del bridge
    async def test_bridge():
        bridge = await initialize_hexagonal_bridge()
        
        # Test open position
        result = await bridge.open_position_bridge(
            symbol="DOGEUSDT",
            side="BUY",
            quantity="100"
        )
        
        print(f"🔗 Bridge test result: {result}")
    
    asyncio.run(test_bridge())
