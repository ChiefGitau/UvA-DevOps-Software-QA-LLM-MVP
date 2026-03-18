"""Lightweight session path helpers — read-only, resolves EFS paths."""

from __future__ import annotations

from pathlib import Path

from app.core.config import settings


class SessionService:
    @staticmethod
    def _base_dir() -> Path:
        return Path(settings.DATA_DIR)

    @staticmethod
    def session_dir(session_id: str) -> Path:
        return SessionService._base_dir() / session_id

    @staticmethod
    def workspace_active_dir(session_id: str) -> Path:
        return SessionService.session_dir(session_id) / "workspace"

    @staticmethod
    def reports_dir(session_id: str) -> Path:
        return SessionService.session_dir(session_id) / "reports"

    @staticmethod
    def session_exists(session_id: str) -> bool:
        return SessionService.session_dir(session_id).exists()
