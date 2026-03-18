from __future__ import annotations

import operator
from typing import Annotated

from typing_extensions import TypedDict


class AgentTask(TypedDict):
    tool: str  # 'bandit' | 'ruff' | 'radon_cc' | 'trufflehog'
    findings: list  # Finding dicts for this agent
    files: list[str]  # Files this agent will touch


class PatchResult(TypedDict):
    finding_id: str
    file: str
    tool: str
    agent: str
    description: str
    unified_diff: str
    applied: bool
    error: str | None
    reviewer_note: str | None


class AgentState(TypedDict):
    session_id: str
    provider: str | None
    all_findings: list[dict]

    # Execution plan (set by Dispatcher)
    parallel_tasks: list[AgentTask]  # safe to run concurrently
    queued_tasks: list[AgentTask]  # file conflicts — run sequentially after

    # Accumulated results (reducer = list append)
    patches: Annotated[list[PatchResult], operator.add]
    errors: Annotated[list[dict], operator.add]
    review_notes: Annotated[list[dict], operator.add]

    # Final report (set by Orchestrator)
    final_report: dict
