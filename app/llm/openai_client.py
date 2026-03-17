"""Backward-compatibility shim — imports from the new provider architecture.

Kept so existing tests and code that import from here continue to work.
New code should import from ``app.llm.base`` and ``app.llm.openai_provider``.
"""

from app.llm.base import LLMResponse, TokenTracker  # noqa: F401
from app.llm.openai_provider import OpenAIProvider

_provider = OpenAIProvider()


def chat_completion(
    system: str,
    user: str,
    tracker: TokenTracker | None = None,
) -> LLMResponse:
    """Legacy wrapper: delegates to OpenAIProvider.chat()."""
    return _provider.chat(system, user, tracker)
