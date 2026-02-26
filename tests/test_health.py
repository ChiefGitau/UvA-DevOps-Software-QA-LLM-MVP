"""Tests for the /health endpoint."""

def test_health_returns_200(client):
    res = client.get("/health")
    assert res.status_code == 200


def test_health_reports_healthy(client):
    data = client.get("/health").json()
    assert data["status"] == "healthy"
    assert "version" in data