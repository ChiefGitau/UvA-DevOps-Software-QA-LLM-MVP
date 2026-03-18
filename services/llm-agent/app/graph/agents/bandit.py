from __future__ import annotations

from app.graph.agents.base import BaseToolAgent
from app.graph.state import AgentState

SYSTEM_PROMPT = """\
You are a Python security engineer specialising in OWASP Top-10 and CWE vulnerabilities.
You will be given ONE bandit finding and the full source file it appears in.
Your ONLY job is to fix that specific security flaw with the minimal change possible.

Rules:
- Prefer safe stdlib alternatives (ast.literal_eval > eval, subprocess list args > shell=True,
  secrets.token_hex > random for security tokens).
- Never introduce new imports unless strictly required.
- Never change logic unrelated to the finding.
- Return the COMPLETE corrected file. No markdown fences. No explanation.\
"""


class BanditAgent(BaseToolAgent):
    TOOL_NAME = "bandit"
    SYSTEM_PROMPT = SYSTEM_PROMPT


def bandit_node(state: AgentState) -> dict:
    task = next((t for t in state.get("parallel_tasks", []) if t["tool"] == "bandit"), None)
    if task is None:
        return {"patches": [], "errors": []}
    agent = BanditAgent(session_id=state["session_id"], provider=state.get("provider"))
    return agent.run(task)
