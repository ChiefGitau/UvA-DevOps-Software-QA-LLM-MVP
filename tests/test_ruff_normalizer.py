import json
from pathlib import Path

from app.normalizers.base import NormalizationContext
from app.normalizers.ruff_normalizer import RuffNormalizer


def test_ruff_normalizer_extracts_findings_and_snippet(tmp_path: Path):
    workspace = tmp_path / "ws"
    reports = tmp_path / "reports"
    workspace.mkdir()
    reports.mkdir()

    src = workspace / "demo.py"
    src.write_text("import os\n\nprint('x')\n", encoding="utf-8")

    # Ruff JSON artifact (typical structure)
    ruff_items = [
        {
            "code": "F401",
            "message": "`os` imported but unused",
            "filename": str(src),
            "location": {"row": 1, "column": 1},
            "fixable": True,
        }
    ]
    (reports / "ruff.json").write_text(json.dumps(ruff_items), encoding="utf-8")

    raw = {"tool": "ruff", "artifact": "ruff.json"}
    ctx = NormalizationContext(session_id="sid", workspace_dir=workspace, reports_dir=reports)

    findings = RuffNormalizer().normalize(raw, ctx)

    assert len(findings) == 1
    f = findings[0]
    assert f.tool == "ruff"
    assert f.type == "SMELL"
    assert f.rule_id == "F401"
    assert f.line == 1
    assert f.code_snippet is not None
    assert "import os" in f.code_snippet
