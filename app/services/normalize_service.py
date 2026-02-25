import json
from pathlib import Path
import logging

from app.domain.models import Finding, Summary
from app.services.session_service import SessionService
from app.normalizers.failure_policy import is_real_failure

from app.normalizers.base import RawToolResult, NormalizerContext
from app.normalizers.registry import NormalizerRegistry
from app.services.snippet_service import SnippetService

class NormalizeService:
    def __init__(self, registry: NormalizerRegistry):
        self.registry = registry

    def run(self, session_id: str) -> list[Finding]:
        reports = SessionService.reports_dir(session_id)
        ws = SessionService.workspace_dir(session_id)
        ctx = NormalizerContext(session_id=session_id, workspace_dir=ws, reports_dir=reports)

        raw_index_path = reports / "analysis_raw_index.json"
        raw_items = []
        if raw_index_path.exists():
            raw_items = json.loads(raw_index_path.read_text(encoding="utf-8") or "[]")

        findings: list[Finding] = []

        for r in raw_items:
            raw = RawToolResult(
                tool=r.get("tool", ""),
                exit_code=int(r.get("exit_code", 0)),
                stdout=r.get("stdout", "") or "",
                stderr=r.get("stderr", "") or "",
                artifact=r.get("artifact"),
            )

            normalizer = self.registry.by_tool(raw.tool)
            if normalizer:
                findings += normalizer.normalize(raw, ctx)

            # Convert tool failures into explicit findings (visibility!)
            artifact_path = (ctx.reports_dir / raw.artifact) if raw.artifact else None
            if is_real_failure(raw.tool, raw.exit_code, artifact_path):
                findings.append(Finding(
                    tool=raw.tool,
                    type="OTHER",
                    severity="MEDIUM",
                    file="",
                    line=None,
                    message=f"Tool execution failed (exit_code={raw.exit_code})",
                    rule_id="TOOL_EXECUTION",
                    extra={"stderr": (raw.stderr or "")[-2000:], "artifact": raw.artifact}
                ))

        # Enrich findings with source snippets
        logging.info("Enriching findings...")
        for f in findings:
            logger = logging.getLogger(__name__)
            logger.info("Adding code snippet for file: %s", f.file)

            if not f.code_snippet:
                f.code_snippet = SnippetService.get_snippet(
                    workspace=ws,
                    file_path=f.file,
                    line=f.line,
                    context=2
                )
        (reports / "findings_unified.json").write_text(
            json.dumps([f.to_dict() for f in findings], indent=2),
            encoding="utf-8"
        )
        return findings

    def summarize(self, findings: list[Finding]) -> Summary:
        by_sev = {k: 0 for k in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]}
        by_type = {k: 0 for k in ["SECURITY", "SMELL", "COMPLEXITY", "SECRET", "OTHER"]}
        for f in findings:
            by_sev[f.severity] += 1
            by_type[f.type] += 1
        return Summary(total=len(findings), by_severity=by_sev, by_type=by_type)
