"""Tests for session management, upload, and file selection (QALLM-1, QALLM-6)."""
import io
from pathlib import Path

from app.services.session_service import SessionService


# ---------- Session ----------

class TestSession:
    def test_create_session_returns_id(self, client):
        res = client.post("/api/session")
        assert res.status_code == 200
        assert "session_id" in res.json()

    def test_session_creates_directories(self, client):
        sid = client.post("/api/session").json()["session_id"]
        assert SessionService.workspace_raw_dir(sid).exists()
        assert SessionService.workspace_dir(sid).exists()
        assert SessionService.reports_dir(sid).exists()
        assert SessionService.patches_dir(sid).exists()

    def test_get_session_not_allowed(self, client):
        """Browser GET on /api/session should return 405, not 500."""
        res = client.get("/api/session")
        assert res.status_code == 405


# ---------- Upload ----------

class TestUpload:
    def test_upload_zip_returns_workspace_ready(self, client, session_id, sample_zip):
        res = client.post(
            f"/api/session/{session_id}/upload",
            files={"file": ("code.zip", io.BytesIO(sample_zip), "application/zip")},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "workspace_ready"

    def test_upload_populates_workspace_raw(self, client, session_id, sample_zip):
        client.post(
            f"/api/session/{session_id}/upload",
            files={"file": ("code.zip", io.BytesIO(sample_zip), "application/zip")},
        )
        raw = SessionService.workspace_raw_dir(session_id)
        py_files = list(raw.rglob("*.py"))
        assert len(py_files) >= 2


# ---------- GitHub Clone ----------

class TestGitHubClone:
    def test_missing_url_returns_400(self, client, session_id):
        res = client.post(
            f"/api/session/{session_id}/github",
            json={},
        )
        assert res.status_code == 400
        assert "Missing url" in res.json()["detail"]


# ---------- File Listing ----------

class TestFileList:
    def test_empty_session_returns_empty_list(self, client, session_id):
        res = client.get(f"/api/session/{session_id}/files")
        assert res.status_code == 200
        assert res.json() == []

    def test_lists_files_after_upload(self, client, session_id, sample_zip):
        client.post(
            f"/api/session/{session_id}/upload",
            files={"file": ("code.zip", io.BytesIO(sample_zip), "application/zip")},
        )
        res = client.get(f"/api/session/{session_id}/files")
        files = res.json()
        assert len(files) >= 2
        assert any("hello.py" in f for f in files)


# ---------- Selection ----------

class TestSelection:
    def test_select_copies_to_workspace(self, client, session_id, sample_zip):
        # Upload first
        client.post(
            f"/api/session/{session_id}/upload",
            files={"file": ("code.zip", io.BytesIO(sample_zip), "application/zip")},
        )

        # Get file list
        files = client.get(f"/api/session/{session_id}/files").json()

        # Select all
        res = client.post(
            f"/api/session/{session_id}/select",
            json={"selected_files": files},
        )
        data = res.json()
        assert data["ok"] is True
        assert data["copied"] == len(files)

    def test_select_ignores_nonexistent_files(self, client, session_id, sample_zip):
        """Paths that don't exist in workspace_raw are skipped, not copied."""
        client.post(
            f"/api/session/{session_id}/upload",
            files={"file": ("code.zip", io.BytesIO(sample_zip), "application/zip")},
        )
        res = client.post(
            f"/api/session/{session_id}/select",
            json={"selected_files": ["../../etc/passwd", "nonexistent.py"]},
        )
        data = res.json()
        assert data["ok"] is True
        assert data["copied"] == 0
        assert data["skipped"] == 2

    def test_select_invalid_type_returns_400(self, client, session_id):
        res = client.post(
            f"/api/session/{session_id}/select",
            json={"selected_files": "not-a-list"},
        )
        assert res.status_code == 400
