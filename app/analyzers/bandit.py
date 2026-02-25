from pathlib import Path
from app.core.util import run_cmd, tool_exists
from .base import StaticCodeAnalyzer, RawToolResult

class BanditAnalyzer(StaticCodeAnalyzer):
    def tool_name(self) -> str:
        return "bandit"

    def analyze(self, workspace: Path, reports_dir: Path) -> RawToolResult:
        reports_dir.mkdir(parents=True, exist_ok=True)
        artifact = reports_dir / "bandit.json"

        if not tool_exists("bandit"):
            artifact.write_text("{}", encoding="utf-8")
            return RawToolResult(
                tool="bandit",
                exit_code=127,
                stdout="",
                stderr="bandit not installed (install with: pip install bandit)",
                artifact=artifact.name
            )

        r = run_cmd(["bandit", "-r", ".", "-f", "json"], cwd=workspace, timeout_sec=120)
        artifact.write_text(r.stdout or "{}", encoding="utf-8")

        return RawToolResult(self.tool_name(), r.exit_code, r.stdout, r.stderr, artifact.name)
