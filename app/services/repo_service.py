from pathlib import Path
import shutil
import subprocess

from app.core.security import safe_extract_zip
from app.services.session_service import SessionService


class RepoService:
    @staticmethod
    def prepare_from_upload(session_id: str, archive_path: Path) -> Path:
        """Extract uploaded zip into workspace_raw."""
        raw = SessionService.workspace_raw_dir(session_id)
        shutil.rmtree(raw, ignore_errors=True)
        raw.mkdir(parents=True, exist_ok=True)

        safe_extract_zip(archive_path, raw)
        return raw

    @staticmethod
    def prepare_from_github(session_id: str, url: str) -> Path:
        """Shallow-clone a GitHub repo into workspace_raw."""
        raw = SessionService.workspace_raw_dir(session_id)
        shutil.rmtree(raw, ignore_errors=True)
        raw.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            ["git", "clone", "--depth", "1", url, str(raw)],
            check=True,
            timeout=120,
        )
        return raw
