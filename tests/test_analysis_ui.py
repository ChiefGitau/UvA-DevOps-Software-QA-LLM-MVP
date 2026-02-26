"""Tests for unified analysis pipeline (QALLM-11) and minimal UI (QALLM-15)."""
import io
import json

from app.services.analysis_service import AnalysisService


class TestAnalyzersEndpoint:
    def test_list_analyzers_returns_all_four(self, client):
        res = client.get("/api/analyzers")
        assert res.status_code == 200
        tools = res.json()
        assert "bandit" in tools
        assert "ruff" in tools
        assert "radon" in tools
        assert "trufflehog" in tools


class TestAnalyseEndpoint:
    def _create_session_with_files(self, client, sample_zip):
        """Helper: upload zip → get session_id + file list."""
        upload_res = client.post(
            "/api/session/upload",
            files={"archive": ("code.zip", io.BytesIO(sample_zip), "application/zip")},
        )
        sid = upload_res.json()["session_id"]
        files_res = client.get(f"/api/session/{sid}/files")
        files = files_res.json()["files"]
        return sid, files

    def test_analyse_returns_findings(self, client, sample_zip):
        sid, files = self._create_session_with_files(client, sample_zip)

        res = client.post("/api/analyse", json={
            "session_id": sid,
            "selected_files": files,
        })
        assert res.status_code == 200
        data = res.json()
        assert "summary" in data
        assert "findings" in data
        assert data["summary"]["total"] >= 0
        assert isinstance(data["findings"], list)

    def test_analyse_with_specific_analyzer(self, client, sample_zip):
        sid, files = self._create_session_with_files(client, sample_zip)

        res = client.post("/api/analyse", json={
            "session_id": sid,
            "selected_files": files,
            "analyzers": ["bandit"],
        })
        assert res.status_code == 200
        data = res.json()
        # Only bandit findings
        for f in data["findings"]:
            assert f["tool"] == "bandit"

    def test_analyse_auto_selects_all_files(self, client, sample_zip):
        sid, _ = self._create_session_with_files(client, sample_zip)

        # Don't pass selected_files → should auto-select all
        res = client.post("/api/analyse", json={
            "session_id": sid,
        })
        assert res.status_code == 200

    def test_analyse_unknown_session_404(self, client):
        res = client.post("/api/analyse", json={
            "session_id": "nonexistent",
        })
        assert res.status_code == 404

    def test_summary_counts_match(self, client, sample_zip):
        sid, files = self._create_session_with_files(client, sample_zip)

        res = client.post("/api/analyse", json={
            "session_id": sid,
            "selected_files": files,
        })
        data = res.json()
        summary = data["summary"]
        assert summary["total"] == len(data["findings"])

        sev_sum = sum(summary["by_severity"].values())
        assert sev_sum == summary["total"]


class TestReportEndpoint:
    def test_report_before_analysis_404(self, client, sample_zip):
        upload_res = client.post(
            "/api/session/upload",
            files={"archive": ("code.zip", io.BytesIO(sample_zip), "application/zip")},
        )
        sid = upload_res.json()["session_id"]
        res = client.get(f"/api/session/{sid}/report")
        assert res.status_code == 404

    def test_report_after_analysis(self, client, sample_zip):
        upload_res = client.post(
            "/api/session/upload",
            files={"archive": ("code.zip", io.BytesIO(sample_zip), "application/zip")},
        )
        sid = upload_res.json()["session_id"]

        # Run analysis first
        client.post("/api/analyse", json={"session_id": sid})

        res = client.get(f"/api/session/{sid}/report")
        assert res.status_code == 200
        data = res.json()
        assert data["session_id"] == sid
        assert "findings" in data
        assert data["count"] == len(data["findings"])


class TestSummarize:
    def test_summarize_empty(self):
        result = AnalysisService.summarize([])
        assert result["total"] == 0
        assert all(v == 0 for v in result["by_severity"].values())


class TestMinimalUI:
    def test_root_serves_html(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]
        assert "Quality Repair Tool" in res.text

    def test_html_has_upload_form(self, client):
        html = client.get("/").text
        assert 'id="zipFile"' in html
        assert 'id="gitUrl"' in html

    def test_html_has_findings_table(self, client):
        html = client.get("/").text
        assert "<table>" in html
        assert "Severity" in html
        assert "findingsBody" in html
