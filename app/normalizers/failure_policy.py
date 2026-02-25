from __future__ import annotations
from pathlib import Path

def is_real_failure(tool: str, exit_code: int, artifact_path: Path | None) -> bool:
    tool = (tool or "").lower()

    # Ruff uses exit code 1 to indicate lint findings
    if tool == "ruff":
        return exit_code not in (0, 1)

    # Bandit may return non-zero based on findings, but must produce an artifact
    if tool == "bandit":
        if artifact_path and artifact_path.exists():
            return False
        return exit_code != 0

    # Trufflehog: treat non-zero as failure (missing binary => 127)
    if tool == "trufflehog":
        return exit_code != 0

    # Radon: non-zero is failure
    if tool == "radon":
        return exit_code != 0

    return exit_code != 0
