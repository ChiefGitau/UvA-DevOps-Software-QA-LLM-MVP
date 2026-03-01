"""
Project 4 – Software Quality Analysis & Repair Using LLMs
FastAPI application entry point.

Routes and service wiring are added incrementally per feature branch.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.analysis_routes import router as analysis_router
from app.api.repair_routes import router as repair_router
from app.api.session_routes import router as session_router

app = FastAPI(
    title="Quality Repair Tool",
    description="Analyse code with static analysis tools and repair findings with LLMs",
    version="0.1.0",
)

# Mount static assets
_static = Path("app/ui/static")
if _static.exists():
    app.mount("/static", StaticFiles(directory=str(_static)), name="static")

# API routers
app.include_router(session_router)
app.include_router(analysis_router)
app.include_router(repair_router)


@app.get("/health")
def health():
    """Health check endpoint for Docker HEALTHCHECK and monitoring."""
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/", response_class=HTMLResponse)
def index():
    """Serve the minimal UI (QALLM-15)."""
    html = Path("app/ui/templates/index.html")
    if html.exists():
        return html.read_text(encoding="utf-8")
    return "<h1>Quality Repair Tool</h1><p>UI not built yet.</p>"
