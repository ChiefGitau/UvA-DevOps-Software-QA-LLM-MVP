from __future__ import annotations

import difflib
import logging
from pathlib import Path

from app.core.config import settings
from app.core.containers import build_llm_registry
from app.graph.state import AgentTask, PatchResult

logger = logging.getLogger(__name__)


class BaseToolAgent:
    """
    Shared logic for all tool-specific repair agents.

    Subclasses only need to define SYSTEM_PROMPT and TOOL_NAME.
    """

    TOOL_NAME: str = "unknown"
    SYSTEM_PROMPT: str = ""

    def __init__(self, provider: str | None = None) -> None:
        self._registry = build_llm_registry()
        if provider:
            self._model = self._registry.pick(provider)
        else:
            m = self._registry.get_default()
            if m is None:
                raise RuntimeError("No LLM provider configured.")
            self._model = m

    # ------------------------------------------------------------------
    # Public entry point called by each node function
    # ------------------------------------------------------------------

    def run(self, task: AgentTask) -> dict:
        patches: list[PatchResult] = []
        errors: list[dict] = []

        # Group findings by file so we only read each file once
        by_file: dict[str, list[dict]] = {}
        for f in task["findings"]:
            fp = f.get("file", "")
            by_file.setdefault(fp, []).append(f)

        for file_path, findings in by_file.items():
            source = self._read_source(file_path)
            if source is None:
                for f in findings:
                    errors.append({
                        "finding_id": f.get("id", ""),
                        "file": file_path,
                        "tool": self.TOOL_NAME,
                        "error": f"File not found: {file_path}",
                    })
                continue

            # Apply findings one at a time, feeding patched output forward
            current_source = source
            for finding in findings:
                result, current_source = self._repair_one(
                    finding, file_path, current_source
                )
                if result["applied"]:
                    patches.append(result)
                    # Write the patched file back so later agents see it
                    self._write_source(file_path, current_source)
                else:
                    errors.append({
                        "finding_id": finding.get("id", ""),
                        "file": file_path,
                        "tool": self.TOOL_NAME,
                        "error": result.get("error") or "Unknown error",
                    })

        return {"patches": patches, "errors": errors}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _repair_one(
        self, finding: dict, file_path: str, source: str
    ) -> tuple[PatchResult, str]:
        user_prompt = self._build_user_prompt(finding, source)
        resp = self._model.chat(system=self.SYSTEM_PROMPT, user=user_prompt)

        if resp.error or not resp.content.strip():
            result: PatchResult = {
                "finding_id": finding.get("id", ""),
                "file": file_path,
                "tool": self.TOOL_NAME,
                "agent": self.__class__.__name__,
                "description": finding.get("message", ""),
                "unified_diff": "",
                "applied": False,
                "error": resp.error or "Empty LLM response",
                "reviewer_note": None,
            }
            return result, source

        patched = resp.content.strip()
        diff = self._make_diff(source, patched, file_path)

        result = {
            "finding_id": finding.get("id", ""),
            "file": file_path,
            "tool": self.TOOL_NAME,
            "agent": self.__class__.__name__,
            "description": finding.get("message", ""),
            "unified_diff": diff,
            "applied": True,
            "error": None,
            "reviewer_note": None,
        }
        return result, patched

    def _build_user_prompt(self, finding: dict, source: str) -> str:
        return (
            f"Finding:\n"
            f"  tool: {finding.get('tool')}\n"
            f"  rule: {finding.get('rule_id', 'N/A')}\n"
            f"  severity: {finding.get('severity', 'N/A')}\n"
            f"  line: {finding.get('line', 'N/A')}\n"
            f"  message: {finding.get('message', '')}\n"
            f"\nSource file ({finding.get('file', '')}):\n"
            f"```python\n{source}\n```"
        )

    @staticmethod
    def _make_diff(original: str, patched: str, file_path: str) -> str:
        orig_lines = original.splitlines(keepends=True)
        patched_lines = patched.splitlines(keepends=True)
        diff = difflib.unified_diff(
            orig_lines,
            patched_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
        )
        return "".join(diff)

    def _read_source(self, file_path: str) -> str | None:
        path = Path(file_path)
        if not path.is_absolute():
            path = Path(settings.DATA_DIR) / file_path
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning("%s: file not found: %s", self.TOOL_NAME, file_path)
            return None

    def _write_source(self, file_path: str, content: str) -> None:
        path = Path(file_path)
        if not path.is_absolute():
            path = Path(settings.DATA_DIR) / file_path
        try:
            path.write_text(content, encoding="utf-8")
        except OSError as e:
            logger.error("%s: failed to write %s: %s", self.TOOL_NAME, file_path, e)
