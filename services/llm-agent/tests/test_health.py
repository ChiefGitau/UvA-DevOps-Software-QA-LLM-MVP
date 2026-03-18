"""Tests for the LLM Agent Service health endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200():
    """GET /health must respond with HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_response_shape():
    """Response must include status, service, and uptime_seconds fields."""
    response = client.get("/health")
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "llm-agent-service"
    assert isinstance(data["uptime_seconds"], (int, float))
    assert data["uptime_seconds"] >= 0


def test_health_content_type():
    """Response must be JSON."""
    response = client.get("/health")
    assert "application/json" in response.headers["content-type"]
