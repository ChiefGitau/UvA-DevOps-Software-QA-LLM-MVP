from app.domain.models import Finding, Patch
from .base import FindingRepairer, RepairContext

class ComplexitySkipRepairer(FindingRepairer):
    def supports(self, finding: Finding) -> bool:
        return finding.tool == "radon" or finding.type == "COMPLEXITY"

    def repair(self, finding: Finding, ctx: RepairContext) -> Patch:
        return Patch(
            finding_id=finding.id,
            description="Skipped: complexity findings require refactoring (advisory).",
            unified_diff="",
            applied=False,
            error="SKIPPED"
        )
