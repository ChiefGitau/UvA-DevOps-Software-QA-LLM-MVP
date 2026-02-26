import json
from pathlib import Path

from app.normalizers.bandit_normalizer import BanditNormalizer
from app.normalizers.base import NormalizationContext


def test_bandit_normalizer_extracts_findings_and_snippet(tmp_path: Path):
    workspace = tmp_path / "ws"
    reports = tmp_path / "reports"
    workspace.mkdir()
    reports.mkdir()

    # Source file (snippet should be extracted from this)
    src = workspace / "demo.py"
    src.write_text(
        "import subprocess\n"
        "import pickle\n"
        "x = 1\n"
        "subprocess.call('ls', shell=True)\n",
        encoding="utf-8",
    )

    # Bandit JSON artifact
    bandit_data = {
        "results": [
            {
                "filename": str(src),
                "issue_severity": "HIGH",
                "issue_confidence": "HIGH",
                "issue_text": "subprocess call with shell=True identified, security issue.",
                "test_id": "B602",
                "line_number": 4,
            }
        ]
    }
    (reports / "bandit.json").write_text(json.dumps(bandit_data), encoding="utf-8")

    raw = {"tool": "bandit", "artifact": "bandit.json"}
    ctx = NormalizationContext(session_id="sid", workspace_dir=workspace, reports_dir=reports)

    findings = BanditNormalizer().normalize(raw, ctx)

    assert len(findings) == 1
    f = findings[0]
    assert f.tool == "bandit"
    assert f.type == "SECURITY"
    assert f.severity == "HIGH"
    assert f.rule_id == "B602"
    assert f.file.endswith("demo.py")
    assert f.line == 4
    assert f.code_snippet is not None
    assert "shell=True" in f.code_snippet
    assert ">>" in f.code_snippet  # our snippet formatting