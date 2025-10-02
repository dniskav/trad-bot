#!/usr/bin/env python3
"""
Test de integración para Account Domain hexagonal
"""

import sys
import os
import asyncio
from datetime import datetime

# Agregar path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server.account_service_integration import (
    account_service_fastapi_integration,
    get_account_service,
    account_health_check,
)


async def test_account_integration():
    """Probar la integración completa de Account"""

    print("🧪 Testing Account Service Integration")
    print("=" * 50)

    # Test 1: Health check
    print("1️⃣ Testing Health Check...")
    try:
        health_data = await account_health_check()
        print(f"✅ Health Check: {health_data}")
    except Exception as e:
        print(f"❌ Health Check Error: {e}")

    # Test 2: Service resolution
    print("\n2️⃣ Testing Service Resolution...")
    try:
        account_service = await get_account_service()
        service_name = type(account_service).__name__
        print(f"✅ Service Resolved: {service_name}")

        # Verificar métodos esperados
        required_methods = ["get_account_synth", "reset_account_synth"]
        for method in required_methods:
            if hasattr(account_service, method):
                print(f"✅ Method {method}: Available")
            else:
                print(f"❌ Method {method}: Missing")

    except Exception as e:
        print(f"❌ Service Resolution Error: {e}")

    # Test 3: Mock account operation
    print("\n3️⃣ Testing Account Operations...")
    try:
        account_service = await get_account_service()

        # Test get_account_synth
        if hasattr(account_service, "get_account_synth"):
            print("🔍 Testing get_account_synth...")
            result = await account_service.get_account_synth()
            print(f"✅ get_account_synth result: {type(result)}")

            if isinstance(result, dict):
                if result.get("code") == 200:
                    print("✅ Account data retrieved successfully")
                else:
                    print(f"⚠️ Account data issue: {result.get('message', 'Unknown')}")
            else:
                print(f"⚠️ Unexpected result type: {type(result)}")

        # Test reset_account_synth (sin ejecutar realmente)
        if hasattr(account_service, "reset_account_synth"):
            print("🔍 Testing reset_account_synth (dry run)...")
            # No ejecutar realmente para no afectar datos
            print("✅ reset_account_synth method available")

    except Exception as e:
        print(f"❌ Account Operations Error: {e}")

    # Test 4: Integration status
    print("\n4️⃣ Testing Integration Status...")
    try:
        health_data = await account_health_check()
        integration = health_data.get("account_integration", {})

        print(f"Status: {integration.get('status', 'unknown')}")
        print(f"Hexagonal: {integration.get('hexagonal_available', False)}")
        print(f"Legacy: {integration.get('legacy_fallback_available', False)}")

        if integration.get("hexagonal_available"):
            print("✅ Hexagonal Account Domain is operational")
        elif integration.get("legacy_fallback_available"):
            print("✅ Legacy STM Service fallback is operational")
        else:
            print("❌ No account services available")

    except Exception as e:
        print(f"❌ Integration Status Error: {e}")

    print("\n" + "=" * 50)
    print("🎯 Account Integration Test Complete")


async def test_di_container_resolution():
    """Probar resolución del DI Container para Account Domain"""

    print("\n🧪 Testing DI Container Resolution for Account Domain")
    print("=" * 50)

    try:
        from infrastructure.di_configuration import create_production_container
        from application.services.account_service import AccountApplicationService

        # Crear container
        print("1️⃣ Creating DI Container...")
        container = create_production_container()
        print("✅ DI Container created")

        # Resolver AccountApplicationService
        print("2️⃣ Resolving AccountApplicationService...")
        account_service = await container.resolve_service(AccountApplicationService)

        if account_service:
            print(
                f"✅ AccountApplicationService resolved: {type(account_service).__name__}"
            )

            # Verificar métodos esperados
            expected_methods = [
                "get_account_details",
                "process_balance_changes",
                "create_initial_balance_changes",
                "get_account_performance",
            ]

            for method in expected_methods:
                if hasattr(account_service, method):
                    print(f"✅ Method {method}: Available")
                else:
                    print(f"❌ Method {method}: Missing")

        else:
            print("❌ Failed to resolve AccountApplicationService")

    except Exception as e:
        print(f"❌ DI Container Resolution Error: {e}")


async def main():
    """Función principal de testing"""

    print("🚀 Starting Account Domain Integration Tests")
    print(f"⏰ Time: {datetime.now().isoformat()}")

    # Tests
    await test_account_integration()
    await test_di_container_resolution()

    print("\n🎉 All Tests Completed!")


if __name__ == "__main__":
    asyncio.run(main())
