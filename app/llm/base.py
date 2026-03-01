"""Abstract base for LLM models (QALLM-12c).

Every registered model must implement the ``LLMModel`` interface.
The registry lists individual models (gpt-4o-mini, gpt-5-mini,
claude-3-5-haiku, ollama/llama3) — not providers.

Adding a new model = one class (or one constructor call) + one
registry.register() in containers.py.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Shared data classes ──────────────────────────────────────────


@dataclass
class LLMResponse:
    """Response from a single LLM call."""

    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    provider: str = ""
    error: str | None = None


@dataclass
class TokenTracker:
    """Accumulates token usage across multiple calls within a session."""

    budget: int = 0
    total_input: int = 0
    total_output: int = 0
    calls: int = 0
    errors: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return self.total_input + self.total_output

    @property
    def remaining(self) -> int:
        return max(0, self.budget - self.total_tokens)

    def record(self, resp: LLMResponse) -> None:
        self.calls += 1
        self.total_input += resp.input_tokens
        self.total_output += resp.output_tokens
        if resp.error:
            self.errors += 1
        self.history.append(
            {
                "call": self.calls,
                "input_tokens": resp.input_tokens,
                "output_tokens": resp.output_tokens,
                "model": resp.model,
                "provider": resp.provider,
                "error": resp.error,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "budget": self.budget,
            "total_input_tokens": self.total_input,
            "total_output_tokens": self.total_output,
            "total_tokens": self.total_tokens,
            "remaining": self.remaining,
            "calls": self.calls,
            "errors": self.errors,
        }


# ── Abstract model interface ─────────────────────────────────────


class LLMModel(ABC):
    """Interface every registered LLM model must implement.

    Each instance represents one callable model (e.g. gpt-4o-mini).
    The dropdown, API, and routing all use ``name()`` as the key.
    """

    @abstractmethod
    def name(self) -> str:
        """Display name shown in the UI dropdown (e.g. 'gpt-4o-mini')."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if the required API key / env vars are set."""

    @abstractmethod
    def chat(
        self,
        system: str,
        user: str,
        tracker: TokenTracker | None = None,
    ) -> LLMResponse:
        """Send a chat completion request and return the response."""


# Backward compatibility alias
LLMProvider = LLMModel
