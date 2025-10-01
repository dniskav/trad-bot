#!/usr/bin/env python3
"""
Strategies Router
API endpoints for strategy management
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

from ..services.strategy_service import StrategyService
from backend.shared.logger import get_logger

log = get_logger("strategies.router")
router = APIRouter(prefix="/strategies", tags=["strategies"])

# Global strategy service instance (will be injected)
strategy_service_instance: StrategyService = None


def set_strategy_service(service: StrategyService):
    """Set the global strategy service instance"""
    global strategy_service_instance
    strategy_service_instance = service
    log.info(f"Strategy service injected: {service is not None}")


def get_strategy_service() -> StrategyService:
    if strategy_service_instance is None:
        log.error("Strategy service not initialized")
        raise HTTPException(status_code=500, detail="Strategy service not initialized")
    log.info(f"Strategy service accessed: {strategy_service_instance is not None}")
    return strategy_service_instance


class StrategyResponse(BaseModel):
    """Strategy response model"""

    name: str
    description: str
    version: str
    author: str
    symbol: str
    interval: str
    enabled: bool
    status: str
    last_signal: Optional[Dict[str, Any]] = None
    performance: Dict[str, Any] = {}


class StrategyListResponse(BaseModel):
    """Strategy list response model"""

    strategies: List[StrategyResponse]
    total: int


class StrategyActionRequest(BaseModel):
    """Strategy action request model"""

    action: str  # start, stop, reload


@router.get("/", response_model=StrategyListResponse)
async def get_strategies(
    strategy_service: StrategyService = Depends(get_strategy_service),
):
    """Get all available strategies"""
    try:
        log.info(f"Getting strategies from service: {strategy_service is not None}")
        strategies = strategy_service.get_all_strategies()
        log.info(f"Found {len(strategies)} strategies")

        strategy_responses = []
        for name, strategy_instance in strategies.items():
            strategy_responses.append(
                StrategyResponse(
                    name=name,
                    description=strategy_instance.config.description,
                    version=strategy_instance.config.version,
                    author=strategy_instance.config.author,
                    symbol=strategy_instance.config.symbol,
                    interval=strategy_instance.config.interval,
                    enabled=strategy_instance.config.enabled,
                    status=strategy_instance.status.value,
                    last_signal=(
                        strategy_instance.last_signal.__dict__
                        if strategy_instance.last_signal
                        else None
                    ),
                    performance=strategy_instance.performance,
                )
            )

        return StrategyListResponse(
            strategies=strategy_responses, total=len(strategy_responses)
        )

    except Exception as e:
        log.error(f"Error getting strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configs", response_model=List[str])
async def get_available_configs():
    """Get list of available strategy config files"""
    service = get_strategy_service()
    return service.get_available_configs()


@router.get("/{strategy_name}", response_model=StrategyResponse)
async def get_strategy(
    strategy_name: str,
    strategy_service: StrategyService = Depends(get_strategy_service),
):
    """Get a specific strategy"""
    try:
        strategy_instance = strategy_service.get_strategy(strategy_name)
        if not strategy_instance:
            raise HTTPException(status_code=404, detail="Strategy not found")

        return StrategyResponse(
            name=strategy_name,
            description=strategy_instance.config.description,
            version=strategy_instance.config.version,
            author=strategy_instance.config.author,
            symbol=strategy_instance.config.symbol,
            interval=strategy_instance.config.interval,
            enabled=strategy_instance.config.enabled,
            status=strategy_instance.status.value,
            last_signal=(
                strategy_instance.last_signal.__dict__
                if strategy_instance.last_signal
                else None
            ),
            performance=strategy_instance.performance,
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting strategy {strategy_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{strategy_name}/start")
async def start_strategy(
    strategy_name: str,
    strategy_service: StrategyService = Depends(get_strategy_service),
):
    """Start a strategy"""
    try:
        success = await strategy_service.start_strategy(strategy_name)
        if not success:
            raise HTTPException(status_code=404, detail="Strategy not found")

        return {"message": f"Strategy {strategy_name} started successfully"}

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error starting strategy {strategy_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{strategy_name}/stop")
async def stop_strategy(
    strategy_name: str,
    strategy_service: StrategyService = Depends(get_strategy_service),
):
    """Stop a strategy"""
    try:
        success = await strategy_service.stop_strategy(strategy_name)
        if not success:
            raise HTTPException(status_code=404, detail="Strategy not found")

        return {"message": f"Strategy {strategy_name} stopped successfully"}

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error stopping strategy {strategy_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{strategy_name}/reload")
async def reload_strategy(
    strategy_name: str,
    strategy_service: StrategyService = Depends(get_strategy_service),
):
    """Reload a strategy configuration"""
    try:
        success = await strategy_service.reload_strategy(strategy_name)
        if not success:
            raise HTTPException(status_code=404, detail="Strategy not found")

        return {"message": f"Strategy {strategy_name} reloaded successfully"}

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error reloading strategy {strategy_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{strategy_name}/config")
async def get_strategy_config(
    strategy_name: str,
    strategy_service: StrategyService = Depends(get_strategy_service),
):
    """Get strategy configuration"""
    try:
        config = strategy_service.get_strategy_config(strategy_name)
        if not config:
            raise HTTPException(status_code=404, detail="Strategy not found")

        return config

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting strategy config {strategy_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{strategy_name}/performance")
async def get_strategy_performance(
    strategy_name: str,
    strategy_service: StrategyService = Depends(get_strategy_service),
):
    """Get strategy performance metrics"""
    try:
        performance = strategy_service.get_strategy_performance(strategy_name)
        if not performance:
            raise HTTPException(status_code=404, detail="Strategy not found")

        return performance

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting strategy performance {strategy_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/load/{strategy_name}")
async def load_strategy(strategy_name: str):
    """Load a strategy by name from config file"""
    service = get_strategy_service()
    
    # Check if strategy is already loaded
    if service.get_strategy(strategy_name) is not None:
        raise HTTPException(
            status_code=400, 
            detail=f"Strategy '{strategy_name}' is already loaded"
        )
    
    # Check if config file exists
    available_configs = service.get_available_configs()
    if strategy_name not in available_configs:
        raise HTTPException(
            status_code=404, 
            detail=f"Strategy config '{strategy_name}' not found. Available: {available_configs}"
        )
    
    # Load the strategy
    success = await service.load_strategy(strategy_name)
    if not success:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to load strategy '{strategy_name}'"
        )
    
    return {"message": f"Strategy '{strategy_name}' loaded successfully"}


@router.post("/unload/{strategy_name}")
async def unload_strategy(strategy_name: str):
    """Unload a strategy from memory"""
    service = get_strategy_service()
    
    # Check if strategy is loaded
    if service.get_strategy(strategy_name) is None:
        raise HTTPException(
            status_code=404, 
            detail=f"Strategy '{strategy_name}' is not loaded"
        )
    
    # Unload the strategy
    success = await service.unload_strategy(strategy_name)
    if not success:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to unload strategy '{strategy_name}'"
        )
    
    return {"message": f"Strategy '{strategy_name}' unloaded successfully"}
