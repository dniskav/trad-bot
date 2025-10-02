from datetime import datetime, timezone
from fastapi import Request
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from shared.logger import get_logger

log = get_logger("stm.middleware")


async def log_requests_middleware(request: Request, call_next):
    """Log all HTTP requests with timing and status"""
    start = datetime.now(timezone.utc)
    method = request.method.upper()

    # Method icons for better log readability
    method_icon = {
        "GET": "🟢",
        "POST": "🟠",
        "PUT": "🔵",
        "PATCH": "🟦",
        "DELETE": "🔴",
        "OPTIONS": "⚪",
        "HEAD": "⚪",
    }.get(method, "⚪")

    # Log request start
    log.info(f"{method_icon} {method} {request.url.path}")

    # Process request
    response = await call_next(request)

    # Calculate duration and log response
    duration_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000.0
    status_icon = "✅" if 200 <= response.status_code < 400 else "❌"
    log.info(
        f"{method_icon} {method} {request.url.path} {status_icon} {response.status_code} ({duration_ms:.1f} ms)"
    )

    return response
