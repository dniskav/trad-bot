#!/usr/bin/env python3
"""
DI Configuration
Configuración de todas las dependencias para el container DI
"""

from typing import Dict, Any

from .di_container import DIContainer

# Imports de ports (interfaces)
from ..domain.ports.trading_ports import (
    IPositionRepository,
    IOrderRepository,
    IMarketDataProvider,
    ITradingExecutor,
    ICommissionCalculator,
    IExecutionValidator,
    IPositionTracker,
)

from ..domain.ports.strategy_ports import (
    IStrategyEngine,
    IIndicatorService,
    ISignalEvaluator,
    IStrategyRepository,
    IRiskManager,
    IStrategyPerformanceTracker,
)

from ..domain.ports.account_ports import (
    IAccountRepository,
    IBalanceCalculator,
    ICommissionCalculator as IAccountCommissionCalculator,
    IAccountValidator,
    IAccountTransactionHandler,
    IAccountReportGenerator,
    IMarketDataPricer,
)

from ..domain.ports.communication_ports import (
    IEventPublisher,
    IWebSocketManager,
    IExternalNotificationService,
    IMessageQueueAdapter,
    ICacheAdapter,
    ILogger,
    IRateLimiter,
)

# Imports de application services
from ..application.services.trading_service import TradingApplicationService


def configure_trading_domain(container: DIContainer) -> None:
    """Configurar dependencias del dominio de trading"""

    # Por ahora registramos placeholders hasta que tengamos implementaciones
    # Una vez que tengamos los adapters, se registrarán así:

    # === REPOSITORY LAYER ===
    from ..infrastructure.adapters.data.file_position_repository import (
        FilePositionRepository,
    )

    container.register_singleton(IPositionRepository, FilePositionRepository)

    from ..infrastructure.adapters.data.file_order_repository import FileOrderRepository

    container.register_singleton(IOrderRepository, FileOrderRepository)

    # === INFRASTRUCTURE LAYER ===
    from ..infrastructure.adapters.external.binance_market_data_provider import (
        BinanceMarketDataProvider,
    )

    container.register_singleton(IMarketDataProvider, BinanceMarketDataProvider)

    from ..infrastructure.adapters.trading.stm_trading_executor import (
        STMTradingExecutor,
    )

    container.register_transient(ITradingExecutor, STMTradingExecutor)

    # === COMMUNICATION LAYER ===
    from ..infrastructure.adapters.communication.domain_event_publisher import (
        DomainEventPublisher,
    )

    container.register_singleton(IEventPublisher, DomainEventPublisher)

    # === ACCOUNT DOMAIN ADAPTERS ===
    from ..adapters.data.file_account_repository import FileAccountRepository

    container.register_singleton(IAccountRepository, FileAccountRepository)

    from ..adapters.domain.balance_calculator import SimpleBalanceCalculator

    container.register_transient(IBalanceCalculator, SimpleBalanceCalculator)

    from ..adapters.domain.commission_calculator import StandardCommissionCalculator

    container.register_singleton(
        IAccountCommissionCalculator, StandardCommissionCalculator
    )

    from ..adapters.domain.account_validator import StandardAccountValidator

    container.register_transient(IAccountValidator, StandardAccountValidator)

    from ..adapters.domain.transaction_handler import StandardTransactionHandler

    container.register_transient(IAccountTransactionHandler, StandardTransactionHandler)

    from ..adapters.domain.market_data_pricer import BinanceMarketDataPricer

    container.register_singleton(IMarketDataPricer, BinanceMarketDataPricer)

    # === APPLICATION SERVICES ===
    container.register_singleton(
        AccountApplicationService,
        AccountApplicationService,
        [
            IAccountRepository,
            IBalanceCalculator,
            IAccountCommissionCalculator,
            IAccountValidator,
            IAccountTransactionHandler,
            IMarketDataPricer,
            IEventPublisher,
        ],
    )

    # === DOMAIN SERVICES ===
    # from ..domain.services.commission_calculator import BinanceCommissionCalculator
    # container.register_singleton(ICommissionCalculator, BinanceCommissionCalculator)

    # === APPLICATION LAYER ===
    container.register_transient(TradingApplicationService, TradingApplicationService)

    print("🏦 Trading Domain configured")


