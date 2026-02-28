from __future__ import annotations

from app.analyzers.bandit import BanditAnalyzer
from app.analyzers.radon import RadonAnalyzer
from app.analyzers.registry import AnalyzerRegistry
from app.analyzers.ruff import RuffAnalyzer
from app.analyzers.trufflehog import TruffleHogAnalyzer
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.ollama_provider import OllamaProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.registry import LLMProviderRegistry
from app.normalizers.bandit_normalizer import BanditNormalizer
from app.normalizers.radon_normalizer import RadonNormalizer
from app.normalizers.registry import NormalizerRegistry
from app.normalizers.ruff_normalizer import RuffNormalizer
from app.normalizers.trufflehog_normalizer import TruffleHogNormalizer


def build_analyzer_registry() -> AnalyzerRegistry:
    return AnalyzerRegistry([BanditAnalyzer(), RuffAnalyzer(), RadonAnalyzer(), TruffleHogAnalyzer()])


def build_normalizer_registry() -> NormalizerRegistry:
    return NormalizerRegistry(
        [
            BanditNormalizer(),
            RuffNormalizer(),
            RadonNormalizer(),
            TruffleHogNormalizer(),
        ]
    )


def build_llm_registry() -> LLMProviderRegistry:
    """Register all available LLM providers.

    To add a new provider:
    1. Create ``app/llm/my_provider.py`` implementing ``LLMProvider``
    2. ``registry.register(MyProvider())`` here
    3. Add env vars to ``.env.example``
    """
    registry = LLMProviderRegistry()
    registry.register(OpenAIProvider())
    registry.register(AnthropicProvider())
    registry.register(OllamaProvider())
    return registry
