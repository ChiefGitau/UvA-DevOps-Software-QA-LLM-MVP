from __future__ import annotations
from dataclasses import dataclass
from .base import FindingNormalizer

@dataclass
class NormalizerRegistry:
    normalizers: list[FindingNormalizer]

    def by_tool(self, tool: str) -> FindingNormalizer | None:
        for n in self.normalizers:
            if n.tool_name() == tool:
                return n
        return None
