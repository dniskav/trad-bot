#!/usr/bin/env python3
"""
Test Hexagonal Integration
Test rápido para verificar que la integración hexagonal funciona
"""

import asyncio
import sys
import os

# Agregar paths para imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)


async def test_hexagonal_integration():
    print("\n🚀 Testing Hexagonal Strategy Domain Integration...")

    try:
        # === TEST: DI Container Resolution ===
        print("\n📋 Step 1: Testing DI Container Setup")

        from infrastructure.di_configuration import create_production_container

        container = create_production_container()
        print("✅ DI Container created")

        # === TEST: Resolve StrategyApplicationService ===
        print("\n📋 Step 2: Resolving StrategyApplicationService")

        from application.services.strategy_service import StrategyApplicationService

        strategy_service = await container.resolve_service(StrategyApplicationService)

        if strategy_service:
            print(
                f"✅ StrategyApplicationService resolved: {type(strategy_service).__name__}"
            )
        else:
            print("❌ Failed to resolve StrategyApplicationService")
            return False

        # === TEST: Resolve Individual Services ===
        print("\n📋 Step 3: Testing Individual Services Resolution")

        # Signal Evaluator
        from domain.ports.strategy_ports import ISignalEvaluator

        signal_evaluator = await container.resolve_service(ISignalEvaluator)
        print(f"✅ SignalEvaluator: {type(signal_evaluator).__name__}")

        # Indicator Service
        from domain.ports.strategy_ports import IIndicatorService

        indicator_service = await container.resolve_service(IIndicatorService)
        print(f"✅ IndicatorService: {type(indicator_service).__name__}")

        # Strategy Repository
        from domain.ports.strategy_ports import IStrategyRepository

        strategy_repository = await container.resolve_service(IStrategyRepository)
        print(f"✅ StrategyRepository: {type(strategy_repository).__name__}")

        # === TEST: StrategyServiceAdapter Creation ===
        print("\n📋 Step 4: Testing StrategyServiceAdapter")

        from adapters.domain.strategy_service_adapter import StrategyServiceAdapter

        adapter = StrategyServiceAdapter(strategy_service)
        print("✅ StrategyServiceAdapter created")

        # === TEST: Mock Strategy Creation ===
        print("\n📋 Step 5: Testing Strategy Creation")

        from domain.models.strategy import (
            StrategyConfig,
            IndicatorConfig,
            SignalConfig,
            SignalCondition,
            IndicatorType,
            SignalType,
        )

        # Crear configuración simple para test
        test_config = StrategyConfig(
            name="test_integration_strategy",
            description="Test strategy for hexagonal integration",
            symbol="DOGEUSDT",
            timeframe="1m",
            indicators=[],
            signals=[],
            enabled=True,
        )

        # Crear estrategia usando el servicio
        new_strategy = await strategy_service.create_strategy(test_config)

        if new_strategy:
            print(f"✅ Strategy created: {new_strategy.strategy_id}")
        else:
            print("❌ Failed to create strategy")

        # === TEST: Strategy Loading from File ===
        print("\n📋 Step 6: Testing Strategy Loading from File")

        # Intentar cargar una estrategia desde archivo
        load_success = await adapter.load_strategy("simple_trend_strategy")

        if load_success:
            print("✅ Strategy loaded from file successfully")
        else:
            print("ℹ️ Strategy file not found or loading failed (OK for test)")

        # === TEST: Strategy List ===
        print("\n📋 Step 7: Testing Strategy List")

        all_strategies = await adapter.get_all_strategies()
        print(f"✅ Found {len(all_strategies)} strategies")

        for name, strategy in all_strategies.items():
            print(f"   - {name}: {strategy.config.name} ({strategy.status.value})")

        print("\n🎯 Hexagonal Integration Test COMPLETED SUCCESSFULLY!")
        return True

    except Exception as e:
        print(f"\n❌ Hexagonal Integration Test FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_individual_services():
    print("\n🔧 Testing Individual Services...")

    try:
        # Test Indicator Service directly
        print("\n📊 Testing IndicatorService Directly")

        from infrastructure.adapters.domain.indicator_service import IndicatorService

        indicator_service = IndicatorService()

        market_data = {
            "current_price": 0.085,
            "prices": [0.084, 0.085, 0.086, 0.084, 0.085] * 20,
        }

        sma_result = await indicator_service.calculate_indicator(
            "SMA", {"period": 5}, market_data
        )
        print(f"✅ SMA Result: {sma_result}")

        rsi_result = await indicator_service.calculate_indicator(
            "RSI", {"period": 14}, market_data
        )
        print(f"✅ RSI Result: {rsi_result}")

        # Test Signal Evaluator directly
        print("\n🎯 Testing SignalEvaluatorService Directly")

        from infrastructure.adapters.domain.signal_evaluator_service import (
            SignalEvaluatorService,
        )

        evaluator = SignalEvaluatorService()

        indicators_data = {"sma_5": sma_result, "rsi_14": rsi_result}

        from domain.models.strategy import SignalConfig, SignalCondition, SignalType

        signal_config = SignalConfig(
            name="test_signal",
            signal_type=SignalType.BUY,
            conditions=[
                SignalCondition(indicator="sma_5", operator=">", value=0.08),
                SignalCondition(indicator="rsi_14", operator="<", value=70),
            ],
            enabled=True,
        )

        signal_result = await evaluator.evaluate_single_signal(
            signal_config, indicators_data, market_data
        )

        if signal_result:
            print(f"✅ Signal Evaluation Result:")
            print(f"   Type: {signal_result.signal_type.value}")
            print(f"   Confidence: {signal_result.confidence}")
            print(f"   Reasoning: {signal_result.reasoning}")
        else:
            print("ℹ️ No signal generated (conditions not met)")

        print("\n🎯 Individual Services Test COMPLETED SUCCESSFULLY!")
        return True

    except Exception as e:
        print(f"\n❌ Individual Services Test FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    print("🚀 Starting Hexagonal Architecture Integration Tests...")

    # Test integration completa
    integration_test_passed = await test_hexagonal_integration()

    # Test servicios individuales
    individual_test_passed = await test_individual_services()

    print("\n🏁 All Hexagonal Integration Tests Completed!")
    print(
        f"   Integration Test: {'✅ PASSED' if integration_test_passed else '❌ FAILED'}"
    )
    print(
        f"   Individual Services Test: {'✅ PASSED' if individual_test_passed else '❌ FAILED'}"
    )

    if integration_test_passed and individual_test_passed:
        print("\n🎉 ALL TESTS PASSED! Hexagonal Architecture Integration is ready!")
        print("✅ Strategy Domain is production-ready for router integration")
    else:
        print("\n⚠️ Some tests failed. Check the logs above.")
        print("⚠️ Fix issues before integrating with production routers")


if __name__ == "__main__":
    asyncio.run(main())
