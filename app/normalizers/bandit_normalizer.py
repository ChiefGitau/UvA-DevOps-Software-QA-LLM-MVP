import json
from app.domain.models import Finding
from .base import FindingNormalizer, RawToolResult, NormalizerContext
from .util import to_workspace_relative, is_ignored_path

class BanditNormalizer(FindingNormalizer):
    def tool_name(self) -> str:
        return "bandit"

    def normalize(self, raw: RawToolResult, ctx: NormalizerContext) -> list[Finding]:
        # if bandit failed to write artifact, no results
        if raw.artifact:
            p = ctx.reports_dir / raw.artifact
            if not p.exists():
                return []
            try:
                data = json.loads(p.read_text(encoding="utf-8") or "{}")
            except Exception:
                return []
        else:
            return []

        out: list[Finding] = []
        for it in data.get("results", []) or []:
            sev = (it.get("issue_severity") or "LOW").upper()
            if sev not in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
                sev = "LOW"
            filename = to_workspace_relative(it.get("filename") or "", ctx.workspace_dir)
            if is_ignored_path(filename):
                continue
            out.append(Finding(
                tool="bandit",
                type="SECURITY",
                severity=sev,
                file=filename,
                line=it.get("line_number"),
                message=it.get("issue_text") or "Bandit issue",
                rule_id=it.get("test_id"),
                extra={"confidence": it.get("issue_confidence")}
            ))
        return out
