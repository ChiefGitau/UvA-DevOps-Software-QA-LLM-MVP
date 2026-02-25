import json
from pathlib import Path
from app.domain.models import Finding
from .base import FindingNormalizer, RawToolResult, NormalizerContext
from .util import to_workspace_relative, is_ignored_path

class RuffNormalizer(FindingNormalizer):
    def tool_name(self) -> str:
        return "ruff"

    def normalize(self, raw: RawToolResult, ctx: NormalizerContext) -> list[Finding]:
        # Prefer artifact, fallback to stdout
        data = []
        if raw.artifact:
            p = ctx.reports_dir / raw.artifact
            if p.exists():
                try:
                    data = json.loads(p.read_text(encoding="utf-8") or "[]")
                except Exception:
                    data = []
        if not data and raw.stdout.strip():
            try:
                data = json.loads(raw.stdout)
            except Exception:
                data = []

        out: list[Finding] = []
        for it in data or []:
            loc = it.get("location") or {}
            filename = to_workspace_relative(it.get("filename") or "", ctx.workspace_dir)
            if is_ignored_path(filename):
                continue
            out.append(Finding(
                tool="ruff",
                type="SMELL",
                severity="LOW",
                file=filename,
                line=loc.get("row"),
                message=it.get("message") or "Ruff finding",
                rule_id=it.get("code"),
                extra={"fixable": it.get("fix") is not None}
            ))
        return out