def configure_strategy_domain(container: DIContainer) -> None:
    """Configurar dependencias del dominio de estrategias"""

    # === STRATEGY REPOSITORY ===
    from ...domain.ports.strategy_ports import IStrategyRepository
    from ..adapters.data.file_strategy_repository import FileStrategyRepository
    container.register_singleton(IStrategyRepository, FileStrategyRepository)

    # === STRATEGY ENGINE (Mock Implementation) ===
    from ...domain.ports.strategy_ports import IStrategyEngine
    from ..adapters.domain.strategy_manager import StrategyManager
    container.register_transient(IStrategyEngine, StrategyManager)

    # === INDICATOR SERVICE ===
    from ...domain.ports.strategy_ports import IIndicatorService
    from ..adapters.domain.indicator_service import IndicatorService
    container.register_transient(IIndicatorService, IndicatorService)

    # === SIGNAL EVALUATOR SERVICE ===
    from ...domain.ports.strategy_ports import ISignalEvaluator
    from ..adapters.domain.signal_evaluator_service import SignalEvaluatorService
    container.register_transient(ISignalEvaluator, SignalEvaluatorService)

    # === RISK MANAGER (Mock Implementation) ===
    from ...domain.ports.strategy_ports import IRiskManager
    class MockRiskManager:
        async def apply_risk_management(self, signal, balance):
            return signal  # Mock: no risk management
    container.register_transient(IRiskManager, MockRiskManager)

    # === PERFORMANCE TRACKER (Mock Implementation) ===
    from ...domain.ports.strategy_ports import IStrategyPerformanceTracker
    class MockPerformanceTracker:
        async def record_signal_generated(self, strategy_id, signal):
            pass  # Mock: no tracking
        async def get_strategy_performance(self, strategy_id):
            return {}
    container.register_transient(IStrategyPerformanceTracker, MockPerformanceTracker)

    # === STRATEGY MANAGER ===
    container.register_singleton("StrategyManager", StrategyManager)

    # === APPLICATION LAYER ===
    from ...domain.ports.communication_ports import IEventPublisher
    from ..application.services.strategy_service import StrategyApplicationService
    container.register_singleton(
        StrategyApplicationService,
        StrategyApplicationService,
        [
            IStrategyEngine,
            IIndicatorService,
            ISignalEvaluator,
            IStrategyRepository,
            IRiskManager,
            IStrategyPerformanceTracker,
            IEventPublisher,
        ],
    )

    print("🤖 Strategy Domain configured")


def configure_account_domain(container: DIContainer) -> None:
    """Configurar dependencias del dominio de cuentas"""

    # === REPOSITORY LAYER ===
    # from ..infrastructure.adapters.data.file_account_repository import FileAccountRepository
    # container.register_singleton(IAccountRepository, FileAccountRepository)

    # === DOMAIN SERVICES ===
    # from ..domain.services.balance_calculator import BalanceCalculator
    # container.register_transient(IBalanceCalculator, BalanceCalculator)

    # === APPLICATION LAYER ===
    # from ..application.services.account_application_service import AccountApplicationService
    # container.register_transient(AccountApplicationService, AccountApplicationService)

    print("💰 Account Domain configured")


def configure_communication_domain(container: DIContainer) -> None:
    """Configurar dependencias del dominio de comunicación"""

    # === EVENT PUBLISHER (Mock Implementation) ===
    from ...domain.ports.communication_ports import IEventPublisher
    
    class MockEventPublisher:
        async def publish_account_event(self, account_id, event_type, data=None):
            print(f"Event: {event_type} for account {account_id}: {data}")
        
        async def publish_strategy_event(self, strategy_id, event_type, data=None):
            print(f"Strategy Event: {event_type} for strategy {strategy_id}: {data}")
            
        async def publish_trading_event(self, event_type, data=None):
            print(f"Trading Event: {event_type}: {data}")
    
    container.register_singleton(IEventPublisher, MockEventPublisher)

    print("📡 Communication Domain configured")


def configure_root_services(container: DIContainer) -> None:
    """Configurar servicios raíz y compartidos"""

    # === SHARED SERVICES ===
    # from ..shared.services.logging_service import AppLogger
    # container.register_singleton(ILogger, AppLogger)

    # === CACHING ===
    # from ..infrastructure.adapters.cache.memory_cache_adapter import MemoryCacheAdapter
    # container.register_singleton(ICacheAdapter, MemoryCacheAdapter)

    print("🔧 Root services configured")


def register_all_dependencies(container: DIContainer) -> DIContainer:
    """
    Registrar todas las dependencias de la aplicación

    Este es el punto central de configuración que conecta todos los dominios
    siguiendo los principios de Clean Architecture.
    """

    print("🚀 Configuring Hexagonal Architecture dependencies...")

    # Configurar cada dominio
    configure_trading_domain(container)
    configure_strategy_domain(container)
    configure_account_domain(container)
    configure_communication_domain(container)
    configure_root_services(container)

    # Verificar configuración
    total_services = (
        len(container._services)
        + len(container._factories)
        + len(container._singletons)
    )
    print(f"✅ Configuration complete: {total_services} services registered")

    # Mostrar servicios registrados (debug)
    if True:  # Set to False in production
        print("\n📋 Registered services:")
        for (
            interface_name,
            implementation_name,
        ) in container.get_registered_services().items():
            print(f"   {interface_name} -> {implementation_name}")

    return container


def create_production_container() -> DIContainer:
    """Crear container configurado para producción"""
    container = DIContainer()
    return register_all_dependencies(container)


def create_test_container() -> DIContainer:
    """Crear container configurado para testing con mocks"""
    container = DIContainer()

    # En testing se registrarían mocks en lugar de implementaciones reales
    print("🧪 Creating TEST container with mocks...")

    # Ejemplo de configuración con mocks para testing:
    # from .test.mocks import MockPositionRepository, MockMarketDataProvider
    # container.register_transient(IPositionRepository, MockPositionRepository)
    # container.register_transient(IMarketDataProvider, MockMarketDataProvider)

    return container


def get_trading_service(container: DIContainer) -> TradingApplicationService:
    """Helper para obtener trading service desde container"""
    return container.get(TradingApplicationService)


if __name__ == "__main__":
    # Test de configuración
    container = create_production_container()

    # Verificar que se puede resolver trading service
    try:
        trading_service = get_trading_service(container)
        print(f"✅ Trading service resolved: {type(trading_service).__name__}")
    except Exception as e:
        print(f"❌ Error resolving trading service: {e}")

    print("\n🎯 DI Configuration test complete!")
