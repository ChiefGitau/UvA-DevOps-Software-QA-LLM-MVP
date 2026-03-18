from __future__ import annotations

from app.graph.agents.base import BaseToolAgent
from app.graph.state import AgentState

SYSTEM_PROMPT = """\
You are a secrets-management engineer.
You will be given ONE trufflehog finding indicating a hardcoded credential. Remove it safely.

Rules:
- Replace the secret with os.environ.get('ENV_VAR_NAME') or equivalent.
- Choose an obvious, descriptive env-var name derived from context.
- Add a comment: # TODO: set ENV_VAR_NAME in deployment environment
- Never print, log, or re-expose the secret value.
- Return the COMPLETE corrected file. No markdown fences. No explanation.\
"""


class TruffleHogAgent(BaseToolAgent):
    TOOL_NAME = "trufflehog"
    SYSTEM_PROMPT = SYSTEM_PROMPT


def trufflehog_node(state: AgentState) -> dict:
    task = next((t for t in state.get("parallel_tasks", []) if t["tool"] == "trufflehog"), None)
    if task is None:
        return {"patches": [], "errors": []}
    agent = TruffleHogAgent(session_id=state["session_id"], provider=state.get("provider"))
    return agent.run(task)
