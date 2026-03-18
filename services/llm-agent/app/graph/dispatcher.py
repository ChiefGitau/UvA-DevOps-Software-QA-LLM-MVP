from __future__ import annotations

import json
import logging
from pathlib import Path

from app.core.config import settings
from app.domain.models import Finding
from app.graph.state import AgentState, AgentTask

logger = logging.getLogger(__name__)

TOOL_PRIORITY: dict[str, int] = {
    "trufflehog": 0,
    "bandit": 1,
    "ruff": 2,
    "radon_cc": 3,
}
SEV_PRIORITY: dict[str, int] = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
}


def _file_priority(finding: dict) -> tuple[int, int]:
    sev = finding.get("severity", "LOW")
    tool = finding.get("tool", "ruff")
    return (SEV_PRIORITY.get(sev, 3), TOOL_PRIORITY.get(tool, 3))


def dispatcher_node(state: AgentState) -> dict:
    """
    Groups findings by tool, detects file conflicts, and produces
    parallel_tasks + queued_tasks for the rest of the graph.
    """
    session_id = state["session_id"]
    findings_path = (
        Path(settings.DATA_DIR) / session_id / "reports" / "findings_unified.json"
    )

    # Load findings
    raw: list[dict] = []
    if state.get("all_findings"):
        raw = state["all_findings"]
    elif findings_path.exists():
        with findings_path.open() as f:
            data = json.load(f)
        raw = data if isinstance(data, list) else data.get("findings", [])
    else:
        logger.warning("dispatcher: no findings source for session %s", session_id)

    # Filter: skip secrets with no file path, cap total
    filtered: list[dict] = []
    for f in raw:
        if f.get("tool") == "trufflehog" and not f.get("file"):
            continue
        filtered.append(f)

    filtered = filtered[: settings.MAX_REPAIR_ISSUES]

    # Group by tool
    by_tool: dict[str, list[dict]] = {}
    for f in filtered:
        tool = f.get("tool", "unknown")
        by_tool.setdefault(tool, []).append(f)

    # Detect file conflicts: file touched by >1 tool
    file_to_tools: dict[str, list[str]] = {}
    for tool, findings in by_tool.items():
        for f in findings:
            fp = f.get("file", "")
            if fp:
                file_to_tools.setdefault(fp, []).append(tool)

    contested_files: set[str] = {
        fp for fp, tools in file_to_tools.items() if len(tools) > 1
    }

    # For each contested file, find the winning tool (lowest priority score)
    file_winner: dict[str, str] = {}
    for fp in contested_files:
        candidates = [f for f in filtered if f.get("file") == fp]
        best = min(candidates, key=_file_priority)
        file_winner[fp] = best.get("tool", "")

    # Build parallel tasks (each tool gets its non-contested files, plus
    # contested files it won)
    parallel_tasks: list[AgentTask] = []
    queued_tasks: list[AgentTask] = []

    for tool, findings in by_tool.items():
        parallel_findings = [
            f for f in findings
            if f.get("file", "") not in contested_files
            or file_winner.get(f.get("file", "")) == tool
        ]
        deferred_findings = [
            f for f in findings
            if f.get("file", "") in contested_files
            and file_winner.get(f.get("file", "")) != tool
        ]

        if parallel_findings:
            parallel_tasks.append(AgentTask(
                tool=tool,
                findings=parallel_findings,
                files=list({f.get("file", "") for f in parallel_findings}),
            ))

        if deferred_findings:
            # Sort deferred by priority so ConflictResolver processes them in order
            deferred_findings.sort(key=_file_priority)
            queued_tasks.append(AgentTask(
                tool=tool,
                findings=deferred_findings,
                files=list({f.get("file", "") for f in deferred_findings}),
            ))

    # Sort queued tasks by best priority in the group
    queued_tasks.sort(key=lambda t: min(_file_priority(f) for f in t["findings"]))

    logger.info(
        "dispatcher: %d findings → %d parallel tasks, %d queued tasks",
        len(filtered),
        len(parallel_tasks),
        len(queued_tasks),
    )

    return {
        "all_findings": filtered,
        "parallel_tasks": parallel_tasks,
        "queued_tasks": queued_tasks,
        "patches": [],
        "errors": [],
        "review_notes": [],
    }
