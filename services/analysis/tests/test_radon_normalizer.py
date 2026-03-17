import json
from pathlib import Path

from app.normalizers.base import NormalizationContext
from app.normalizers.radon_normalizer import RadonNormalizer


def test_radon_normalizer_extracts_findings_and_snippet(tmp_path: Path):
    workspace = tmp_path / "ws"
    reports = tmp_path / "reports"
    workspace.mkdir()
    reports.mkdir()

    src = workspace / "demo.py"
    src.write_text(
        "def f(x):\n    if x:\n        return 1\n    return 0\n",
        encoding="utf-8",
    )

    # Radon cc -j output format: { "file.py": [ {..}, ... ] }
    radon_data = {
        str(src): [
            {"name": "f", "lineno": 1, "complexity": 12, "rank": "C"},
        ]
    }
    (reports / "radon_cc.json").write_text(json.dumps(radon_data), encoding="utf-8")

    raw = {"tool": "radon", "artifact": "radon_cc.json"}
    ctx = NormalizationContext(session_id="sid", workspace_dir=workspace, reports_dir=reports)

    findings = RadonNormalizer().normalize(raw, ctx)

    assert len(findings) == 1
    f = findings[0]
    assert f.tool == "radon"
    assert f.type == "COMPLEXITY"
    assert f.rule_id == "CC"
    assert f.line == 1
    assert f.code_snippet is not None
    assert "def f" in f.code_snippet
    assert f.extra["complexity"] == 12
