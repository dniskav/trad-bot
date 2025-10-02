#!/usr/bin/env python3
"""
File Position Repository Adapter
Implementación del IPositionRepository usando persistencia en archivos JSON
"""

import os
from typing import List, Optional
from pathlib import Path

from ...domain.ports.trading_ports import IPositionRepository
from ...domain.models.position import PositionAggregate, PositionStatus
from ...domain.ports.base_types import OrderSide, Money
from backend.shared.persistence import JsonStore


class FilePositionRepository(IPositionRepository):
    """Repositorio de posiciones implementado con persistencia en archivos JSON"""

    def __init__(self, data_dir: str = None):
        # Usar data dir del STM si no se especifica directamente
        if data_dir is None:
            self.data_dir = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "stm", "data"
            )
        else:
            self.data_dir = data_dir

        # Crear directorio si no existe
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)

        # Inicializar JsonStore
        self.store = JsonStore(self.data_dir)
        self.positions_file = "positions"

    async def save_position(self, position: PositionAggregate) -> None:
        """Guardar una nueva posición"""
        try:
            positions_data = self._load_positions()

            # Buscar si ya existe una posición con este ID
            existing_index = None
            for i, pos_dict in enumerate(positions_data):
                if pos_dict.get("positionId") == position.position_id:
                    existing_index = i
                    break

            # Convertir posición a dict
            position_dict = position.to_dict()

            if existing_index is not None:
                # Actualizar posición existente
                positions_data[existing_index] = position_dict
            else:
                # Agregar nueva posición
                positions_data.append(position_dict)

            self._save_positions(positions_data)

        except Exception as e:
            raise Exception(f"Error saving positions: {str(e)}")

    async def get_position(self, position_id: str) -> Optional[PositionAggregate]:
        """Obtener posición por ID"""
        try:
            positions_data = self._load_positions()

            for pos_dict in positions_data:
                if pos_dict.get("positionId") == position_id:
                    return PositionAggregate.from_dict(pos_dict)

            return None

        except Exception as e:
            raise Exception(f"Error getting position: {str(e)}")

    async def get_active_positions(
        self, symbol: Optional[str] = None
    ) -> List[PositionAggregate]:
        """Obtener posiciones activas, opcionalmente filtradas por símbolo"""
        try:
            positions_data = self._load_positions()
            active_positions = []

            for pos_dict in positions_data:
                if pos_dict.get("status") == PositionStatus.OPEN.value:
                    # Filtrar por símbolo si se especifica
                    if symbol is None or pos_dict.get("symbol") == symbol:
                        position = PositionAggregate.from_dict(pos_dict)
                        active_positions.append(position)

            return active_positions

        except Exception as e:
            raise Exception(f"Error getting active positions: {str(e)}")

    async def update_position(self, position: PositionAggregate) -> None:
        """Actualizar posición existente"""
        await self.save_position(position)

    async def close_position(
        self, position_id: str, exit_price: float, reason: str = "manual"
    ) -> None:
        """Cerrar posición"""
        try:
            position = await self.get_position(position_id)
            if not position:
                raise ValueError(f"Position {position_id} not found")

            if position.status != PositionStatus.OPEN:
                raise ValueError(f"Position {position_id} is not open")

            # Usar precio en símbolo apropiado
            from ...domain.models.position import Price

            exit_price_obj = Price.from_float(exit_price, position.symbol)

            # Calcular P&L final y cerrar
            final_pnl = position.close_position(exit_price_obj, reason)

            # Guardar posición actualizada
            await self.save_position(position)

        except Exception as e:
            raise Exception(f"Error closing position: {str(e)}")

    def _load_positions(self) -> List[dict]:
        """Cargar posiciones desde archivo JSON"""
        try:
            positions_data = self.store.read(self.positions_file, [])

            # Convertir campos de timestamp strings a dict para evitar errores
            for pos_dict in positions_data:
                # Normalizar campos de timestamp si es necesario
                if "created_at" in pos_dict and isinstance(pos_dict["created_at"], str):
                    try:
                        from datetime import datetime

                        # Validar que el timestamp sea válido
                        datetime.fromisoformat(
                            pos_dict["created_at"].replace("Z", "+00:00")
                        )
                    except:
                        # Si hay error con timestamp, usar timestamp actual
                        pos_dict["created_at"] = datetime.now().isoformat()

                if "updated_at" in pos_dict and isinstance(pos_dict["updated_at"], str):
                    try:
                        from datetime import datetime

                        datetime.fromisoformat(
                            pos_dict["updated_at"].replace("Z", "+00:00")
                        )
                    except:
                        pos_dict["updated_at"] = datetime.now().isoformat()

            return positions_data

        except Exception as e:
            # Si hay error cargando, retornar lista vacía
            return []

    def _save_positions(self, positions_data: List[dict]) -> None:
        """Guardar posiciones a archivo JSON"""
        self.store.write(self.positions_file, positions_data)


class FileOrderRepository:
    """Repositorio de órdenes implementado con persistencia en archivos JSON"""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            self.data_dir = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "stm", "data"
            )
        else:
            self.data_dir = data_dir

        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        self.store = JsonStore(self.data_dir)
        self.orders_file = "orders"

    async def save_order(self, order_dict: dict) -> None:
        """Guardar orden"""
        try:
            orders_data = self._load_orders()

            # Convertir el order domain model a dict si es necesario
            if hasattr(order_dict, "to_dict"):
                order_dict = order_dict.to_dict()

            # Agregar metadata si no existe
            if "timestamp" not in order_dict:
                from datetime import datetime

                order_dict["timestamp"] = datetime.now().isoformat()

            orders_data.append(order_dict)
            self._save_orders(orders_data)

        except Exception as e:
            raise Exception(f"Error saving order: {str(e)}")

    def _load_orders(self) -> List[dict]:
        """Cargar órdenes desde archivo"""
        try:
            return self.store.read(self.orders_file, [])
        except:
            return []

    def _save_orders(self, orders_data: List[dict]) -> None:
        """Guardar órdenes a archivo"""
        self.store.write(self.orders_file, orders_data)


if __name__ == "__main__":
    # Test del repositorio
    import asyncio

    async def test_repository():
        repo = FilePositionRepository()

        # Test crear posición
        from ...domain.models.position import (
            PositionAggregate,
            OrderSide,
            Quantity,
            Price,
            Money,
        )

        test_position = PositionAggregate(
            position_id="test_position_123",
            symbol="DOGEUSDT",
            side=OrderSide.BUY,
            quantity=Quantity.from_float(100.0),
            entry_price=Price.from_float(0.085, "DOGEUSDT"),
            leverage=5,
        )

        print("📁 Testing FilePositionRepository...")

        # Guardar posición
        await repo.save_position(test_position)
        print("✅ Position saved")

        # Recuperar posición
        retrieved = await repo.get_position("test_position_id")
        if retrieved:
            print(f"✅ Position retrieved: {retrieved.symbol} {retrieved.side.value}")
        else:
            print("❌ Position not found")

        # Obtener posições activas
        active_positions = await repo.get_active_positions()
        print(f"✅ Active positions count: {len(active_positions)}")

        print("🎯 Repository test complete!")

    # No ejecutar automáticamente el test para evitar errores de importación circular
