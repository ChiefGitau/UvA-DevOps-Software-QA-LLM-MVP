"""Lightweight session path helpers for the Analysis service.

This is NOT a full SessionService — the real one lives in the Session microservice.
Analysis service only needs to resolve session directory paths on the shared EFS volume.
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import settings


class SessionService:
    """Read-only session path resolver (shared EFS volume)."""

    @staticmethod
    def _base_dir() -> Path:
        return Path(settings.DATA_DIR)

    @staticmethod
    def session_dir(session_id: str) -> Path:
        return SessionService._base_dir() / session_id

    @staticmethod
    def workspace_raw_dir(session_id: str) -> Path:
        return SessionService.session_dir(session_id) / "workspace_raw"

    @staticmethod
    def workspace_active_dir(session_id: str) -> Path:
        return SessionService.session_dir(session_id) / "workspace"

    @staticmethod
    def reports_dir(session_id: str) -> Path:
        return SessionService.session_dir(session_id) / "reports"

    @staticmethod
    def session_exists(session_id: str) -> bool:
        return SessionService.session_dir(session_id).exists()

    @staticmethod
    def list_workspace_files(session_id: str) -> list[str]:
        """List files under workspace_raw as relative, unix-style paths."""
        raw_dir = SessionService.workspace_raw_dir(session_id)
        if not raw_dir.exists():
            return []

        files: list[str] = []
        for p in raw_dir.rglob("*"):
            if p.is_file():
                rel = p.relative_to(raw_dir).as_posix()
                files.append(rel)

        files.sort()
        return files
