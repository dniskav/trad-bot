import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from api import orders as _api_orders  # type: ignore

router = _api_orders.router

def set_dependencies(trading_tracker):
    _api_orders.set_dependencies(trading_tracker)


