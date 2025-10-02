#!/usr/bin/env python3
"""
Simple Account Domain Test
Test independiente de Account Domain sin DI Container
"""

import asyncio
import sys
import os
from decimal import Decimal
from datetime import datetime

# Agregar paths para imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, current_dir)
sys.path.insert(0, parent_dir)


async def test_account_models():
    """Test básico de modelos de Account"""
    print("🧪 Testing Account Domain Models...")

    try:
        # Test 1: AssetBalance
        print("\n💰 Test 1: AssetBalance")

        from domain.models.account import AssetBalance, AssetType
        from domain.models.position import Money

        usdt_balance = AssetBalance(
            asset=AssetType.USDT,
            free=Money.from_float(500.0),
            locked=Money.from_float(100.0),
        )

        print(f"✅ Created USDT balance:")
        print(f"   Free: ${usdt_balance.free.amount}")
        print(f"   Locked: ${usdt_balance.locked.amount}")
        print(f"   Total: ${usdt_balance.get_total_amount().amount}")

        # Test 2: AccountAggregate
        print("\n📋 Test 2: AccountAggregate")

        from domain.models.account import AccountAggregate, TransactionType

        account = AccountAggregate.create_default()
        account.account_id = "test_model_123"

        print(f"✅ Created account: {account.account_id}")
        print(f"   Initial Balance: ${account.initial_balance_usdt.amount}")
        print(f"   Assets count: {len(account.assets)}")

        # Test 3: Lock/Unlock operations
        print("\n🔒 Test 3: Lock/Unlock Operations")

        # Bloquear $50 USDT
        to_lock = Money.from_float(50.0)
        success = account.lock_funds(AssetType.USDT, to_lock)

        if success:
            print(f"✅ Locked ${to_lock.amount} USDT")
            usdt_bal = account.get_asset_balance(AssetType.USDT)
            if usdt_bal:
                print(f"   Free after lock: ${usdt_bal.free.amount}")
                print(f"   Locked after lock: ${usdt_bal.locked.amount}")

            # Desbloquear $30 USDT
            to_unlock = Money.from_float(30.0)
            unlock_success = account.unlock_funds(AssetType.USDT, to_unlock)

            if unlock_success:
                print(f"✅ Unlocked ${to_unlock.amount} USDT")
                usdt_bal = account.get_asset_balance(AssetType.USDT)
                if usdt_bal:
                    print(f"   Free after unlock: ${usdt_bal.free.amount}")
                    print(f"   Locked after unlock: ${usdt_bal.locked.amount}")
            else:
                print("❌ Failed to unlock funds")
        else:
            print("❌ Failed to lock funds")

        # Test 4: Account summary
        print("\n📊 Test 4: Account Summary")
        summary = account.get_account_summary()

        print("✅ Account Summary:")
        for key, value in summary.items():
            print(f"   {key}: {value}")

        print("\n🎯 Account Models test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Account Models test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_account_repository():
    """Test básico del repositorio de cuentas"""
    print("\n🗃️ Testing Account Repository...")

    try:
        from infrastructure.adapters.data.file_account_repository import (
            FileAccountRepository,
        )
        from domain.models.account import AccountAggregate

        # Crear repositorio
        repo = FileAccountRepository()
        print("✅ FileAccountRepository created")

        # Crear cuenta de prueba
        test_account = AccountAggregate.create_default()
        test_account.account_id = "repo_simple_test"

        # Guardar cuenta
        await repo.save_account(test_account)
        print("✅ Account saved to repository")

        # Recuperar cuenta
        retrieved = await repo.get_account("repo_simple_test")

        if retrieved:
            print(f"✅ Account retrieved: {retrieved.account_id}")
            print(f"   Initial Balance: ${retrieved.initial_balance_usdt.amount}")
        else:
            print("❌ Failed to retrieve account")
            return False

        # Test balance changes
        print("\n📈 Test: Balance Changes")

        from domain.models.account import BalanceChange, TransactionType, AssetType

        # Crear cambio de balance
        balance_change = BalanceChange(
            asset=AssetType.USDT,
            amount=Decimal("100.0"),
            transaction_type=TransactionType.DEPOSIT,
            description="Test deposit",
            related_position_id="test_pos_789",
        )

        # Agregar cambio de balance
        await repo.add_balance_change("repo_simple_test", balance_change)
        print("✅ Balance change added")

        # Obtener cambios
        changes = await repo.get_balance_changes("repo_simple_test", limit=10)
        print(f"✅ Retrieved {len(changes)} balance changes")

        for i, change in enumerate(changes[:3]):  # Mostrar primeros 3
            print(f"   Change {i+1}: {change.description} ${change.amount}")

        print("\n🎯 Account Repository test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Account Repository test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_balance_calculator():
    """Test del balance calculator"""
    print("\n🧮 Testing Balance Calculator...")

    try:
        from infrastructure.adapters.domain.balance_calculator import (
            SimpleBalanceCalculator,
        )
        from domain.models.account import AssetType, AccountAggregate
        from domain.models.position import Money

        calculator = SimpleBalanceCalculator()

        # Crear cuenta con balances conocidos
        account = AccountAggregate.create_default()
        account.account_id = "calc_test"

        # Definir precios
        prices = {
            AssetType.USDT: Money.from_float(1.0),
            AssetType.DOGE: Money.from_float(0.085),
        }

        # Calcular balances
        total_balance, current_balance = await calculator.calculate_balances(
            account, prices
        )

        print(f"✅ Balance calculation:")
        print(f"   Total Balance: ${total_balance.amount}")
        print(f"   Current Balance: ${current_balance.amount}")

        # Test validación de balance suficiente
        required = Money.from_float(50.0)
        has_sufficient = await calculator.validate_balance_sufficient(account, required)

        print(f"   Has sufficient ${required.amount}: {has_sufficient}")

        print("\n🎯 Balance Calculator test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Balance Calculator test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Starting Account Domain Tests...")

    # Ejecutar tests
    asyncio.run(test_account_models())
    asyncio.run(test_account_repository())
    asyncio.run(test_balance_calculator())

    print("\n🏁 All Account Domain tests completed!")
