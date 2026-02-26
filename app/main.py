"""
Project 4 – Software Quality Analysis & Repair Using LLMs
FastAPI application entry point.

Routes and service wiring are added incrementally per feature branch.
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.session_routes import router as session_router

app = FastAPI(
    title="Quality Repair Tool",
    description="Analyse code with static analysis tools and repair findings with LLMs",
    version="0.1.0",
)

# Mount static assets (created in QALLM-15 minimal UI branch)
_static = Path("app/ui/static")
if _static.exists():
    app.mount("/static", StaticFiles(directory=str(_static)), name="static")

# API routers
app.include_router(session_router)


@app.get("/health")
def health():
    """Health check endpoint for Docker HEALTHCHECK and monitoring."""
    return {"status": "healthy", "version": "0.1.0"}