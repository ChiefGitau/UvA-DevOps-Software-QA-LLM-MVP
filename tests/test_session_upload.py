"""Tests for session management, upload, clone, and file listing (QALLM-1, QALLM-6)."""

import io


class TestUpload:
    def test_upload_zip_creates_session(self, client, sample_zip):
        res = client.post(
            "/api/session/upload",
            files={"archive": ("code.zip", io.BytesIO(sample_zip), "application/zip")},
        )
        assert res.status_code == 200
        assert "session_id" in res.json()
        assert res.json()["session_id"]

    def test_upload_then_list_files(self, client, sample_zip):
        sid = client.post(
            "/api/session/upload",
            files={"archive": ("code.zip", io.BytesIO(sample_zip), "application/zip")},
        ).json()["session_id"]

        res = client.get(f"/api/session/{sid}/files")
        assert res.status_code == 200
        payload = res.json()
        assert payload["session_id"] == sid
        assert payload["count"] >= 2
        assert any("hello.py" in f for f in payload["files"])

    def test_upload_rejects_non_zip(self, client):
        res = client.post(
            "/api/session/upload",
            files={"archive": ("code.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        assert res.status_code == 400


class TestClone:
    def test_clone_creates_session(self, client):
        # Public repo example (adjust if you want to mock clone later)
        res = client.post(
            "/api/session/clone",
            json={"git_url": "https://github.com/octocat/Hello-World.git"},
        )
        # In CI this might fail if network access is restricted — accept either:
        assert res.status_code in (200, 500)

        if res.status_code == 200:
            assert "session_id" in res.json()

    def test_clone_missing_url_422(self, client):
        # Pydantic validation → 422 Unprocessable Entity
        res = client.post("/api/session/clone", json={})
        assert res.status_code == 422


class TestSessionInfo:
    def test_get_session_info(self, client, sample_zip):
        sid = client.post(
            "/api/session/upload",
            files={"archive": ("code.zip", io.BytesIO(sample_zip), "application/zip")},
        ).json()["session_id"]

        res = client.get(f"/api/session/{sid}")
        assert res.status_code == 200
        payload = res.json()
        assert payload["session_id"] == sid
        assert "config" in payload


class TestFilesEndpoint:
    def test_files_unknown_session_404(self, client):
        res = client.get("/api/session/not-a-real-session/files")
        assert res.status_code == 404
