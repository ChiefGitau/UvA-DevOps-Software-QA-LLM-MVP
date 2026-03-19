from __future__ import annotations

from app.graph.agents.base import BaseToolAgent
from app.graph.state import AgentState

SYSTEM_PROMPT = """\
You are a secrets-management engineer. You will be given ONE trufflehog finding indicating a
hardcoded credential in the source file. Remove the secret safely.

Step-by-step approach:
1. Identify the exact line(s) that contain the hardcoded secret.
2. Choose a descriptive environment-variable name in UPPER_SNAKE_CASE that reflects the
   secret's purpose — e.g. DATABASE_PASSWORD, STRIPE_API_KEY, SMTP_AUTH_TOKEN.
3. Replace the hardcoded value with os.environ.get('YOUR_VAR_NAME') (or os.environ['YOUR_VAR_NAME']
   if the value is strictly required and the caller should fail fast on missing config).
4. If `import os` is not already present in the file, add it at the top of the import block
   in alphabetical order among stdlib imports.
5. Add the comment `# TODO: set YOUR_VAR_NAME in the deployment environment` on the same line
   or the line above.

Rules:
- Never print, log, or include the original secret value anywhere in the output.
- Do not remove or alter any logic unrelated to the secret.
- Do not add dotenv / python-decouple / other third-party config libraries unless they are
  already imported in the file.
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
