from pathlib import Path
import uuid
from app.core.config import settings

class SessionService:
    @staticmethod
    def session_dir(session_id: str) -> Path:
        return Path(settings.DATA_DIR) / session_id

    @staticmethod
    def workspace_raw_dir(session_id: str) -> Path:
        return SessionService.session_dir(session_id) / "workspace_raw"

    @staticmethod
    def workspace_dir(session_id: str) -> Path:
        return SessionService.session_dir(session_id) / "workspace"

    @staticmethod
    def reports_dir(session_id: str) -> Path:
        return SessionService.session_dir(session_id) / "reports"

    @staticmethod
    def patches_dir(session_id: str) -> Path:
        return SessionService.session_dir(session_id) / "patches"

    @staticmethod
    def ensure_dirs(session_id: str) -> None:
        SessionService.session_dir(session_id).mkdir(parents=True, exist_ok=True)
        SessionService.workspace_raw_dir(session_id).mkdir(parents=True, exist_ok=True)
        SessionService.workspace_dir(session_id).mkdir(parents=True, exist_ok=True)
        SessionService.reports_dir(session_id).mkdir(parents=True, exist_ok=True)
        SessionService.patches_dir(session_id).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def create_session() -> str:
        sid = str(uuid.uuid4())
        SessionService.ensure_dirs(sid)
        return sid
