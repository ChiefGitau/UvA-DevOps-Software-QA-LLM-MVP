from pathlib import Path
import shutil
import zipfile
import subprocess
from app.services.session_service import SessionService

class RepoService:
    @staticmethod
    def prepare_from_upload(session_id: str, archive_path: Path) -> Path:
        raw = SessionService.workspace_raw_dir(session_id)
        shutil.rmtree(raw, ignore_errors=True)
        raw.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(archive_path, "r") as z:
            z.extractall(raw)

        return raw

    @staticmethod
    def prepare_from_github(session_id: str, url: str) -> Path:
        raw = SessionService.workspace_raw_dir(session_id)
        shutil.rmtree(raw, ignore_errors=True)
        raw.mkdir(parents=True, exist_ok=True)

        subprocess.run(["git", "clone", "--depth", "1", url, str(raw)], check=True)
        return raw
