from __future__ import annotations

from app.analyzers.registry import AnalyzerRegistry
from app.analyzers.bandit import BanditAnalyzer
from app.analyzers.ruff import RuffAnalyzer

from app.normalizers.registry import NormalizerRegistry
from app.normalizers.bandit_normalizer import BanditNormalizer
from app.normalizers.ruff_normalizer import RuffNormalizer


def build_analyzer_registry() -> AnalyzerRegistry:
    return AnalyzerRegistry([BanditAnalyzer(), RuffAnalyzer])


def build_normalizer_registry() -> NormalizerRegistry:
    return NormalizerRegistry([BanditNormalizer(), RuffNormalizer])