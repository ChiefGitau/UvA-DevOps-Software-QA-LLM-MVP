from __future__ import annotations

from app.graph.agents.base import BaseToolAgent
from app.graph.state import AgentState

SYSTEM_PROMPT = """\
You are a Python refactoring expert.
You will be given ONE radon complexity finding and the full source file.
Reduce the cyclomatic complexity of the reported function to below the threshold (default: 10).

Rules:
- Extract sub-functions, simplify conditionals, or use early returns.
- Preserve all existing behaviour and external interfaces.
- Return the COMPLETE corrected file. No markdown fences. No explanation.\
"""


class RadonAgent(BaseToolAgent):
    TOOL_NAME = "radon_cc"
    SYSTEM_PROMPT = SYSTEM_PROMPT


def radon_node(state: AgentState) -> dict:
    task = next(
        (t for t in state.get("parallel_tasks", []) if t["tool"] == "radon_cc"), None
    )
    if task is None:
        return {"patches": [], "errors": []}
    agent = RadonAgent(provider=state.get("provider"))
    return agent.run(task)
