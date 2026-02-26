from app.analyzers.radon import RadonAnalyzer


def test_radon_analyzer_writes_artifact_when_tool_missing(tmp_path, monkeypatch):
    reports = tmp_path / "reports"
    ws = tmp_path / "ws"
    reports.mkdir()
    ws.mkdir()

    monkeypatch.setattr("app.analyzers.radon.shutil.which", lambda _: None)

    r = RadonAnalyzer().analyze(ws, reports)

    assert r.tool == "radon"
    assert r.exit_code == 127
    assert (reports / "radon_cc.json").exists()


def test_radon_analyzer_writes_stdout_to_json(tmp_path, monkeypatch):
    reports = tmp_path / "reports"
    ws = tmp_path / "ws"
    reports.mkdir()
    ws.mkdir()

    monkeypatch.setattr("app.analyzers.radon.shutil.which", lambda _: "/usr/bin/radon")

    class Dummy:
        exit_code = 0
        stdout = "{}"
        stderr = ""

    monkeypatch.setattr("app.analyzers.radon.run_cmd", lambda *args, **kwargs: Dummy())

    r = RadonAnalyzer().analyze(ws, reports)
    assert r.exit_code == 0
    assert (reports / "radon_cc.json").read_text(encoding="utf-8").strip() == "{}"