"""Build targeted prompts for LLM code repair (QALLM-12 / US-08).

Each prompt contains:
  - The finding details (tool, severity, message, rule_id)
  - The surrounding function/class context
  - Clear instructions to return ONLY the corrected code block
"""

from __future__ import annotations

from app.domain.models import Finding

SYSTEM_PROMPT = """\
You are an expert Python code repair assistant. You fix static analysis \
findings while preserving the original code's intent and style.

Rules:
1. Return ONLY the corrected code block, no explanations, no markdown fences.
2. Preserve the original indentation exactly.
3. Do NOT add imports unless strictly necessary for the fix.
4. If the finding is a false positive or cannot be fixed safely, return \
the original code unchanged and add a `# noqa` comment on the relevant line.
5. Keep changes minimal — fix only the reported issue.
"""


def build_repair_prompt(
    finding: Finding,
    context: str,
    context_start_line: int,
) -> str:
    """Build the user prompt for a single finding.

    Parameters
    ----------
    finding : Finding
        The unified finding to repair.
    context : str
        Source code surrounding the finding.
    context_start_line : int
        1-indexed line number where *context* begins in the original file.
    """
    parts = [
        "## Static analysis finding\n",
        f"- **Tool:** {finding.tool}",
        f"- **Type:** {finding.type}",
        f"- **Severity:** {finding.severity}",
        f"- **File:** {finding.file}",
        f"- **Line:** {finding.line}",
        f"- **Rule:** {finding.rule_id or 'N/A'}",
        f"- **Message:** {finding.message}",
        f"\n## Code context (starting at line {context_start_line})\n",
        f"```python\n{context}\n```",
        "\n## Task",
        "Return the corrected version of the code above. "
        "Fix ONLY the issue described. Return raw Python code, no markdown.",
    ]
    return "\n".join(parts)
