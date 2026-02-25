import json
from app.domain.models import Finding
from .base import FindingNormalizer, RawToolResult, NormalizerContext
from .util import is_ignored_path

class RadonNormalizer(FindingNormalizer):
    def __init__(self, cc_threshold: int = 10):
        self.cc_threshold = cc_threshold

    def tool_name(self) -> str:
        return "radon"

    def normalize(self, raw: RawToolResult, ctx: NormalizerContext) -> list[Finding]:
        data = {}
        if raw.artifact:
            p = ctx.reports_dir / raw.artifact
            if p.exists():
                try:
                    data = json.loads(p.read_text(encoding="utf-8") or "{}")
                except Exception:
                    data = {}
        if not data and raw.stdout.strip():
            try:
                data = json.loads(raw.stdout)
            except Exception:
                data = {}

        out: list[Finding] = []
        for file, items in (data or {}).items():
            if is_ignored_path(file):
                continue
            for it in items or []:
                cc = it.get("complexity")
                if not isinstance(cc, int) or cc < self.cc_threshold:
                    continue
                sev = "MEDIUM" if cc < 20 else "HIGH"
                out.append(Finding(
                    tool="radon",
                    type="COMPLEXITY",
                    severity=sev,
                    file=file,
                    line=it.get("lineno"),
                    message=f"Cyclomatic complexity too high in {it.get('name')} (CC={cc})",
                    rule_id="CC",
                    extra={"function": it.get("name"), "complexity": cc}
                ))
        return out
