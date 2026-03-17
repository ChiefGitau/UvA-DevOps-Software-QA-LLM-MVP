"""Tests for repair service (QALLM-12c — batch per file)."""

import json

import pytest
from fastapi.testclient import TestClient

from app.llm.base import LLMModel, LLMResponse
from app.main import app
from app.services.repair_service import (
    _group_by_file,
    _highest_severity,
    _load_findings,
    _make_file_diff,
    _resolve_model,
    _strip_fences,
    run_repair,
)

client = TestClient(app)


# ── Fake LLM model for testing ───────────────────────────────────


class FakeLLM(LLMModel):
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
    data = [
        {
            "id": "abc",
            "tool": "bandit",
            "type": "SECURITY",
            "severity": "HIGH",
            "file": "demo.py",
            "line": 5,
            "message": "eval()",
            "rule_id": "B307",
            "code_snippet": None,
            "extra": {},
        }
    ]
    (reports / "findings_unified.json").write_text(json.dumps(data))
    monkeypatch.setattr(
        "app.services.repair_service.SessionService.reports_dir",
        staticmethod(lambda sid: reports),
    )
    findings = _load_findings("test")
    assert len(findings) == 1
    assert findings[0].tool == "bandit"


def test_make_file_diff():
    diff = _make_file_diff("x = eval(y)\n", "x = int(y)\n", "demo.py")
    assert "--- a/demo.py" in diff
    assert "+++ b/demo.py" in diff


def test_make_file_diff_identical():
    assert _make_file_diff("x = 1\n", "x = 1\n", "demo.py").strip() == ""


def test_strip_fences():
    assert _strip_fences("```python\nx = 1\n```") == "x = 1"
    assert _strip_fences("x = 1") == "x = 1"


def test_group_by_file():
    from app.domain.models import Finding

    f1 = Finding(tool="bandit", type="SECURITY", severity="HIGH", file="a.py", line=1, message="m")
    f2 = Finding(tool="ruff", type="SMELL", severity="LOW", file="a.py", line=5, message="m")
    f3 = Finding(tool="bandit", type="SECURITY", severity="MEDIUM", file="b.py", line=3, message="m")

    groups = _group_by_file([f1, f2, f3])
    assert len(groups) == 2
    assert len(groups["a.py"]) == 2
    assert len(groups["b.py"]) == 1


def test_highest_severity():
    from app.domain.models import Finding

    findings = [
        Finding(tool="ruff", type="SMELL", severity="LOW", file="a.py", line=1, message="m"),
        Finding(tool="bandit", type="SECURITY", severity="HIGH", file="a.py", line=5, message="m"),
        Finding(tool="radon", type="COMPLEXITY", severity="MEDIUM", file="a.py", line=10, message="m"),
    ]
    assert _highest_severity(findings) == "HIGH"


# ── Model routing ────────────────────────────────────────────────


def test_routing_critical_to_strong():
    assert _resolve_model("CRITICAL", None) != ""


def test_routing_low_to_fast():
    assert _resolve_model("LOW", None) != ""


def test_routing_explicit_overrides():
    assert _resolve_model("CRITICAL", "claude-3-5-haiku-20241022") == "claude-3-5-haiku-20241022"


# ── Integration: batch per file ──────────────────────────────────


