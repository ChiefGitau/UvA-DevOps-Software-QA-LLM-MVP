"""LLM Provider Registry: mirrors the analyzer registry pattern (QALLM-12).

Usage::

    registry = LLMProviderRegistry()
    registry.register(OpenAIProvider())
    registry.register(AnthropicProvider())

    provider = registry.get("openai")       # specific provider
    provider = registry.pick("anthropic")   # raises if missing
    names    = registry.list()              # ["openai", "anthropic"]
    available = registry.list_configured()  # only those with API keys set
"""

from __future__ import annotations

from app.llm.base import LLMProvider


class LLMProviderRegistry:
    """Registry of available LLM providers."""

    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}

    def register(self, provider: LLMProvider) -> None:
        self._providers[provider.name()] = provider

    def get(self, name: str) -> LLMProvider | None:
        return self._providers.get(name)

    def pick(self, name: str) -> LLMProvider:
        p = self.get(name)
        if p is None:
            available = ", ".join(self.list())
            raise ValueError(f"Unknown LLM provider '{name}'. Available: {available}")
        if not p.is_configured():
            raise ValueError(f"LLM provider '{name}' is not configured. Set the required API key in your .env file.")
        return p

    def list(self) -> list[str]:
        """All registered provider names."""
        return list(self._providers.keys())

    def list_configured(self) -> list[str]:
        """Only providers whose API keys are set."""
        return [n for n, p in self._providers.items() if p.is_configured()]

    def get_default(self) -> LLMProvider | None:
        """Return the first configured provider, or None."""
        for p in self._providers.values():
            if p.is_configured():
                return p
        return None
