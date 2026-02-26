from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Any

from app.services.session_service import SessionService
from app.services.repo_service import RepoService

router = APIRouter(prefix="/api/session", tags=["session"])


class CloneRequest(BaseModel):
    git_url: str


@router.post("/upload")
def create_session_from_upload(archive: UploadFile = File(...)) -> dict[str, Any]:
    """
    QALLM-1: Upload a zip file containing source code.
    Creates a session and extracts into workspace_raw.
    """
    if not archive.filename or not archive.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip uploads are supported in this PoC.")

    sid = SessionService.create_session(source_type="upload", github_url=None)
    try:
        SessionService.save_uploaded_zip(sid, archive)
        return {"session_id": sid}
    except Exception as e:
        # Cleanup on failure (optional)
        raise HTTPException(status_code=500, detail=f"Upload/extract failed: {e}")


@router.post("/clone")
def create_session_from_git(req: CloneRequest) -> dict[str, Any]:
    """
    QALLM-6: Clone a Git repository URL.
    Creates a session and clones into workspace_raw.
    """
    sid = SessionService.create_session(source_type="github", github_url=req.git_url)
    try:
        RepoService.clone_into_session(sid, req.git_url)
        return {"session_id": sid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clone failed: {e}")


@router.get("/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    """
    Simple session info endpoint (useful for debugging + UI).
    """
    info = SessionService.get_session_info(session_id)
    if not info:
        raise HTTPException(status_code=404, detail="Session not found")
    return info


@router.get("/{session_id}/files")
def list_session_files(session_id: str) -> dict[str, Any]:
    """
    Lists files extracted/cloned in workspace_raw (before selection).
    UI uses this to show the file tree for inclusion/exclusion.
    """
    if not SessionService.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    files = SessionService.list_workspace_files(session_id)
    return {"session_id": session_id, "files": files, "count": len(files)}