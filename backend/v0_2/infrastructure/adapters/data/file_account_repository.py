#!/usr/bin/env python3
"""
File Account Repository Implementation
Implementación de IAccountRepository usando persistencia en archivos JSON
"""

import os
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from ...domain.models.account import AccountAggregate, BalanceChange
from ...domain.ports.base_types import RepositoryResult
from ...domain.ports.account_ports import IAccountRepository
from ...infrastructure.persistence.file_repository import JsonStore


class FileAccountRepository:
    """Repositorio de cuentas implementado con persistencia en archivos JSON"""

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
        self.accounts_file = "accounts"
        self.balance_changes_file = "balance_changes"

    async def get_account(self, account_id: str) -> Optional[AccountAggregate]:
        """Obtener cuenta por ID"""
        try:
            accounts_data = self._load_accounts()
            
            # Buscar cuenta específica
            for account_data in accounts_data:
                if account_data.get("account_id") == account_id:
                    return AccountAggregate.from_dict(account_data)
            
            return None
            
        except Exception as e:
            raise Exception(f"Error getting account {account_id}: {str(e)}")

    async def save_account(self, account: AccountAggregate) -> None:
        """Guardar cuenta"""
        try:
            accounts_data = self._load_accounts()
            
            # Buscar si ya existe
            existing_index = None
            for i, account_data in enumerate(accounts_data):
                if account_data.get("account_id") == account.account_id:
                    existing_index = i
                    break
            
            # Convertir cuenta a dict
            account_dict = account.to_dict()
            
            if existing_index is not None:
                # Actualizar cuenta existente
                accounts_data[existing_index] = account_dict
            else:
                # Agregar nueva cuenta
                accounts_data.append(account_dict)
                
            self._save_accounts(accounts_data)
            
        except Exception as e:
            raise Exception(f"Error saving account {account.account_id}: {str(e)}")

    async def add_balance_change(self, account_id : str, balance_change: BalanceChange) -> None:
        """Agregar cambio de balance al historial"""
        try:
            changes_data = self._load_balance_changes()
            
            # Filtrar solo cambios de esta cuenta
            account_changes = [
                change for change in changes_data 
                if change.get("account_id") == account_id
            ]
            
            # Agregar nuevo cambio
            change_dict = balance_change.to_dict()
            change_dict["account_id"] = account_id
            change_dict["timestamp"] = datetime.now().isoformat()
            
            # Agregar al archivo completo
            changes_data.append(change_dict)
            
            self._save_balance_changes(changes_data)
            
        except Exception as e:
            raise Exception(f"Error adding balance change: {str(e)}")

    async def get_balance_changes(self, account_id: str, limit: int = 100) -> List[BalanceChange]:
        """Obtener historial de cambios de balance para una cuenta"""
        try:
            changes_data = self._load_balance_changes()
            
            # Filtrar por cuenta y ordenar por timestamp descendente
            account_changes = [
                change for change in changes_data 
                if change.get("account_id") == account_id
            ]
            
            # Ordenar del más reciente al más antiguo
            account_changes.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            # Limitar resultados
            limited_changes = account_changes[:limit]
            
            # Convertir a objetos BalanceChange
            balance_changes = []
            for change_dict in limited_changes:
                try:
                    balance_change = BalanceChange.from_dict({
                        "asset": change_dict["asset"],
                        "amount": change_dict["amount"],
                        "transaction_type": change_dict["transaction_type"],
                        "description": change_dict["description"],
                        "related_position_id": change_dict.get("related_position_id"),
                        "timestamp": change_dict["timestamp"]
                    })
                    balance_changes.append(balance_change)
                except Exception as e:
                    # Skip cambios con errores
                    continue
            
            return balance_changes
            
        except Exception as e:
            raise Exception(f"Error getting balance changes for {account_id}: {str(e)}")

    async def get_account_list(self, limit: int = 50) -> List[AccountAggregate]:
        """Obtener lista de todas las cuentas"""
        try:
            accounts_data = self._load_accounts()
            
            accounts = []
            for account_data in accounts_data[:limit]:
                try:
                    account = AccountAggregate.from_dict(account_data)
                    accounts.append(account)
                except Exception as e:
                    # Skip cuentas con errores
                    continue
            
            return accounts
            
        except Exception as e:
            raise Exception(f"Error getting account list: {str(e)}")

    def _load_accounts(self) -> List[Dict[str, Any]]:
        """Cargar datos de cuentas"""
        try:
            accounts_data = self.store.read(self.accounts_file, [])
            
            # Validar campos de timestamp si es necesario
            for account_data in accounts_data:
                if "created_at" in account_data and isinstance(
                    account_data["created_at"], str
                ):
                    try:
                        from datetime import datetime

                        datetime.fromisoformat(
                            account_data["created_at"].replace("Z", "+00:00")
                        )
                    except:
                        account_data["created_at"] = datetime.now().isoformat()
                
                if "updated_at" in account_data and isinstance(
                    account_data["updated_at"], str
                ):
                    try:
                        from datetime import datetime

                        datetime.fromisoformat(
                            account_data["updated_at"].replace("Z", "+00:00")
                        )
                    except:
                        account_data["updated_at"] = datetime.now().isoformat()
                
                if "last_activity" in account_data and isinstance(
                    account_data["last_activity"], str
                ):
                    try:
                        from datetime import datetime

                        datetime.fromisoformat(
                            account_data["last_activity"].replace("Z", "+00:00")
                        )
                    except:
                        account_data["last_activity"] = datetime.now().isoformat()

            return accounts_data
            
        except Exception as e:
            # Si hay error cargando, retornar lista vacía
            print(f"Warning: Failed to load accounts: {e}")
            return []

    def _save_accounts(self, accounts_data: List[Dict[str, Any]]) -> None:
        """Guardar datos de cuentas"""
        self.store.write(self.accounts_file, accounts_data)

    def _load_balance_changes(self) -> List[Dict[str, Any]]:
        """Cargar datos de cambios de balance"""
        try:
            changes_data = self.store.read(self.balance_changes_file, [])
            
            # Validar campos de timestamp
            for change_data in changes_data:
                if "timestamp" in change_data and isinstance(
                    change_data["timestamp"], str
                ):
                    try:
                        from datetime import datetime

                        datetime.fromisoformat(
                            change_data["timestamp"].replace("Z", "+00:00")
                        )
                    except:
                        change_data["timestamp"] = datetime.now().isoformat()

            return changes_data
            
        except Exception as e:
            print(f"Warning: Failed to load balance changes: {e}")
            return []

    def _save_balance_changes(self, changes_data: List[Dict[str, Any]]) -> None:
        """Guardar datos de cambios de balance"""
        self.store.write(self.balance_changes_file, changes_data)

    def get_account_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de cuentas"""
        try:
            accounts_data = self._load_accounts()
            
            stats = {
                "total_accounts": len(accounts_data),
                "total_balance_usdt": 0.0,
                "accounts_with_zero_balance": 0,
                "average_balance_usdt": 0.0,
                "high_balance_accounts": 0,
            }
            
            if accounts_data:
                balances = []
                for account_data in accounts_data:
                    try:
                        balance = float(
                            account_data.get("total_balance_usdt", 0) or 0
                        )
                        balances.append(balance)
                        
                        if balance == 0:
                            stats["accounts_with_zero_balance"] += 1
                        elif balance > 1000:
                            stats["high_balance_accounts"] += 1
                    except:
                        continue
                
                if balances:
                    stats["total_balance_usdt"] = sum(balances)
                    stats["average_balance_usdt"] = stats["total_balance_usdt"] / len(balances)
            
            return stats
            
        except Exception as e:
            print(f"Error getting account statistics: {e}")
            return {"error": str(e)}

    def migrate_from_legacy_account(self, legacy_account_data: Dict[str, Any]) -> AccountAggregate:
        """Migrar de formato de cuenta legacy a nuestro formato"""
        try:
            from ...domain.models.account import AssetType, AssetBalance, Money
            
            # Crear nueva cuenta
            account = AccountAggregate.create_default()
            account.account_id = "default"
            
            # Convertir datos legacy
            usdt_balance = float(legacy_account_data.get("usdt_balance", 500.0))
            doge_balance = float(legacy_account_data.get("doge_balance", 5000.0))
            
            # Crear assets con balances legacy
            account.add_asset(AssetType.USDT, Money.from_float(usdt_balance))
            account.add_asset(AssetType.DOGE, Money.from_float(doge_balance))
            
            # Actualizar balances USDT
            account.initial_balance_usdt = Money.from_float(
                float(legacy_account_data.get("initial_balance", 1000.0))
            )
            account.total_balance_usdt = Money.from_float(
                float(legacy_area_data.get("total_balance_usdt", 1000.0))
            )
            account.current_balance_usdt = Money.from_float(
                float(legacy_account_data.get("current_balance", 1000.0))
            )
            account.total_pnl = Money.from_float(
                float(legacy_account_data.get("total_pnl", 0.0))
            )
            account.invested_amount = Money.from_float(
                float(legacy_account_data.get("invested", 0.0))
            )
            
            # Usar timestamp legacy si existe
            if "last_updated" in legacy_account_data:
                try:
                    legacy_datetime = datetime.fromisoformat(
                        legacy_account_data["last_updated"].replace("Z", "+00:00")
                    )
                    account.last_activity = legacy_datetime
                    account.updated_at = legacy_datetime
                except:
                    pass
            
            return account
            
        except Exception as e:
            print(f"Error migrating legacy account: {e}")
            # Retornar cuenta por defecto si hay error
            return AccountAggregate.create_default()


if __name__ == "__main__":
    # Test del repositorio
    import asyncio
    
    async def test_account_repository():
        repo = FileAccountRepository()
        
        print("📁 Testing FileAccountRepository...")
        
        # Test crear cuenta
        from ...domain.models.account import AccountAggregate
        
        account = AccountAggregate.create_default()
        account.account_id = "test_account_123"
        
        # Guardar cuenta
        await repo.save_account(account)
        print("✅ Account saved")
        
        # Recuperar cuenta
        retrieved = await repo.get_account("test_account_123")
        if retrieved:
            print(f"✅ Account retrieved: {retrieved.account_id}")
        else:
            print("❌ Account not found")
        
        # Test balance change
        from ...domain.models.account import BalanceChange, TransactionType, AssetType
        from ...domain.models.position import Money
        
        balance_change = BalanceChange(
            asset=AssetType.USDT,
            amount=Decimal("100.0"),
            transaction_type=TransactionType.DEPOSIT,
            description="Test deposit",
            related_position_id="test_pos_123"
        )
        
        await repo.add_balance_change("test_account_123", balance_change)
        print("✅ Balance change added")
        
        # Obtener cambios
        changes = await repo.get_balance_changes("test_account_123", limit=5)
        print(f"✅ Balance changes count: {len(changes)}")
        
        # Estadísticas
        stats = repo.get_account_statistics()
        print(f"✅ Account stats: {stats}")
        
        print("🎯 Account repository test complete!")
    
    # No ejecutar automáticamente para evitar imports circulares
