from __future__ import annotations

from app.analyzers.registry import AnalyzerRegistry
from app.analyzers.bandit import BanditAnalyzer

from app.normalizers.registry import NormalizerRegistry
from app.normalizers.bandit_normalizer import BanditNormalizer


def build_analyzer_registry() -> AnalyzerRegistry:
    return AnalyzerRegistry([BanditAnalyzer()])


def build_normalizer_registry() -> NormalizerRegistry:
    return NormalizerRegistry([BanditNormalizer()])