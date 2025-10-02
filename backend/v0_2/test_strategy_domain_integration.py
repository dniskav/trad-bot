#!/usr/bin/env python3
"""
Strategy Domain Integration Test
Test para verificar la integración completa del Strategy Domain
"""

import asyncio
import sys
import os
from datetime import datetime

# Agregar paths para imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from infrastructure.di_configuration import create_production_container
from application.services.strategy_service import StrategyApplicationService
from domain.models.strategy import (
    StrategyConfig,
    IndicatorConfig,
    SignalConfig,
    SignalCondition,
    IndicatorType,
    SignalType,
)


async def test_strategy_domain_integration():
    print("\n🚀 Testing Strategy Domain Integration...")

    try:
        # === SETUP: Configurar DI Container ===
        print("\n📋 Step 1: Setting up DI Container")
        container = create_production_container()
        print("✅ DI Container configured successfully")

        # === TEST: Resolver StrategyApplicationService ===
        print("\n📋 Step 2: Resolving StrategyApplicationService")
        strategy_service = await container.resolve_service(StrategyApplicationService)

        if strategy_service:
            print("✅ StrategyApplicationService resolved successfully")
            print(f"   Service type: {type(strategy_service).__name__}")
        else:
            print("❌ Failed to resolve StrategyApplicationService")
            return False

        # === TEST: Crear configuración de estrategia ===
        print("\n📋 Step 3: Creating Strategy Configuration")

        # Crear indicadores
        indicators = [
            IndicatorConfig(
                name="sma_20",
                indicator_type=IndicatorType.SMA,
                params={"period": 20},
                enabled=True,
                weight=1.0,
            ),
            IndicatorConfig(
                name="rsi_14",
                indicator_type=IndicatorType.RSI,
                params={"period": 14},
                enabled=True,
                weight=1.0,
            ),
        ]

        # Crear señales
        signals = [
            SignalConfig(
                name="buy_signal",
                signal_type=SignalType.BUY,
                conditions=[
                    SignalCondition(indicator="sma_20", operator=">", value=0.08),
                    SignalCondition(indicator="rsi_14", operator="<", value=70),
                ],
                logic_type="AND",
                enabled=True,
                min_confidence=0.6,
            )
        ]

        strategy_config = StrategyConfig(
            name="test_hexagonal_strategy",
            description="Test strategy for hexagonal architecture",
            symbol="DOGEUSDT",
            timeframe="1m",
            indicators=indicators,
            signals=signals,
            enabled=True,
        )

        print("✅ Strategy configuration created")

        # === TEST: Crear estrategia ===
        print("\n📋 Step 4: Creating Strategy Instance")

        new_strategy = await strategy_service.create_strategy(strategy_config)

        if new_strategy:
            print(f"✅ Strategy created successfully")
            print(f"   Strategy ID: {new_strategy.strategy_id}")
            print(f"   Name: {new_strategy.config.name}")
            print(f"   Status: {new_strategy.status.value}")
        else:
            print("❌ Failed to create strategy")
            return False

        # === TEST: Iniciar estrategia ===
        print("\n📋 Step 5: Starting Strategy")

        start_success = await strategy_service.start_strategy(new_strategy.strategy_id)

        if start_success:
            print("✅ Strategy started successfully")
        else:
            print("❌ Failed to start strategy")
            return False

        # === TEST: Generar señal ===
        print("\n📋 Step 6: Generating Signal")

        market_data = {
            "symbol": "DOGEUSDT",
            "current_price": 0.085,
            "service_name": "price_monitor",
            "volume": 1000000,
            "timestamp": datetime.now().isoformat(),
        }

        signal = await strategy_service.generate_signal(
            new_strategy.strategy_id, market_data
        )

        if signal:
            print("✅ Signal generated successfully")
            print(f"   Signal Type: {signal.signal_type.value}")
            print(f"   Confidence: {signal.confidence}")
            print(f"   Reasoning: {signal.reasoning[:50]}...")
            print(f"   Signal Strength: {signal.signal_strength.value}")
        else:
            print("ℹ️ No signal generated (conditions not met)")

        # === TEST: Obtener performance ===
        print("\n📋 Step 7: Getting Strategy Performance")

        perf_data = await strategy_service.get_strategy_performance(
            new_strategy.strategy_id
        )

        print("✅ Performance data retrieved:")
        for key, value in perf_data.items():
            print(f"   {key}: {value}")

        # === TEST: Obtener resumen general ===
        print("\n📋 Step 8: Getting All Strategies Summary")

        summary = await strategy_service.get_all_strategies_summary()

        print("✅ All strategies summary:")
        print(f"   Total strategies: {summary.get('total_strategies', 0)}")
        print(
            f"   Active strategies: {summary.get('global_metrics', {}).get('active_strategies', 0)}"
        )

        # === TEST: Health Check ===
        print("\n📋 Step 9: Running Health Check")

        health_report = await strategy_service.run_strategy_health_check()

        print("✅ Health check completed:")
        print(f"   Strategies checked: {len(health_report)}")

        for strategy_id, health_data in health_report.items():
            print(f"   Strategy {strategy_id}:")
            print(f"     Healthy: {health_data.get('healthy', False)}")
            print(f"     Safe: {health_data.get('safe', False)}")

        # === TEST: Parar estrategia ===
        print("\n📋 Step 10: Stopping Strategy")

        stop_success = await strategy_service.stop_strategy(new_strategy.strategy_id)

        if stop_success:
            print("✅ Strategy stopped successfully")
        else:
            print("❌ Failed to stop strategy")

        print("\n🎯 Strategy Domain Integration Test COMPLETED!")
        return True

    except Exception as e:
        print(f"\n❌ Strategy Domain Integration Test FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_strategy_services_individually():
    print("\n🔧 Testing Individual Strategy Services...")

    try:
        container = create_production_container()

        # Test IndicatorService
        print("\n📊 Testing IndicatorService")
        from infrastructure.adapters.domain.indicator_service import IndicatorService

        indicator_service = IndicatorService()

        market_data = {
            "current_price": 0.085,
            "prices": [0.084, 0.085, 0.086, 0.084, 0.085] * 20,
        }

        result = await indicator_service.calculate_indicator(
            "SMA", {"period": 5}, market_data
        )

        print(f"✅ SMA calculation result: {result}")

        # Test SignalEvaluatorService
        print("\n🎯 Testing SignalEvaluatorService")
        from infrastructure.adapters.domain.signal_evaluator_service import (
            SignalEvaluatorService,
        )

        evaluator_service = SignalEvaluatorService()

        indicators_data = {
            "sma_20": {"type": "SMA", "value": 0.085, "trend": "bullish"},
            "rsi_14": {"type": "RSI", "value": 65, "status": "neutral"},
        }

        signal_config = SignalConfig(
            name="test_signal",
            signal_type=SignalType.BUY,
            conditions=[
                SignalCondition(indicator="sma_20", operator=">", value=0.08),
                SignalCondition(indicator="rsi_14", operator="<", value=70),
            ],
            enabled=True,
        )

        eval_result = await evaluator_service.evaluate_single_signal(
            signal_config, indicators_data, market_data
        )

        if eval_result:
            print(f"✅ Signal evaluation result: {eval_result.signal_type.value}")
            print(f"   Confidence: {eval_result.confidence}")
        else:
            print("ℹ️ No signal generated")

        print("\n🎯 Individual Services Test COMPLETED!")
        return True

    except Exception as e:
        print(f"\n❌ Individual Services Test FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    print("🚀 Starting Strategy Domain Integration Tests...")

    # Test principal de integración
    main_test_passed = await test_strategy_domain_integration()

    # Test de servicios individuales
    individual_test_passed = await test_strategy_services_individually()

    print("\n🏁 All Strategy Domain Tests Completed!")
    print(
        f"   Main Integration Test: {'✅ PASSED' if main_test_passed else '❌ FAILED'}"
    )
    print(
        f"   Individual Services Test: {'✅ PASSED' if individual_test_passed else '❌ FAILED'}"
    )

    if main_test_passed and individual_test_passed:
        print("\n🎉 ALL TESTS PASSED! Strategy Domain is fully functional!")
    else:
        print("\n⚠️ Some tests failed. Check the logs above.")


if __name__ == "__main__":
    asyncio.run(main())
