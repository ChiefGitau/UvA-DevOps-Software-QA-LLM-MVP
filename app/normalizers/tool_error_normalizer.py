from app.domain.models import Finding
from .base import FindingNormalizer, RawToolResult, NormalizerContext

class ToolErrorNormalizer(FindingNormalizer):
    def tool_name(self) -> str:
        return "__tool_errors__"

    def normalize(self, raw: RawToolResult, ctx: NormalizerContext) -> list[Finding]:
        # Not used directly; NormalizeService will call this when a tool fails.
        raise NotImplementedError
