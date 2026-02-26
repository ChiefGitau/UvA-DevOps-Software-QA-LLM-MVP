from pathlib import Path
from app.core.containers import build_analyzer_registry, build_normalizer_registry
from app.services.session_service import SessionService
from app.normalizers.base import NormalizationContext

sid = SessionService.create_session("upload", None)

# Put a demo file in workspace_raw/workspace manually for test, or reuse your existing session flow.
ws = SessionService.workspace_active_dir(sid)
ws.mkdir(parents=True, exist_ok=True)

(ws / "x.py").write_text("import pickle\nimport subprocess\nsubprocess.call('ls', shell=True)\n", encoding="utf-8")

reports = SessionService.reports_dir(sid)
reports.mkdir(parents=True, exist_ok=True)

areg = build_analyzer_registry()
nreg = build_normalizer_registry()

raw_results = []
for a in areg.pick(["bandit"]):
    raw = a.analyze(ws, reports)
    raw_results.append(raw.__dict__)

ctx = NormalizationContext(session_id=sid, workspace_dir=ws, reports_dir=reports)
normalizer = nreg.get("bandit")
findings = normalizer.normalize(raw_results[0], ctx) if normalizer else []

print("RAW:", raw_results)
print("FINDINGS:", [f.to_dict() for f in findings])