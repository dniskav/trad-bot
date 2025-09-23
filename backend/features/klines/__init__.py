import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from api import klines as _api_klines  # type: ignore

router = _api_klines.router

def set_dependencies(real_trading_manager=None):
    # klines no necesita dependencias - usa Binance directamente
    pass


