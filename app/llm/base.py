"""Abstract base for LLM providers (QALLM-12b).

Every provider must implement a single ``chat()`` method that accepts a
system prompt, user prompt, and optional TokenTracker.  The registry
pattern mirrors the analyzer registry so adding a new provider is a
one-file + one-register operation.
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


# Abstract provider


class LLMProvider(ABC):
    """Interface every LLM provider must implement."""

    @abstractmethod
    def name(self) -> str:
        """Short identifier used in API requests, e.g. ``"openai"``."""

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
