from pathlib import Path
from app.core.util import run_cmd
from .base import StaticCodeAnalyzer, RawToolResult

class RuffAnalyzer(StaticCodeAnalyzer):
    def tool_name(self) -> str:
        return "ruff"

    def analyze(self, workspace: Path, reports_dir: Path) -> RawToolResult:
        artifact = reports_dir / "ruff.json"
        r = run_cmd(["ruff", "check", ".", "--output-format", "json"], cwd=workspace, timeout_sec=120)
        artifact.write_text(r.stdout or "[]", encoding="utf-8")
        return RawToolResult(self.tool_name(), r.exit_code, r.stdout, r.stderr, artifact.name)
