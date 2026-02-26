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
            filename_raw = str(r.get("filename") or "")
            line = r.get("line_number")

            # Normalize file path in a way snippet lookup can still find it
            file_rel = _to_workspace_relative(ctx.workspace_dir, filename_raw)

            sev = (r.get("issue_severity") or "LOW").upper()
            conf = (r.get("issue_confidence") or "LOW").upper()
            msg = r.get("issue_text") or "Bandit finding"
            rule = r.get("test_id") or r.get("test_name")

            # Prefer snippet from workspace; fallback to bandit 'code' when snippet not possible
            snippet = _snippet(ctx.workspace_dir, file_rel, int(line) if line else None, context=2)
            if not snippet:
                code = r.get("code")
                snippet = str(code) if code else None

            out.append(
                Finding(
                    tool="bandit",
                    type="SECURITY",
                    severity=sev if sev in {"LOW", "MEDIUM", "HIGH", "CRITICAL"} else "LOW",
                    file=file_rel,
                    line=int(line) if line else None,
                    message=msg,
                    rule_id=str(rule) if rule else None,
                    code_snippet=snippet,
                    extra={"confidence": conf},
                )
            )

        return out


def _to_workspace_relative(workspace: Path, filename: str) -> str:
    """
    Convert bandit filename to a path relative to workspace when possible.
    Handles absolute paths, './x.py', and already-relative paths.
    """
    if not filename:
        return ""

    # strip leading "./"
    s = filename.replace("\\", "/")
    if s.startswith("./"):
        s = s[2:]

    p = Path(s)
    if p.is_absolute():
        try:
            return p.relative_to(workspace).as_posix()
        except Exception:
            # If it's absolute but not under workspace, just use the basename as best effort
            return p.name

    return p.as_posix()


def _snippet(workspace: Path, rel_file: str, line: int | None, context: int = 2) -> str | None:
    if not rel_file or not line or line < 1:
        return None

    fp = workspace / rel_file
    if not fp.exists() or not fp.is_file():
        return None

    try:
        lines = fp.read_text(encoding="utf-8", errors="replace").splitlines()
        start = max(1, line - context)
        end = min(len(lines), line + context)
        chunk = []
        for i in range(start, end + 1):
            prefix = ">> " if i == line else "   "
            chunk.append(f"{prefix}{i:>4}: {lines[i-1]}")
        return "\n".join(chunk)
    except Exception:
        return None