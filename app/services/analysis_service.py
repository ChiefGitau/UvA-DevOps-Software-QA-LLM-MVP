from __future__ import annotations

import json
import logging

from app.analyzers.registry import AnalyzerRegistry
from app.domain.models import Finding
from app.normalizers.base import NormalizationContext
from app.normalizers.registry import NormalizerRegistry
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)


class AnalysisService:
    """
    Orchestrates: run selected analyzers → normalize raw output → unified findings.
    """

    def __init__(
        self,
        analyzer_registry: AnalyzerRegistry,
        normalizer_registry: NormalizerRegistry,
    ):
        self.analyzers = analyzer_registry
        self.normalizers = normalizer_registry

    def run(
        self,
        session_id: str,
        selected_tools: list[str] | None = None,
    ) -> list[Finding]:
        workspace = SessionService.workspace_active_dir(session_id)
        reports = SessionService.reports_dir(session_id)
        reports.mkdir(parents=True, exist_ok=True)

        if not workspace.exists() or not any(workspace.rglob("*.py")):
            raise RuntimeError("Active workspace has no Python files. Did you select files first?")

        # Phase 1: Run analyzers
        raw_results: list[dict] = []
        for analyzer in self.analyzers.pick(selected_tools):
            logger.info(
                "Running %s ...",
                analyzer.tool_name(),
                extra={"session_id": session_id},
            )
            result = analyzer.analyze(workspace, reports)
            raw_results.append(result.__dict__)

        # Persist raw index
        (reports / "analysis_raw_index.json").write_text(
            json.dumps(raw_results, indent=2),
            encoding="utf-8",
        )

        # Phase 2: Normalize → unified findings
        ctx = NormalizationContext(
            session_id=session_id,
            workspace_dir=workspace,
            reports_dir=reports,
        )

        findings: list[Finding] = []
        for raw in raw_results:
            norm = self.normalizers.get(raw.get("tool", ""))
            if norm:
                findings.extend(norm.normalize(raw, ctx))

        # Persist unified report
        (reports / "findings_unified.json").write_text(
            json.dumps([f.to_dict() for f in findings], indent=2),
            encoding="utf-8",
        )

        logger.info(
            "Analysis complete: %d findings",
            len(findings),
            extra={"session_id": session_id},
        )
        return findings

    @staticmethod
    def summarize(findings: list[Finding]) -> dict:
        by_sev = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        by_type = {"SECURITY": 0, "SMELL": 0, "COMPLEXITY": 0, "SECRET": 0, "OTHER": 0}
        for f in findings:
            by_sev[f.severity] = by_sev.get(f.severity, 0) + 1
            by_type[f.type] = by_type.get(f.type, 0) + 1
        return {
            "total": len(findings),
            "by_severity": by_sev,
            "by_type": by_type,
        }
