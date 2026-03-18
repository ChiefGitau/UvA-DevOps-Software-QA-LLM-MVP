from __future__ import annotations

from app.graph.agents.base import BaseToolAgent
from app.graph.state import AgentState

SYSTEM_PROMPT = """\
You are a Python code-quality engineer.
You will be given ONE ruff finding (lint or style) and the full source file.
Fix only that finding.

Rules:
- Follow PEP 8 / ruff's own fix suggestions where applicable.
- Never alter logic, only formatting/style/unused imports.
- Return the COMPLETE corrected file. No markdown fences. No explanation.\
"""


class RuffAgent(BaseToolAgent):
    TOOL_NAME = "ruff"
    SYSTEM_PROMPT = SYSTEM_PROMPT


def ruff_node(state: AgentState) -> dict:
    task = next(
        (t for t in state.get("parallel_tasks", []) if t["tool"] == "ruff"), None
    )
    if task is None:
        return {"patches": [], "errors": []}
    agent = RuffAgent(provider=state.get("provider"))
    return agent.run(task)
