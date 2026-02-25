import json
from app.domain.models import Finding
from .base import FindingNormalizer, RawToolResult, NormalizerContext
from .util import to_workspace_relative, is_ignored_path

class TrufflehogNormalizer(FindingNormalizer):
    def tool_name(self) -> str:
        return "trufflehog"

    def normalize(self, raw: RawToolResult, ctx: NormalizerContext) -> list[Finding]:
        # JSONL
        lines = []
        if raw.artifact:
            p = ctx.reports_dir / raw.artifact
            if p.exists():
                lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        if not lines and raw.stdout.strip():
            lines = raw.stdout.splitlines()

        out: list[Finding] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                it = json.loads(line)
            except Exception:
                continue
            file = (((it.get("SourceMetadata") or {}).get("Data") or {}).get("Filesystem") or {}).get("file", "")
            file = to_workspace_relative(file or "", ctx.workspace_dir)
            if is_ignored_path(file):
                continue
            out.append(Finding(
                tool="trufflehog",
                type="SECRET",
                severity="HIGH",
                file=file,
                line=None,
                message=it.get("DetectorName") or "Potential secret detected",
                rule_id=it.get("DetectorType"),
                extra={}
            ))
        return out
