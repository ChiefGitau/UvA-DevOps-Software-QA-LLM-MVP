from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import Finding
from .base import ToolNormalizer, NormalizationContext


class BanditNormalizer(ToolNormalizer):
    tool_name = "bandit"

    def normalize(self, raw: dict, ctx: NormalizationContext) -> list[Finding]:
        artifact = raw.get("artifact") or "bandit.json"
        p = ctx.reports_dir / artifact
        if not p.exists():
            return []

        try:
            data = json.loads(p.read_text(encoding="utf-8") or "{}")
        except Exception:
            return []

        results = data.get("results") or []
        out: list[Finding] = []

        for r in results:
            filename = str(r.get("filename") or "")
            file_rel = _rel_path(ctx.workspace_dir, filename)

            sev = (r.get("issue_severity") or "LOW").upper()
            conf = (r.get("issue_confidence") or "LOW").upper()
            msg = r.get("issue_text") or "Bandit finding"
            rule = r.get("test_id") or r.get("test_name")

            line = r.get("line_number")
            code = r.get("code")

            out.append(
                Finding(
                    tool="bandit",
                    type="SECURITY",
                    severity=sev if sev in {"LOW", "MEDIUM", "HIGH", "CRITICAL"} else "LOW",
                    file=file_rel,
                    line=int(line) if line else None,
                    message=msg,
                    rule_id=str(rule) if rule else None,
                    code_snippet=str(code) if code else None,  # later overridden by SnippetService
                    extra={"confidence": conf},
                )
            )

        return out


def _rel_path(workspace: Path, filename: str) -> str:
    """
    Make bandit filename stable: relative to workspace when possible.
    Bandit may output absolute or relative paths.
    """
    if not filename:
        return ""
    try:
        f = Path(filename)
        if f.is_absolute():
            return f.relative_to(workspace).as_posix()
        # already relative
        return f.as_posix().lstrip("./")
    except Exception:
        return filename