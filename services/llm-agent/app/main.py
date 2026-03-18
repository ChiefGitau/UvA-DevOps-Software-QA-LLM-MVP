import logging
import time

from fastapi import FastAPI, Request

from app.api.repair_routes import router as repair_router
from app.core.logging import setup_logging

setup_logging()
_logger = logging.getLogger(__name__)
_BOOT_TIME = time.monotonic()

app = FastAPI(
    title="LLM Agent Service",
    description="LangGraph-based multi-agent repair pipeline.",
    version="0.1.0",
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    _logger.info(
        "%s %s → %d (%.0fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


app.include_router(repair_router)


@app.get("/health", tags=["health"])
def health():
    return {
        "status": "healthy",
        "service": "llm-agent-service",
        "version": "0.1.0",
        "uptime_seconds": round(time.monotonic() - _BOOT_TIME, 1),
    }
