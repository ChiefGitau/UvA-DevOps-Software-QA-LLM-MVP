"""Tests for repair service and API endpoint (QALLM-12, QALLM-12b)."""

import json

import pytest
from fastapi.testclient import TestClient

from app.llm.base import LLMProvider, LLMResponse
from app.main import app
from app.services.repair_service import _load_findings, _make_diff, run_repair

client = TestClient(app)


# ── Fake LLM provider for testing ────────────────────────────────


class FakeLLMProvider(LLMProvider):
    """Returns a pre-set response for testing."""

    def __init__(self, response: LLMResponse):
        self._response = response

    def name(self) -> str:
        return "fake"

    def is_configured(self) -> bool:
        return True

    def chat(self, system, user, tracker=None):
        if tracker:
            tracker.record(self._response)
        return self._response


# ── Unit tests ────────────────────────────────────────────────────


def test_load_findings_from_json(tmp_path, monkeypatch):
    reports = tmp_path / "reports"
    reports.mkdir()
    findings_data = [
        {
            "id": "abc123",
            "tool": "bandit",
            "type": "SECURITY",
            "severity": "HIGH",
            "file": "demo/main.py",
            "line": 5,
            "message": "Use of eval()",
            "rule_id": "B307",
            "code_snippet": None,
            "extra": {},
        }
    ]
    (reports / "findings_unified.json").write_text(json.dumps(findings_data))

    monkeypatch.setattr(
        "app.services.repair_service.SessionService.reports_dir",
        staticmethod(lambda sid: reports),
    )
    findings = _load_findings("test-session")
    assert len(findings) == 1
    assert findings[0].tool == "bandit"


def test_make_diff_produces_unified_diff():
    original = "x = eval(input())\n"
    repaired = "x = int(input())\n"
    diff = _make_diff(original, repaired, "demo.py", 1)
    assert "--- a/demo.py" in diff
    assert "+++ b/demo.py" in diff


def test_make_diff_identical_returns_empty():
    code = "x = 1\n"
    assert _make_diff(code, code, "demo.py", 1).strip() == ""


# ── Integration test with fake provider ──────────────────────────


@pytest.fixture()
def session_with_findings(tmp_path, monkeypatch):
    sid = "repair-test-session"
    base = tmp_path / sid
    workspace = base / "workspace"
    workspace.mkdir(parents=True)
    reports = base / "reports"
    reports.mkdir(parents=True)

    buggy = workspace / "demo" / "main.py"
    buggy.parent.mkdir(parents=True)
    buggy.write_text("import os\n\ndef process(data):\n    result = eval(data)\n    return result\n")

    findings = [
        {
            "id": "f1",
            "tool": "bandit",
            "type": "SECURITY",
            "severity": "HIGH",
            "file": "demo/main.py",
            "line": 4,
            "message": "Use of eval() detected.",
            "rule_id": "B307",
            "code_snippet": None,
            "extra": {},
        }
    ]
    (reports / "findings_unified.json").write_text(json.dumps(findings))

    monkeypatch.setattr(
        "app.services.repair_service.SessionService.workspace_active_dir",
        staticmethod(lambda s: workspace),
    )
    monkeypatch.setattr(
        "app.services.repair_service.SessionService.reports_dir",
        staticmethod(lambda s: reports),
    )

    return sid, workspace, reports


def test_run_repair_with_fake_provider(session_with_findings, monkeypatch):
    sid, workspace, reports = session_with_findings

    fixed_code = "import os\n\ndef process(data):\n    result = int(data)\n    return result"

    fake = FakeLLMProvider(
        LLMResponse(
            content=fixed_code,
            input_tokens=100,
            output_tokens=50,
            model="fake-model",
            provider="fake",
        )
    )

    # Patch the registry to return our fake provider
    monkeypatch.setattr(
        "app.services.repair_service._llm_registry.pick",
        lambda name: fake,
    )

    result = run_repair(sid, provider="fake")

    assert result["repaired_count"] == 1
    assert len(result["patches"]) == 1
    assert result["patches"][0]["applied"] is True
    assert result["patches"][0]["unified_diff"] != ""
    assert result["token_usage"]["total_tokens"] == 150
    assert result["provider_used"] == "fake"

    # File should be modified
    src = (workspace / "demo" / "main.py").read_text()
    assert "int(data)" in src
    assert "eval(data)" not in src

    # Report persisted
    assert (reports / "repair_report.json").exists()
    report = json.loads((reports / "repair_report.json").read_text())
    assert report["provider"] == "fake"


def test_run_repair_skips_secrets(session_with_findings, monkeypatch):
    sid, workspace, reports = session_with_findings

    findings = [
        {
            "id": "s1",
            "tool": "trufflehog",
            "type": "SECRET",
            "severity": "CRITICAL",
            "file": "demo/main.py",
            "line": 1,
            "message": "AWS key detected",
            "rule_id": None,
            "code_snippet": None,
            "extra": {},
        }
    ]
    (reports / "findings_unified.json").write_text(json.dumps(findings))

    # Still need a provider even though it won't be called
    fake = FakeLLMProvider(LLMResponse(content="", provider="fake"))
    monkeypatch.setattr(
        "app.services.repair_service._llm_registry.pick",
        lambda name: fake,
    )

    result = run_repair(sid, provider="fake")
    assert result["repaired_count"] == 0
    assert len(result["patches"]) == 0


# ── API endpoint tests ───────────────────────────────────────────


def test_repair_endpoint_404_missing_session():
    r = client.post("/api/repair/nonexistent", json={})
    assert r.status_code == 404


def test_repair_endpoint_400_no_analysis(tmp_path, monkeypatch):
    sid = "no-analysis-session"
    base = tmp_path / sid
    base.mkdir(parents=True)
    reports = base / "reports"
    reports.mkdir()

    monkeypatch.setattr(
        "app.services.session_service.SessionService.session_exists",
        staticmethod(lambda s: s == sid),
    )
    monkeypatch.setattr(
        "app.services.session_service.SessionService.reports_dir",
        staticmethod(lambda s: reports),
    )

    r = client.post(f"/api/repair/{sid}", json={})
    assert r.status_code == 400
    assert "No analysis run" in r.json()["detail"]
