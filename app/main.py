from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import json

from app.services.session_service import SessionService
from app.services.repo_service import RepoService
from app.services.analysis_service import AnalysisService
from app.services.normalize_service import NormalizeService
from app.services.verify_service import VerifyService
from app.services.repair_service import RepairService

from app.analyzers.registry import AnalyzerRegistry
from app.analyzers.bandit import BanditAnalyzer
from app.analyzers.ruff import RuffAnalyzer
from app.analyzers.radon import RadonAnalyzer
from app.analyzers.trufflehog import TruffleHogAnalyzer

from app.normalizers.registry import NormalizerRegistry
from app.normalizers.bandit_normalizer import BanditNormalizer
from app.normalizers.ruff_normalizer import RuffNormalizer
from app.normalizers.radon_normalizer import RadonNormalizer
from app.normalizers.trufflehog_normalizer import TrufflehogNormalizer

from app.repair.registry import RepairRegistry
from app.repair.complexity_skip import ComplexitySkipRepairer
from app.repair.llm_repairer import LlmFindingRepairer
from app.llm.client import LlmClient


app = FastAPI(title="Quality Repair Tool")

app.mount("/static", StaticFiles(directory="app/ui/static"), name="static")


# ---------- Wiring ----------

analysis_service = AnalysisService(
    AnalyzerRegistry([
        BanditAnalyzer(),
        RuffAnalyzer(),
        RadonAnalyzer(),
        TruffleHogAnalyzer()
    ])
)

normalize_service = NormalizeService(
    NormalizerRegistry([
        BanditNormalizer(),
        RuffNormalizer(),
        RadonNormalizer(cc_threshold=10),
        TrufflehogNormalizer()
    ])
)

repair_service = RepairService(
    RepairRegistry([
        ComplexitySkipRepairer(),
        LlmFindingRepairer(LlmClient())
    ])
)

verify_service = VerifyService(analysis_service, normalize_service)


# ---------- UI ----------

@app.get("/")
def index():
    return FileResponse("app/ui/templates/index.html")


# ---------- Session ----------

@app.post("/api/session")
def create_session():
    sid = SessionService.create_session()
    return {"session_id": sid}


@app.post("/api/session/{sid}/upload")
async def upload(sid: str, file: UploadFile = File(...)):
    SessionService.ensure_dirs(sid)
    dest = SessionService.reports_dir(sid) / file.filename
    dest.write_bytes(await file.read())
    RepoService.prepare_from_upload(sid, dest)
    return {"status": "workspace_ready"}


@app.post("/api/session/{sid}/github")
def from_github(sid: str, body: dict):
    url = body.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing url")
    RepoService.prepare_from_github(sid, url)
    return {"status": "workspace_ready"}


@app.get("/api/session/{sid}/files")
def list_files(sid: str):
    raw = SessionService.workspace_raw_dir(sid)
    if not raw.exists():
        return []
    files = []
    for p in raw.rglob("*"):
        if p.is_file():
            files.append(str(p.relative_to(raw)))
    return sorted(files)


@app.get("/api/analyzers")
def list_analyzers():
    return ["bandit", "ruff", "radon", "trufflehog"]


@app.post("/api/session/{sid}/analyse")
def analyse(sid: str, body: dict):
    selected = body.get("analyzers", [])
    excluded_files = body.get("excluded_files", [])
    excluded_ext = body.get("excluded_extensions", [])

    raw = analysis_service.run(sid, selected_tools=selected)
    findings = normalize_service.run(
        sid
        # ,
        # selected_tools=selected,
        # excluded_files=excluded_files,
        # excluded_extensions=excluded_ext
    )
    return {"findings": len(findings)}


@app.post("/api/session/{sid}/repair")
def repair(sid: str, body: dict):
    model = body.get("model", "gpt-4o-mini")
    max_issues = body.get("max_issues", 10)
    token_budget = body.get("token_budget", 20000)

    return repair_service.run(
        session_id=sid,
        selected_tools=None,
        model=model,
        token_budget=token_budget,
        max_issues=max_issues
    )


@app.post("/api/session/{sid}/verify")
def verify(sid: str):
    return verify_service.run(sid, selected_tools=None)


@app.get("/api/session/{sid}/report")
def get_report(sid: str):
    p = SessionService.reports_dir(sid) / "findings_unified.json"
    return json.loads(p.read_text()) if p.exists() else []


@app.get("/api/session/{sid}/verification")
def get_verification(sid: str):
    p = SessionService.reports_dir(sid) / "verification_summary.json"
    return json.loads(p.read_text()) if p.exists() else {}
from app.services.selection_service import SelectionService

from fastapi import HTTPException

@app.post("/api/session/{sid}/select")
def select_files(sid: str, body: dict):
    selected = body.get("selected_files", [])
    if not isinstance(selected, list):
        raise HTTPException(status_code=400, detail="selected_files must be a list")

    result = SelectionService.apply_selection(sid, selected)

    if not result.get("ok", False):
        # if selection failed structurally, return 400 not 500
        raise HTTPException(status_code=400, detail=result)

    return result
