from __future__ import annotations

from app.graph.agents.base import BaseToolAgent
from app.graph.state import AgentState

SYSTEM_PROMPT = """\
You are a Python code-quality engineer. You will be given ONE ruff finding and the full source file.
Fix ONLY that single finding with the smallest possible change.

Common ruff rule IDs and their correct fixes:
- E501 line-too-long: wrap the line using implicit string concatenation, parentheses, or a backslash.
- E711/E712: use `is` / `is not` for comparisons to None/True/False.
- E721: use isinstance() instead of type() comparisons.
- F401 unused-import: remove the unused import; if it is re-exported, add `# noqa: F401`.
- F811 redefinition: remove or rename the duplicate definition.
- F841 local variable assigned but never used: remove the assignment, or prefix with `_`.
- I001 unsorted-imports: reorder the import block so stdlib < third-party < local, alphabetically within each group.
- N801/N802/N803/N806: rename classes (CapWords), functions/methods (snake_case), args (snake_case), variables (snake_case).
- B006 mutable-argument-default: replace `def f(x=[])` with `def f(x=None): if x is None: x = []`.
- B007 unused-loop-variable: prefix the unused loop variable with `_`.
- B008 function-call-in-default-argument: move the call inside the function body.
- C901 complex-structure: already handled by radon agent; if seen here, extract a helper function.
- SIM105: replace try/except/pass with contextlib.suppress(ExceptionType).
- SIM117: merge nested `with` statements into a single `with a, b:`.
- UP006/UP007: use built-in generics (`list[str]` not `List[str]`; `X | Y` not `Optional[X]`).
- W291/W293 trailing-whitespace: remove trailing spaces.
- W292 no-newline-at-end-of-file: add a final newline.
- W605 invalid-escape-sequence: prefix the string with `r` or double the backslash.

Rules:
- Never alter logic — only fix formatting, style, imports, or naming as required by the rule.
- When fixing I001 (import order), sort ALL imports in the file correctly in one pass.
- Return the COMPLETE corrected file. No markdown fences. No explanation.\
"""


class RuffAgent(BaseToolAgent):
    TOOL_NAME = "ruff"
    SYSTEM_PROMPT = SYSTEM_PROMPT


def ruff_node(state: AgentState) -> dict:
    task = next((t for t in state.get("parallel_tasks", []) if t["tool"] == "ruff"), None)
    if task is None:
        return {"patches": [], "errors": []}
    agent = RuffAgent(session_id=state["session_id"], provider=state.get("provider"))
    return agent.run(task)
