#!/usr/bin/env python3
"""
Dependency Injection Container
Container centralizado para gestión de dependencias siguiendo Hexagonal Architecture
"""

import asyncio
import inspect
import threading
from typing import Dict, Type, TypeVar, Callable, Any, Optional, Union
from datetime import datetime


T = TypeVar('T')


class DIContainer:
    """Container de inyección de dependencias"""

    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        self._lifetime = {}  # 'singleton' | 'transient' | 'scoped'
        self._lock = threading.Lock()
        self._container_id = f"di_container_{datetime.now().timestamp()}"

    def register_singleton(self, interface_type: Type[T], implementation_type: Type[T]) -> None:
        """Registrar servicio como singleton"""
        with self._lock:
            self._services[interface_type] = implementation_type
            self._lifetime[interface_type] = 'singleton'
            print(f"📦 Registered singleton: {interface_type.__name__} -> {implementation_type.__name__}")

    def register_transient(self, interface_type: Type[T], implementation_type: Type[T]) -> None:
        """Registrar servicio como transient (nueva instancia cada vez)"""
        with self._lock:
            self._services[interface_type] = implementation_type
            self._lifetime[interface_type] = 'transient'
            print(f"📦 Registered transient: {interface_type.__name__} -> {implementation_type.__name__}")

    def register_scoped(self, interface_type: Type[T], implementation_type: Type[T]) -> None:
        """Registrar servicio como scoped (una instancia por request/session)"""
        with self._lock:
            self._services[interface_type] = implementation_type
            self._lifetime[interface_type] = 'scoped'
            print(f"📦 Registered scoped: {interface_type.__name__} -> {implementation_type.__name__}")

    def register_factory(self, interface_type: Type[T], factory_function: Callable[..., T]) -> None:
        """Registrar factory function para crear instancia"""
        with self._lock:
            self._factories[interface_type] = factory_function
            self._lifetime[interface_type] = 'factory'
            print(f"📦 Registered factory: {interface_type.__name__}")

    def register_instance(self, interface_type: Type[T], instance: T) -> None:
        """Registrar instancia específica (pre-construida)"""
        with self._lock:
            self._singletons[interface_type] = instance
            self._lifetime[interface_type] = 'singleton'
            print(f"📦 Registered instance: {interface_type.__name__}")

    def get(self, interface_type: Type[T]) -> T:
        """Obtener instancia resuelta del tipo especificado"""
        return self._resolve_type(interface_type)

    async def get_async(self, interface_type: Type[T]) -> T:
        """Obtener instancia resuelta del tipo especificado (async)"""
        return await self._resolve_type_async(interface_type)

    def _resolve_type(self, interface_type: Type[T]) -> T:
        """Resolver tipo síncronamente"""
        if interface_type in self._singletons:
            return self._singletons[interface_type]

        if interface_type in self._services:
            implementation_type = self._services[interface_type]
            lifetime = self._lifetime.get(interface_type, 'transient')

            if lifetime == 'singleton':
                if interface_type not in self._singletons:
                    instance = self._create_instance(implementation_type)
                    self._singletons[interface_type] = instance
                return self._singletons[interface_type]

            elif lifetime in ['transient', 'scoped']:
                return self._create_instance(implementation_type)

        if interface_type in self._factories:
            factory_func = self._factories[interface_type]
            return factory_func(self)

        raise ValueError(f"Service {interface_type.__name__} not registered in container")

    async def _resolve_type_async(self, interface_type: Type[T]) -> T:
        """Resolver tipo de manera asíncrona"""
        if interface_type in self._singletons:
            return self._singletons[interface_type]

        if interface_type in self._services:
            implementation_type = self._services[interface_type]
            lifetime = self._lifetime.get(interface_type, 'transient')

            if lifetime == 'singleton':
                if interface_type not in self._singletons:
                    instance = await self._create_instance_async(implementation_type)
                    self._singletons[interface_type] = instance
                return self._singletons[interface_type]

            elif lifetime in ['transient', 'scoped']:
                return await self._create_instance_async(implementation_type)

        if interface_type in self._factories:
            factory_func = self._factories[interface_type]
            return factory_func(self)

        raise ValueError(f"Service {interface_type.__name__} not registered in container")

    def _create_instance(self, implementation_type: Type[T]) -> T:
        """Crear instancia usando inyección de dependencias"""
        try:
            # Verificar si es async init
            if inspect.iscoroutinefunction(implementation_type.__init__):
                # Para tipos async, crear wrapper temporal
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Si estamos en un loop, necesitamos usar create_task
                    return self._create_instance_sync_fallback(implementation_type)
                else:
                    return loop.run_until_complete(self._create_instance_async(implementation_type))
            else:
                return self._create_instance_sync(implementation_type)
        except Exception as e:
            print(f"❌ Error creating instance of {implementation_type.__name__}: {e}")
            raise

    def _create_instance_sync(self, implementation_type: Type[T]) -> T:
        """Crear instancia síncrona simple"""
        constructor = implementation_type.__init__
        signature = inspect.signature(constructor)

        # Excluir 'self'
        params = {name: param for name, param in signature.parameters.items() if name != 'self'}
        kwargs = {}

        for param_name, param in params.items():
            if param.annotation != param.empty:
                kwargs[param_name] = self._resolve_type(param.annotation)

        return implementation_type(**kwargs)

    def _create_instance_sync_fallback(self, implementation_type: Type[T]) -> T:
        """Fallback para crear instancia sin resolver dependencias"""
        try:
            # Intentar sin dependencias primero
            return implementation_type()
        except Exception:
            # Si falla, intentar resolver manualmente las dependencias comunes
            return self._create_instance_manual_resolve(implementation_type)

    def _create_instance_manual_resolve(self, implementation_type: Type[T]) -> T:
        """Resolver manualmente dependencias comunes"""
        # Patrones comunes para repositorios/servicios
        if "Repository" in implementation_type.__name__:
            # Los repositorios suelen necesitar data_dir
            return implementation_type(data_dir="./data")
        elif "Service" in implementation_type.__name__:
            # Los servicios pueden necesitar dependencies básicas
            return implementation_type()
        else:
            # Por defecto, sin parámetros
            return implementation_type()

    async def _create_instance_async(self, implementation_type: Type[T]) -> T:
        """Crear instancia de manera asíncrona con inyección"""
        constructor = implementation_type.__init__
        signature = inspect.signature(constructor)

        # Excluir 'self'
        params = {name: param for name, param in signature.parameters.items() if name != 'self'}
        kwargs = {}

        for param_name, param in params.items():
            if param.annotation != param.empty:
                if inspect.iscoroutinefunction(self._resolve_type_async):
                    kwargs[param_name] = await self._resolve_type_async(param.annotation)
                else:
                    kwargs[param_name] = self._resolve_type(param.annotation)

        return implementation_type(**kwargs)

    def register_module(self, module_config: Dict[Type, Type]) -> None:
        """Registrar módulo completo de dependencias"""
        print(f"📦 Registering module with {len(module_config)} services...")
        for interface_type, implementation_type in module_config.items():
            self.register_transient(interface_type, implementation_type)

    def get_registered_services(self) -> Dict[str, str]:
        """Obtener lista de servicios registrados"""
        services = {}
        for interface_type, implementation_type in self._services.items():
            lifetime = self._lifetime.get(interface_type, 'transient')
            services[interface_type.__name__] = f"{implementation_type.__name__} ({lifetime})"
        return services

    def contains_service(self, interface_type: Type[T]) -> bool:
        """Verificar si servicio está registrado"""
        return (interface_type in self._services or 
                interface_type in self._factories or 
                interface_type in self._singletons)

    async def shutdown(self) -> None:
        """Cerrar container y limpiar recursos"""
        print(f"🛑 Shutting down DI Container {self._container_id}")
        # Aquí se podrían llamar métodos de cleanup en singletons que lo necesiten
        self._singletons.clear()
        print("✅ DI Container shutdown complete")


