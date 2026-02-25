from pathlib import Path
import shutil
from app.core.util import run_cmd
from .base import StaticCodeAnalyzer, RawToolResult

class TruffleHogAnalyzer(StaticCodeAnalyzer):
    def tool_name(self) -> str:
        return "trufflehog"

    def analyze(self, workspace: Path, reports_dir: Path) -> RawToolResult:
        reports_dir.mkdir(parents=True, exist_ok=True)

        if shutil.which("trufflehog") is None:
            return RawToolResult(
                tool=self.tool_name(),
                exit_code=127,
                stdout="",
                stderr="trufflehog not installed. Install it in Dockerfile or CI workflow.",
                artifact=None
            )

        artifact = reports_dir / "trufflehog.jsonl"
        r = run_cmd(["trufflehog", "filesystem", ".", "--json"], cwd=workspace, timeout_sec=180)
        artifact.write_text(r.stdout or "", encoding="utf-8")
        return RawToolResult(self.tool_name(), r.exit_code, r.stdout, r.stderr, artifact.name)
