from __future__ import annotations

def build_analyzer_registry():
    from app.analyzers.bandit import BanditAnalyzer
    from app.analyzers.radon import RadonAnalyzer
    from app.analyzers.registry import AnalyzerRegistry
    from app.analyzers.ruff import RuffAnalyzer
    from app.analyzers.trufflehog import TruffleHogAnalyzer
    return AnalyzerRegistry([BanditAnalyzer(), RuffAnalyzer(), RadonAnalyzer(), TruffleHogAnalyzer()])


def build_normalizer_registry():
    from app.normalizers.bandit_normalizer import BanditNormalizer
    from app.normalizers.radon_normalizer import RadonNormalizer
    from app.normalizers.registry import NormalizerRegistry
    from app.normalizers.ruff_normalizer import RuffNormalizer
    from app.normalizers.trufflehog_normalizer import TruffleHogNormalizer
    return NormalizerRegistry(
        [
            BanditNormalizer(),
            RuffNormalizer(),
            RadonNormalizer(),
            TruffleHogNormalizer(),
        ]
    )
