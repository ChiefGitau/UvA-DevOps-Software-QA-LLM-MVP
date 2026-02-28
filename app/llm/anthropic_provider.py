"""Anthropic Claude LLM provider (QALLM-12).

Uses the ``anthropic`` Python SDK.  Reads configuration from env vars:
  - ANTHROPIC_API_KEY   (required)
  - ANTHROPIC_MODEL     (default: claude-3-5-haiku-20241022)
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.llm.base import LLMProvider, LLMResponse, TokenTracker

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """Claude 3.5 Haiku (or any Anthropic chat model)."""

    def name(self) -> str:
        return "anthropic"

    def is_configured(self) -> bool:
        return bool(settings.ANTHROPIC_API_KEY)

    def chat(
        self,
        system: str,
        user: str,
        tracker: TokenTracker | None = None,
    ) -> LLMResponse:
        if not self.is_configured():
            return LLMResponse(
                content="",
                provider=self.name(),
                error="ANTHROPIC_API_KEY not configured",
            )

        if tracker and tracker.remaining <= 0:
            return LLMResponse(
                content="",
                provider=self.name(),
                error=f"Token budget exhausted ({tracker.budget} tokens used)",
            )

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            response = client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=4096,
                system=system,
                messages=[
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
            )

            content = ""
            for block in response.content:
                if block.type == "text":
                    content += block.text

            usage = response.usage
            resp = LLMResponse(
                content=content,
                input_tokens=usage.input_tokens if usage else 0,
                output_tokens=usage.output_tokens if usage else 0,
                model=response.model,
                provider=self.name(),
            )

        except Exception as e:
            logger.error("Anthropic API error: %s", e)
            resp = LLMResponse(content="", provider=self.name(), error=str(e))

        if tracker:
            tracker.record(resp)

        return resp
