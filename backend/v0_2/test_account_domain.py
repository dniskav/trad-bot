#!/usr/bin/env python3
"""
Test Account Domain Integration
Test simple para verificar que Account Domain funciona
"""

import asyncio
import sys
import os

# Agregar al path para imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from domain.models.account import AccountAggregate
from infrastructure.di_configuration import configure_all_dependencies
from infrastructure.di_container import DIContainer


async def test_account_domain():
    print("🧪 Testing Account Domain...")

    # Inicializar DI Container
    container = DIContainer()
    configure_all_dependencies(container)

    try:
        # Test 1: Crear cuenta
        print("\n📋 Test 1: Create Account")
        account_service = await container.resolve_service(
            AccountAggregate.create_default().__class__
        )

        if hasattr(container, "resolve"):
            account_service = await container.resolve("AccountApplicationService")

        if account_service:
            print("✅ AccountService resolved successfully")
        else:
            print("❌ Failed to resolve AccountService")
            return

        # Test 2: Crear cuenta de prueba
        print("\n💰 Test 2: Create Test Account")
        test_account = AccountAggregate.create_default()
        test_account.account_id = "test_integration"

        print(f"✅ Created account: {test_account.account_id}")
        print(f"   Total Balance: ${test_account.total_balance_usdt.amount}")
        print(f"   Assets: {len(test_account.assets)}")

        # Test 3: Balance operations
        print("\n🔒 Test 3: Balance Operations")

        from domain.models.account import AssetType
        from domain.models.position import Money

        # Bloquear fondos para trading
        usdt_to_lock = Money.from_float(100.0)
        success = test_account.lock_funds(AssetType.USDT, usdt_to_lock)

        if success:
            print(f"✅ Locked ${usdt_to_lock.amount} USDT")

            usdt_balance = test_account.get_asset_balance(AssetType.USDT)
            if usdt_balance:
                print(f"   Free: ${usdt_balance.free.amount}")
                print(f"   Locked: ${usdt_balance.locked.amount}")
        else:
            print("❌ Failed to lock funds")

        # Test 4: Account summary
        print("\n📊 Test 4: Account Summary")
        summary = test_account.get_account_summary()

        print(f"✅ Account Summary:")
        for key, value in summary.items():
            print(f"   {key}: {value}")

        print("\n🎯 Account Domain test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Account Domain test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_account_repository_integration():
    print("\n🗃️ Testing Account Repository Integration...")

    try:
        # Import y test básico
        from infrastructure.adapters.data.file_account_repository import (
            FileAccountRepository,
        )

        repo = FileAccountRepository()
        print("✅ FileAccountRepository initialized")

        # Crear cuenta de prueba
        test_account = AccountAggregate.create_default()
        test_account.account_id = "repo_test_123"

        # Guardar cuenta
        await repo.save_account(test_account)
        print("✅ Account saved to repository")

        # Recuperar cuenta
        retrieved_account = await repo.get_account("repo_test_123")

        if retrieved_account:
            print(f"✅ Account retrieved: {retrieved_account.account_id}")
            print(f"   Balance: ${retrieved_account.total_balance_usdt.amount}")
        else:
            print("❌ Failed to retrieve account")
            return False

        # Test balance changes
        from domain.models.account import BalanceChange, TransactionType, AssetType
        from decimal import Decimal

        balance_change = BalanceChange(
            asset=AssetType.USDT,
            amount=Decimal("50.0"),
            transaction_type=TransactionType.DEPOSIT,
            description="Test deposit",
            related_position_id="test_pos_456",
        )

        await repo.add_balance_change("repo_test_123", balance_change)
        print("✅ Balance change added")

        # Obtener cambios
        changes = await repo.get_balance_changes("repo_test_123", limit=5)
        print(f"✅ Retrieved {len(changes)} balance changes")

        # Estadísticas
        stats = repo.get_account_statistics()
        print(f"✅ Repository statistics: {stats}")

        print("\n🎯 Account Repository integration test successful!")
        return True

    except Exception as e:
        print(f"❌ Account Repository test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    asyncio.run(test_account_domain())
    asyncio.run(test_account_repository_integration())
