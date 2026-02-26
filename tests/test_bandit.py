from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import Finding
from app.normalizers.base import ToolNormalizer, NormalizationContext


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

            # Prefer real snippet from workspace file; fallback to bandit "code"
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


def _rel_path(workspace: Path, filename: str) -> str:
    if not filename:
        return ""
    try:
        f = Path(filename)
        if f.is_absolute():
            return f.relative_to(workspace).as_posix()
        return f.as_posix().lstrip("./")
    except Exception:
        return filename


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