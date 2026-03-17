import logging
import time

from fastapi import FastAPI, Request

from app.api.session_routes import router as session_router
from app.core.logging import setup_logging

# Configure structured JSON logging
setup_logging()
_logger = logging.getLogger(__name__)
_BOOT_TIME = time.monotonic()

app = FastAPI(
    title="Session Service",
    description="Manages user sessions, file uploads, and workspace state.",
    version="0.2.0",
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    _logger.info("%s %s → %d (%.0fms)", request.method, request.url.path, response.status_code, duration_ms)
    return response


# API routers
app.include_router(session_router)


@app.get("/health", tags=["health"])
def health():
    return {
        "status": "healthy",
        "service": "session-service",
        "version": "0.2.0",
        "uptime_seconds": round(time.monotonic() - _BOOT_TIME, 1),
    }