# Global container instance
_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """Obtener instancia global del container"""
    global _container
    if _container is None:
        _container = DIContainer()
    return _container


def register_services(container: DIContainer) -> DIContainer:
    """Configurar servicios específicos de la aplicación"""
    
    # Aquí se registrarán los servicios una vez que tengamos las implementaciones
    # Por ahora dejamos comentado para referencia
    
    # Ejemplo de registro futuro:
    
    # === TRADING DOMAIN ===
    # container.register_transient(IPositionRepository, FilePositionRepository)
    # container.register_singleton(IMarketDataProvider, BinanceMarketDataAdapter)
    # container.register_transient(ICommissionCalculator, BinanceCommissionCalculator)
    
    # === STRATEGY DOMAIN ===
    # container.register_transient(IStrategyEngine, StrategyEngine)
    # container.register_singleton(IIndicatorService, TechnicalIndicatorService)
    # container.register_transient(ISignalEvaluator, SignalEvaluator)
    
    # === ACCOUNT DOMAIN ===
    # container.register_singleton(IAccountRepository, FileAccountRepository)
    # container.register_transient(IBalanceCalculator, BalanceCalculator)
    # container.register_transient(IAccountValidator, AccountValidator)
    
    # === COMMUNICATION DOMAIN ===
    # container.register_singleton(IEventPublisher, DomainEventPublisher)
    # container.register_singleton(IWebSocketManager, WebSocketManager)
    # container.register_transient(IExternalNotificationService, STMNotificationService)
    
    print(f"🚀 DI Container configured with {len(container._services)} service registrations")
    return container


if __name__ == "__main__":
    # Test del container
    container = DIContainer()
    
    # Test básico
    class TestService:
        def __init__(self):
            self.id = "test_service"
    
    class TestInterface:
        pass
    
    container.register_singleton(TestInterface, TestService)
    instance = container.get(TestInterface)
    print(f"✅ Container test successful: {instance.id}")
