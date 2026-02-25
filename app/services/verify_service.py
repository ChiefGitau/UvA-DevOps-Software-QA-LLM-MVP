import json
from app.domain.models import VerificationReport, Summary
from .analysis_service import AnalysisService
from .normalize_service import NormalizeService
from .session_service import SessionService

class VerifyService:
    def __init__(self, analysis: AnalysisService, normalizer: NormalizeService):
        self.analysis = analysis
        self.normalizer = normalizer

    def run(self, session_id: str) -> dict:
        reports = SessionService.reports_dir(session_id)

        before = self._load_unified(reports / "findings_unified.json")
        before_summary = self._summary_from_unified(before)

        # Re-run tools + normalize
        self.analysis.run(session_id)
        after_findings = self.normalizer.run(session_id)
        after = [f.to_dict() for f in after_findings]
        after_summary = self.normalizer.summarize(after_findings)

        b_ids = {x["id"] for x in before}
        a_ids = {x["id"] for x in after}

        resolved_ids = sorted(list(b_ids - a_ids))
        new_ids = sorted(list(a_ids - b_ids))
        remaining_ids = sorted(list(b_ids & a_ids))

        ver = VerificationReport(
            session_id=session_id,
            before=before_summary,
            after=after_summary,
            resolved=len(resolved_ids),
            remaining=len(remaining_ids),
            new=len(new_ids),
            resolved_ids=resolved_ids[:50],
            new_ids=new_ids[:50],
        )

        (reports / "verification_summary.json").write_text(json.dumps(ver.__dict__, default=lambda o: o.__dict__, indent=2), encoding="utf-8")
        return ver.__dict__

    def _load_unified(self, path):
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def _summary_from_unified(self, items: list[dict]) -> Summary:
        by_sev = {k: 0 for k in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]}
        by_type = {k: 0 for k in ["SECURITY", "SMELL", "COMPLEXITY", "SECRET", "OTHER"]}
        for it in items:
            by_sev[(it.get("severity") or "LOW").upper()] += 1
            by_type[(it.get("type") or "OTHER").upper()] += 1
        return Summary(total=len(items), by_severity=by_sev, by_type=by_type)
