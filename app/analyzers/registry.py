from __future__ import annotations
from dataclasses import dataclass
from .base import StaticCodeAnalyzer

@dataclass
class AnalyzerRegistry:
    analyzers: list[StaticCodeAnalyzer]

    def all(self) -> list[StaticCodeAnalyzer]:
        return self.analyzers
