"""Agent repair API endpoints."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.graph.graph import graph
from app.graph.state import AgentState
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["repair-agent"])


class AgentRepairRequest(BaseModel):
    finding_ids: list[str] | None = Field(
        None,
        description="Specific finding IDs to repair. If omitted, uses all findings "
        "up to MAX_REPAIR_ISSUES.",
    )
    provider: str | None = Field(
        None,
        description="LLM model name (e.g. 'gpt-4o-mini', 'claude-haiku-4-5-20251001'). "
        "Defaults to the first configured provider.",
    )


@router.post(
    "/repair-agent/{session_id}",
    summary="Repair findings via agent pipeline",
    response_description="Patches and report from the multi-agent LangGraph pipeline",
)
async def repair_agent(
    session_id: str, req: AgentRepairRequest | None = None
) -> dict[str, Any]:
    """Invoke the LangGraph multi-agent repair pipeline for a session.

    Runs a Dispatcher → parallel tool agents → ConflictResolver →
    Reviewer → Orchestrator graph. Returns the same response shape as the
    simple repair endpoint so the frontend works unchanged.
    """
    if not SessionService.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    reports = SessionService.reports_dir(session_id)
    findings_path = reports / "findings_unified.json"

    if not findings_path.exists():
        raise HTTPException(
            status_code=400,
            detail="No analysis run yet. Run POST /api/analyse first.",
        )

    body = req or AgentRepairRequest()

    # Load raw findings so we can pre-filter by finding_ids if supplied
    raw: list[dict] = json.loads(findings_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        raw = raw.get("findings", [])

    if body.finding_ids:
        id_set = set(body.finding_ids)
        raw = [f for f in raw if f.get("id") in id_set]

    initial_state: AgentState = {
        "session_id": session_id,
        "provider": body.provider,
        "all_findings": raw,
        "parallel_tasks": [],
        "queued_tasks": [],
        "patches": [],
        "errors": [],
        "review_notes": [],
        "final_report": {},
    }

    try:
        result_state: AgentState = await graph.ainvoke(initial_state)
    except Exception as e:
        logger.error("agent pipeline failed for session %s: %s", session_id, e)
        raise HTTPException(status_code=500, detail=f"Agent pipeline error: {e}")

    report = result_state.get("final_report", {})

    # Return shape compatible with the simple service so renderRepairResults() works
    return {
        "session_id": session_id,
        "patches": report.get("patches", []),
        "repaired_count": report.get("repaired_count", 0),
        "provider_used": report.get("provider", body.provider or "auto"),
        "token_usage": {},  # LangGraph agents use per-call tracking; no single tracker
        "agent_report": report,
    }


@router.get(
    "/repair-agent/{session_id}/report",
    summary="Get persisted agent repair report",
    response_description="Previously computed agent repair report",
)
def get_agent_repair_report(session_id: str) -> dict[str, Any]:
    """Retrieve the persisted agent repair report for a session."""
    if not SessionService.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    p = SessionService.reports_dir(session_id) / "repair_report.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="No agent repair run yet")

    return json.loads(p.read_text(encoding="utf-8"))
