#!/usr/bin/env python3
"""
File Order Repository Adapter
Implementación del IOrderRepository usando persistencia en archivos JSON
"""

import os
from typing import List, Optional
from pathlib import Path

from ...domain.ports.trading_ports import IOrderRepository
from ...domain.models.order import OrderAggregate, OrderStatus
from ...domain.ports.base_types import OrderSide
from backend.shared.persistence import JsonStore


class FileOrderRepository(IOrderRepository):
    """Repositorio de órdenes implementado con persistencia en archivos JSON"""

    def __init__(self, data_dir: str = None):
        # Usar data dir del STM si no se especifica directamente
        if data_dir is None:
            self.data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "stm", "data")
        else:
            self.data_dir = data_dir
            
        # Crear directorio si no existe
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        
        # Inicializar JsonStore
        self.store = JsonStore(self.data_dir)
        self.orders_file = "orders"

    async def save_order(self, order: OrderAggregate) -> None:
        """Guardar una nueva orden"""
        try:
            orders_data = self._load_orders()
            
            # Buscar si ya existe una orden con este ID
            existing_index = None
            for i, order_dict in enumerate(orders_data):
                if order_dict.get("order_id") == order.order_id:
                    existing_index = i
                    break
            
            # Convertir orden a dict
            order_dict = order.to_dict()
            
            if existing_index is not None:
                # Actualizar orden existente
                orders_data[existing_index] = order_dict
            else:
                # Agregar nueva orden
                orders_data.append(order_dict)
                
            self._save_orders(orders_data)
            
        except Exception as e:
            raise Exception(f"Error saving order {order.order_id}: {str(e)}")

    async def get_order(self, order_id: str) -> Optional[OrderAggregate]:
        """Obtener orden por ID"""
        try:
            orders_data = self._load_orders()
            
            for order_dict in orders_data:
                if order_dict.get("order_id") == order_id:
                    return OrderAggregate.from_dict(order_dict)
            
            return None
            
        except Exception as e:
            raise Exception(f"Error getting order {order_id}: {str(e)}")

    async def get_orders_by_position(self, position_id: str) -> List[OrderAggregate]:
        """Obtener todas las órdenes de una posición"""
        try:
            orders_data = self._load_orders()
            position_orders = []
            
            for order_dict in orders_data:
                if order_dict.get("position_id") == position_id:
                    order = OrderAggregate.from_dict(order_dict)
                    position_orders.append(order)
            
            return position_orders
            
        except Exception as e:
            raise Exception(f"Error getting orders for position {position_id}: {str(e)}")

    async def get_active_orders(self, symbol: Optional[str] = None) -> List[OrderAggregate]:
        """Obtener órdenes activas, opcionalmente filtradas por símbolo"""
        try:
            orders_data = self._load_orders()
            active_orders = []
            
            # Estados que consideramos activos
            active_statuses = [
                OrderStatus.PENDING.value,
                OrderStatus.PARTIALLY_FILLED.value
            ]
            
            for order_dict in orders_data:
                if order_dict.get("status") in active_statuses:
                    # Filtrar por símbolo si se especifica
                    if symbol is None or order_dict.get("symbol") == symbol:
                        order = OrderAggregate.from_dict(order_dict)
                        active_orders.append(order)
            
            return active_orders
            
        except Exception as e:
            raise Exception(f"Error getting active orders: {str(e)}")

    async def cancel_order(self, order_id: str) -> bool:
        """Cancelar orden"""
        try:
            order = await self.get_order(order_id)
            if not order:
                return False
            
            # Verificar si se puede cancelar
            if order.status not in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]:
                return False
            
            # Cancelar orden
            order.cancel()
        
            # Guardar orden cancelada
            await self.save_order(order)
            return True
            
        except Exception as e:
            raise Exception(f"Error cancelling order {order_id}: {str(e)}")

    def _load_orders(self) -> List[dict]:
        """Cargar órdenes desde archivo JSON"""
        try:
            orders_data = self.store.read(self.orders_file, [])
            
            # Validar campos de timestamp si es necesario
            for order_dict in orders_data:
                if "created_at" in order_dict and isinstance(order_dict["created_at"], str):
                    try:
                        from datetime import datetime
                        datetime.fromisoformat(order_dict["created_at"].replace('Z', '+00:00'))
                    except:
                        order_dict["created_at"] = datetime.now().isoformat()
                
                if "updated_at" in order_dict and isinstance(order_dict["updated_at"], str):
                    try:
                        from datetime import datetime
                        datetime.fromisoformat(order_dict["updated_at"].replace('Z', '+00:00'))
                    except:
                        order_dict["updated_at"] = datetime.now().isoformat()
            
            return orders_data
            
        except Exception as e:
            # Si hay error cargando, retornar lista vacía
            return []

    def _save_orders(self, orders_data: List[dict]) -> None:
        """Guardar órdenes a archivo JSON"""
        self.store.write(self.orders_file, orders_data)

    def get_orders_for_test(self, symbol: Optional[str] = None, limit: int = 100) -> List[dict]:
        """Obtener órdenes con datos filtrados para testing"""
        try:
            orders_data = self._load_orders()
            
            if symbol:
                orders_data = [o for o in orders_data if o.get("symbol") == symbol]
            
            return orders_data[-limit:] if limit > 0 else orders_data
            
        except Exception as e:
            print(f"Error getting test orders: {e}")
            return []

    def get_order_statistics(self) -> dict:
        """Obtener estadísticas de órdenes"""
        try:
            orders_data = self._load_orders()
            
            stats = {
                "total_orders": len(orders_data),
                "by_status": {},
                "by_symbol": {},
                "by_type": {}
            }
            
            for order_dict in orders_data:
                # Estadísticas por estado
                status = order_dict.get("status", "unknown")
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
                
                # Estadísticas por símbolo
                symbol = order_dict.get("symbol", "unknown")
                stats["by_symbol"][symbol] = stats["by_symbol"].get(symbol, 0) + 1
                
                # Estadísticas por tipo
                order_type = order_dict.get("order_type", "unknown")
                stats["by_type"][order_type] = stats["by_type"].get(order_type, 0) + 1
            
            return stats
            
        except Exception as e:
            print(f"Error getting order statistics: {e}")
            return {"total_orders": 0, "by_status": {}, "by_symbol": {}, "by_type": {}}


if __name__ == "__main__":
    # Test del repositorio
    import asyncio
    
    async def test_order_repository():
        repo = FileOrderRepository()
        
        # Test crear orden
        from ...domain.models.order import OrderAggregate, OrderFactory, OrderSide, OrderType
        from ...domain.models.position import Quantity
        
        test_order = OrderFactory.create_market_order(
            symbol="DOGEUSDT",
            side=OrderSide.BUY,
            quantity=100.0,
            client_order_id="test_order_123"
        )
        test_order.position_id = "test_position_456"
        
        print("📁 Testing FileOrderRepository...")
        
        # Guardar orden
        await repo.save_order(test_order)
        print("✅ Order saved")
        
        # Recuperar orden
        retrieved = await repo.get_order(test_order.order_id)
        if retrieved:
            print(f"✅ Order retrieved: {retrieved.symbol} {retrieved.order_type.value}")
        else:
            print("❌ Order not found")
        
        # Obtener órdenes activas
        active_orders = await repo.get_active_orders()
        print(f"✅ Active orders count: {len(active_orders)}")
        
        # Estadísticas
        stats = repo.get_order_statistics()
        print(f"✅ Order stats: {stats}")
        
        print("🎯 Order repository test complete!")
    
    # No ejecutar automáticamente para evitar imports circulares
