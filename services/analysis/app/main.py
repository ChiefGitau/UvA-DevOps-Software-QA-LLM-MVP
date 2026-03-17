import logging
import time

from app.core.logging import setup_logging
from fastapi import FastAPI, Request

from app.api.analysis_routes import router as analysis_router

# Configure structured JSON logging
setup_logging()
_logger = logging.getLogger(__name__)
_BOOT_TIME = time.monotonic()

app = FastAPI(
    title="Analysis Service",
    description="Performs static analysis using Bandit, Ruff, Radon, and TruffleHog.",
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
app.include_router(analysis_router)


def _check_tools() -> dict[str, bool]:
    import shutil

    return {
        "bandit": shutil.which("bandit") is not None,
        "ruff": shutil.which("ruff") is not None,
        "radon": shutil.which("radon") is not None,
        "trufflehog": shutil.which("trufflehog") is not None,
    }


@app.get("/health", tags=["health"])
def health():
    return {
        "status": "healthy",
        "service": "analysis-service",
        "version": "0.2.0",
        "tools": _check_tools(),
        "uptime_seconds": round(time.monotonic() - _BOOT_TIME, 1),
    }
