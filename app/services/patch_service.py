from pathlib import Path
import subprocess
from .session_service import SessionService

class PatchService:
    @staticmethod
    def apply_unified_diff(session_id: str, unified_diff: str) -> None:
        ws = SessionService.workspace_dir(session_id)
        patch_file = SessionService.patches_dir(session_id) / "patch.diff"
        patch_file.write_text(unified_diff, encoding="utf-8")

        if (ws / ".git").exists():
            r = subprocess.run(["git", "apply", "--whitespace=nowarn", str(patch_file)], cwd=str(ws),
                               capture_output=True, text=True)
            if r.returncode == 0:
                return

        r2 = subprocess.run(["patch", "-p0", "-i", str(patch_file)], cwd=str(ws),
                            capture_output=True, text=True)
        if r2.returncode != 0:
            raise RuntimeError(f"Patch apply failed:\n{(r2.stderr or r2.stdout)[-2000:]}")
