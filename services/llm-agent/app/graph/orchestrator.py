from __future__ import annotations

import json
import logging
from pathlib import Path

from app.core.config import settings
from app.graph.state import AgentState

logger = logging.getLogger(__name__)


def orchestrator_node(state: AgentState) -> dict:
    """
    Collects all approved patches, generates repair_report.json, and sets
    final_report in state. Files are already written by BaseToolAgent, so
    this node only produces the report artifact.
    """
    session_id = state["session_id"]
    patches = state.get("patches", [])
    errors = state.get("errors", [])
    review_notes = state.get("review_notes", [])

    approved = [p for p in patches if p.get("applied")]
    rejected = [p for p in patches if not p.get("applied") and p.get("unified_diff")]
    failed = [p for p in patches if not p.get("unified_diff")]

    # Deduplicate: if the same finding_id appears multiple times (parallel +
    # conflict resolver), keep the last entry (most recent patch).
    seen: dict[str, dict] = {}
    for p in approved:
        seen[p["finding_id"]] = p
    deduped_approved = list(seen.values())

    repaired_count = len(deduped_approved)
    total_findings = len(state.get("all_findings", []))

    report = {
        "session_id": session_id,
        "provider": state.get("provider") or "auto",
        "total_findings": total_findings,
        "repaired_count": repaired_count,
        "rejected_count": len(rejected),
        "error_count": len(errors) + len(failed),
        "patches": deduped_approved,
        "rejected_patches": rejected,
        "errors": errors,
        "review_notes": review_notes,
        # Expose resolved_ids for frontend regression detection
        "resolved_ids": [p["finding_id"] for p in deduped_approved],
    }

    # Persist
    reports_dir = Path(settings.DATA_DIR) / session_id / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "repair_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    logger.info(
        "orchestrator: session=%s repaired=%d rejected=%d errors=%d",
        session_id,
        repaired_count,
        len(rejected),
        len(errors),
    )

    return {"final_report": report}
