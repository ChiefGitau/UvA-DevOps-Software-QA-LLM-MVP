"""
Project 4: Software Quality Analysis & Repair Using LLMs
FastAPI application entry point.

Routes and service wiring are added incrementally per feature branch.
"""

import logging
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.analysis_routes import router as analysis_router
from app.api.session_routes import router as session_router
from app.core.logging import setup_logging

# Configure structured JSON logging before anything else
setup_logging()

_logger = logging.getLogger(__name__)

TAG_METADATA = [
    {
        "name": "session",
        "description": "Upload source code (ZIP) or clone a GitHub repository. "
        "Each upload/clone creates an isolated **session** identified by a UUID.",
    },
    {
        "name": "analysis",
        "description": "Run static analysis tools (Bandit, Ruff, Radon, TruffleHog) "
        "against session files and retrieve unified findings reports.",
    },
    {
        "name": "health",
        "description": "Liveness and readiness probes for Docker HEALTHCHECK and monitoring.",
    },
]
_BOOT_TIME = time.monotonic()

app = FastAPI(
    title="Quality Repair Tool — P4 Group 17",
    description=(
        "A web application that analyses Python source code using **four static "
        "analysis tools** (Bandit, Ruff, Radon, TruffleHog) and uses Large Language "
        "Models to **automatically repair** identified issues.\n\n"
        "## Workflow\n"
        "1. **Upload** a ZIP or **clone** a GitHub repo → receive a `session_id`\n"
        "2. **Select files** to include in the analysis\n"
        "3. **Run analysis** → unified findings report\n"
        "4. *(Sprint 2)* **Repair** findings via LLM → verification\n\n"
        "## Links\n"
        "- [GitHub Repository](https://github.com/ChiefGitau/UvA-DevOps-Software-QA-LLM-MVP)\n"
        "- UvA MSc SE · DevOps and Cloud-based Software · Group 17"
    ),
    version="0.2.0",
    openapi_tags=TAG_METADATA,
    license_info={"name": "Academic Use Only"},
    contact={
        "name": "Group 17",
        "url": "https://github.com/ChiefGitau/UvA-DevOps-Software-QA-LLM-MVP",
    },
)

# Mount static assets
_static = Path("app/ui/static")
if _static.exists():
    app.mount("/static", StaticFiles(directory=str(_static)), name="static")


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every request with method, path, status, and duration."""
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


# API routers
app.include_router(session_router)
app.include_router(analysis_router)


def _check_tools() -> dict[str, bool]:
    """Check availability of each analysis tool binary."""
    import shutil

    tools = {
        "bandit": shutil.which("bandit") is not None,
        "ruff": shutil.which("ruff") is not None,
        "radon": shutil.which("radon") is not None,
        "trufflehog": shutil.which("trufflehog") is not None,
    }
    return tools


@app.get(
    "/health",
    tags=["health"],
    summary="Health check",
    response_description="Service status with version",
)
def health():
    """Liveness probe used by Docker HEALTHCHECK and nginx `depends_on`.

    Returns HTTP 200 when the backend is ready to accept requests.
    """
    tools = _check_tools()
    return {
        "status": "healthy",
        "version": "0.2.0",
        "tools": tools,
        "uptime_seconds": round(time.monotonic() - _BOOT_TIME, 1),
    }


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index():
    """Serve the minimal UI (QALLM-15)."""
    html = Path("app/ui/templates/index.html")
    if html.exists():
        return html.read_text(encoding="utf-8")
    return "<h1>Quality Repair Tool</h1><p>UI not built yet.</p>"
