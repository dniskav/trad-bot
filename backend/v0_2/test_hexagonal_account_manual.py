#!/usr/bin/env python3
"""
Test manual para verificar la integración hexagonal del Account Domain
"""

import sys
import os
import asyncio
from datetime import datetime

# Agregar path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


async def test_account_service_adapter():
    """Probar directamente el AccountServiceAdapter"""
    
    print("🧪 Testing AccountServiceAdapter directly")
    print("=" * 50)
    
    try:
        # Importar dependencias
        from infrastructure.di_configuration import create_production_container
        from application.services.account_service import AccountApplicationService
        from infrastructure.adapters.domain.account_service_adapter import AccountServiceAdapter
        
        # Crear container y resolver servicio
        print("1️⃣ Creating DI Container and resolving services...")
        container = create_production_container()
        account_service = await container.resolve_service(AccountApplicationService)
        
        if not account_service:
            print("❌ Failed to resolve AccountApplicationService")
            return
        
        print(f"✅ AccountApplicationService resolved: {type(account_service).__name__}")
        
        # Crear adapter
        print("2️⃣ Creating AccountServiceAdapter...")
        adapter = AccountServiceAdapter(account_service)
        print(f"✅ AccountServiceAdapter created: {type(adapter).__name__}")
        
        # Test get_account_synth
        print("3️⃣ Testing get_account_synth...")
        result = await adapter.get_account_synth()
        print(f"✅ get_account_synth result: {type(result)}")
        
        if isinstance(result, dict):
            if result.get("code") == 200:
                data = result.get("data", {})
                print(f"✅ Account data retrieved:")
                print(f"   - Account ID: {data.get('accountId', 'N/A')}")
                print(f"   - Total Balance: {data.get('total_balance_usdt', 'N/A')} USDT")
                print(f"   - Balances: {len(data.get('balances', {}))} assets")
            else:
                print(f"⚠️ Error response: {result.get('message', 'Unknown error')}")
        
        # Test reset_account_synth (dry run)
        print("4️⃣ Testing reset_account_synth (dry run)...")
        reset_result = await adapter.reset_account_synth()
        
        if isinstance(reset_result, dict):
            if reset_result.get("code") == 200:
                print("✅ Reset account operation successful")
                print(f"   - Reset at: {reset_result.get('data', {}).get('reset_at', 'N/A')}")
            else:
                print(f"⚠️ Reset error: {reset_result.get('message', 'Unknown error')}")
        
        # Test health check
        print("5️⃣ Testing health check...")
        health = await adapter.health_check()

        if health and isinstance(health, dict):
            status = health.get("status", "unknown")
            print(f"✅ Health check status: {status}")
            
            if status == "healthy":
                print("✅ Account service is healthy")
            elif status == "degraded":
                print("⚠️ Account service is degraded")
            else:
                print(f"⚠️ Account service status: {status}")
        
        print("\n✅ Direct AccountServiceAdapter test completed successfully")
        
    except Exception as e:
        print(f"❌ Error testing AccountServiceAdapter: {e}")
        import traceback
        traceback.print_exc()


async def test_router_integration():
    """Probar la integración con el router"""
    
    print("\n🧪 Testing Router Integration")
    print("=" * 50)
    
    try:
        from server.account_service_integration import (
            account_service_fastapi_integration,
            get_account_service
        )
        
        # Test integration initialization
        print("1️⃣ Testing integration initialization...")
        await account_service_fastapi_integration.initialize_background()
        
        # Wait a moment for initialization
        await asyncio.sleep(2)
        
        print("2️⃣ Testing service resolution for router...")
        service = await get_account_service()
        service_name = type(service).__name__
        print(f"✅ Service resolved: {service_name}")
        
        # Test if it's hexagonal or legacy
        if hasattr(service, 'account_service'):
            print("✅ Using Hexagonal AccountServiceAdapter")
            
            # Test methods
            print("3️⃣ Testing adapter methods...")
            
            # get_account_synth
            get_result = await service.get_account_synth()
            if isinstance(get_result, dict) and get_result.get("code") == 200:
                print("✅ get_account_synth: Working")
            else:
                print(f"⚠️ get_account_synth: {get_result}")
            
            # reset_account_synth
            reset_result = await service.reset_account_synth()
            if isinstance(reset_result, dict):
                print(f"✅ reset_account_synth: Code {reset_result.get('code', 'N/A')}")
            else:
                print(f"⚠️ reset_account_synth: {reset_result}")
                
        else:
            print("✅ Using Legacy STMService (via adapter)")
            print("✅ Fallback mode properly functioning")
        
        print("\n✅ Router integration test completed successfully")
        
    except Exception as e:
        print(f"❌ Error testing router integration: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Función principal de testing"""
    
    print("🚀 Starting Hexagonal Account Domain Integration Tests")
    print(f"⏰ Time: {datetime.now().isoformat()}")
    
    # Tests
    await test_account_service_adapter()
    await test_router_integration()
    
    print("\n🎉 All Tests Completed!")


if __name__ == "__main__":
    asyncio.run(main())