@pytest.fixture()
def session_with_findings(tmp_path, monkeypatch):
    sid = "repair-test"
    base = tmp_path / sid
    workspace = base / "workspace"
    workspace.mkdir(parents=True)
    reports = base / "reports"
    reports.mkdir(parents=True)

    buggy = workspace / "demo" / "main.py"
    buggy.parent.mkdir(parents=True)
    buggy.write_text(
        "import os\n"
        "import pickle\n"
        "\n"
        "def process(data):\n"
        "    result = eval(data)\n"
        "    obj = pickle.loads(data)\n"
        "    return result, obj\n"
    )

    findings = [
        {
            "id": "f1",
            "tool": "bandit",
            "type": "SECURITY",
            "severity": "HIGH",
            "file": "demo/main.py",
            "line": 5,
            "message": "Use of eval() detected.",
            "rule_id": "B307",
            "code_snippet": None,
            "extra": {},
        },
        {
            "id": "f2",
            "tool": "bandit",
            "type": "SECURITY",
            "severity": "MEDIUM",
            "file": "demo/main.py",
            "line": 6,
            "message": "Pickle loads unsafe.",
            "rule_id": "B301",
            "code_snippet": None,
            "extra": {},
        },
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


def test_batch_repair_writes_valid_file(session_with_findings, monkeypatch):
    """Two findings in one file → one LLM call → complete corrected file."""
    sid, workspace, reports = session_with_findings

    corrected_file = (
        "import os\n"
        "import ast\n"
        "\n"
        "def process(data):\n"
        "    result = ast.literal_eval(data)\n"
        "    obj = None  # pickle removed for safety\n"
        "    return result, obj\n"
    )

    fake = FakeLLM(
        LLMResponse(
            content=corrected_file,
            input_tokens=200,
            output_tokens=100,
            model="fake",
            provider="fake",
        )
    )
    monkeypatch.setattr("app.services.repair_service._llm_registry.pick", lambda name: fake)

    result = run_repair(sid, provider="fake")

    assert result["repaired_count"] == 1  # 1 file patched
    assert result["token_usage"]["total_tokens"] == 300

    # The workspace file should be the complete corrected file
    actual = (workspace / "demo" / "main.py").read_text()
    assert "ast.literal_eval" in actual  # eval replaced with safe alternative
    assert "pickle.loads(data)" not in actual  # unsafe pickle removed
    assert "import pickle" not in actual  # pickle import gone

    # File must compile (the key safety check)
    compile(actual, "demo/main.py", "exec")

    # Diff should exist
    assert result["patches"][0]["unified_diff"] != ""
    assert result["patches"][0]["applied"] is True

    # Report persisted
    assert (reports / "repair_report.json").exists()


def test_batch_repair_rejects_invalid_python(session_with_findings, monkeypatch):
    """If the LLM returns invalid Python, the file is NOT modified."""
    sid, workspace, reports = session_with_findings

    original = (workspace / "demo" / "main.py").read_text()

    fake = FakeLLM(
        LLMResponse(
            content="def broken(\n    x = {\n",  # invalid syntax
            input_tokens=50,
            output_tokens=20,
            model="fake",
            provider="fake",
        )
    )
    monkeypatch.setattr("app.services.repair_service._llm_registry.pick", lambda name: fake)

    result = run_repair(sid, provider="fake")

    assert result["repaired_count"] == 0
    # File should be unchanged
    assert (workspace / "demo" / "main.py").read_text() == original
    # Error should be reported
    assert "syntax_error" in result["patches"][0]["error"]


def test_run_repair_skips_secrets(session_with_findings, monkeypatch):
    sid, workspace, reports = session_with_findings
    secrets = [
        {
            "id": "s1",
            "tool": "trufflehog",
            "type": "SECRET",
            "severity": "CRITICAL",
            "file": "demo/main.py",
            "line": 1,
            "message": "AWS key",
            "rule_id": None,
            "code_snippet": None,
            "extra": {},
        }
    ]
    (reports / "findings_unified.json").write_text(json.dumps(secrets))

    fake = FakeLLM(LLMResponse(content="", provider="fake"))
    monkeypatch.setattr("app.services.repair_service._llm_registry.pick", lambda name: fake)

    result = run_repair(sid, provider="fake")
    assert result["repaired_count"] == 0


# ── API endpoint tests ───────────────────────────────────────────


def test_repair_endpoint_404():
    assert client.post("/api/repair/nonexistent", json={}).status_code == 404


def test_repair_endpoint_400_no_analysis(tmp_path, monkeypatch):
    sid = "no-analysis"
    reports = tmp_path / "reports"
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
