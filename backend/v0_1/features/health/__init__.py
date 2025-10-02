import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from api import health as _api_health  # type: ignore

router = _api_health.router

def set_dependencies():
    if hasattr(_api_health, 'set_dependencies'):
        _api_health.set_dependencies()


