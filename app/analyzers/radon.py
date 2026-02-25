from pathlib import Path
from app.core.util import run_cmd
from .base import StaticCodeAnalyzer, RawToolResult

class RadonAnalyzer(StaticCodeAnalyzer):
    def tool_name(self) -> str:
        return "radon"

    def analyze(self, workspace: Path, reports_dir: Path) -> RawToolResult:
        artifact = reports_dir / "radon_cc.json"
        r = run_cmd(["radon", "cc", ".", "-j"], cwd=workspace, timeout_sec=120)
        artifact.write_text(r.stdout or "{}", encoding="utf-8")
        return RawToolResult(self.tool_name(), r.exit_code, r.stdout, r.stderr, artifact.name)
