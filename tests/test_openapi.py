"""Tests for OpenAPI documentation (QALLM-20)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_openapi_schema_accessible():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    assert schema["info"]["title"] == "Quality Repair Tool — P4 Group 17"
    assert schema["info"]["version"] == "0.2.0"


def test_swagger_ui_accessible():
    r = client.get("/docs")
    assert r.status_code == 200
    assert "swagger-ui" in r.text.lower()


def test_redoc_accessible():
    r = client.get("/redoc")
    assert r.status_code == 200
    assert "redoc" in r.text.lower()


def test_openapi_has_tag_descriptions():
    schema = client.get("/openapi.json").json()
    tags = {t["name"]: t["description"] for t in schema.get("tags", [])}
    assert "session" in tags
    assert "analysis" in tags
    assert "health" in tags
    assert len(tags["session"]) > 10, "Tag description should be meaningful"


def test_all_endpoints_have_summaries():
    schema = client.get("/openapi.json").json()
    paths = schema.get("paths", {})
    for path, methods in paths.items():
        for method, details in methods.items():
            if method in ("get", "post", "put", "delete", "patch"):
                assert "summary" in details, f"{method.upper()} {path} missing summary"


def test_root_excluded_from_docs():
    """The / HTML endpoint should not clutter the API docs."""
    schema = client.get("/openapi.json").json()
    assert "/" not in schema.get("paths", {}), "Root UI route should have include_in_schema=False"
