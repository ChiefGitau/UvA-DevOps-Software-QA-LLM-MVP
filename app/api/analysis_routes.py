from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.containers import build_analyzer_registry, build_normalizer_registry
from app.services.analysis_service import AnalysisService
from app.services.selection_service import SelectionService
from app.services.session_service import SessionService

router = APIRouter(prefix="/api", tags=["analysis"])

# Build once at module level
_analysis_service = AnalysisService(
    build_analyzer_registry(),
    build_normalizer_registry(),
)


class AnalyseRequest(BaseModel):
    session_id: str
    selected_files: list[str] | None = None
    analyzers: list[str] | None = None


@router.get("/analyzers")
def list_analyzers() -> list[str]:
    """List available static analysis tools."""
    return _analysis_service.analyzers.list()


@router.post("/analyse")
def analyse(req: AnalyseRequest) -> dict[str, Any]:
    """
    QALLM-11: Run all selected tools in a single request
    and return a unified findings report.

    Steps:
    1. Apply file selection (workspace_raw → workspace)
    2. Run analyzers
    3. Normalize raw output into unified Finding objects
    4. Return summary + findings
    """
    sid = req.session_id

    if not SessionService.session_exists(sid):
        raise HTTPException(status_code=404, detail="Session not found")

    # Auto-select: if selected_files provided, apply selection first;
    # otherwise copy ALL files from raw → active workspace
    if req.selected_files is not None:
        SelectionService.apply_selection(sid, req.selected_files)
    else:
        # Copy everything from workspace_raw
        raw = SessionService.workspace_raw_dir(sid)
        if raw.exists():
            all_files = SessionService.list_workspace_files(sid)
            SelectionService.apply_selection(sid, all_files)

    try:
        findings = _analysis_service.run(sid, selected_tools=req.analyzers)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    summary = AnalysisService.summarize(findings)
    return {
        "session_id": sid,
        "summary": summary,
        "findings": [f.to_dict() for f in findings],
    }


@router.get("/session/{session_id}/report")
def get_report(session_id: str) -> dict[str, Any]:
    """Return the persisted unified findings report."""
    if not SessionService.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    p = SessionService.reports_dir(session_id) / "findings_unified.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="No analysis run yet")

    findings = json.loads(p.read_text(encoding="utf-8"))
    return {
        "session_id": session_id,
        "count": len(findings),
        "findings": findings,
    }
