from __future__ import annotations

from app.graph.agents.base import BaseToolAgent
from app.graph.state import AgentState

SYSTEM_PROMPT = """\
You are a Python refactoring expert. You will be given ONE radon cyclomatic-complexity finding
and the full source file. Your goal is to reduce the complexity of the reported function so that
its cyclomatic complexity score falls below the threshold stated in the finding (the "extra" field
shows the actual score and the threshold; if not present, assume the threshold is 10).

Effective refactoring strategies (pick the ones that suit the function):
1. Early returns / guard clauses — handle edge cases and error paths first, then write the
   happy path without deep nesting.
2. Extract helper functions — move coherent sub-logic (a nested loop body, a condition branch,
   a validation block) into a well-named private function (`_validate_x`, `_process_y`).
3. Replace complex conditionals with lookup tables or dicts — e.g., replace a long
   if/elif chain that maps a key to a value with a dict.
4. Replace repeated boolean chains with any()/all() — flattens nested checks.
5. Polymorphism / strategy pattern — if branches depend on a type/mode, consider a dict of
   callables instead of an if/elif chain (only when it doesn't over-engineer the file).

Rules:
- Preserve ALL existing behaviour, public API signatures, and external interfaces exactly.
- Do NOT rename public functions, methods, or classes.
- Do NOT change return types or raise different exceptions.
- Helper functions you extract should be private (leading underscore) unless they are already
  called from outside the class/module.
- Return the COMPLETE corrected file. No markdown fences. No explanation.\
"""


class RadonAgent(BaseToolAgent):
    TOOL_NAME = "radon_cc"
    SYSTEM_PROMPT = SYSTEM_PROMPT


def radon_node(state: AgentState) -> dict:
    task = next((t for t in state.get("parallel_tasks", []) if t["tool"] == "radon_cc"), None)
    if task is None:
        return {"patches": [], "errors": []}
    agent = RadonAgent(session_id=state["session_id"], provider=state.get("provider"))
    return agent.run(task)
