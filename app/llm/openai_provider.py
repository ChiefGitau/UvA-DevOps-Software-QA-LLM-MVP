"""OpenAI LLM provider (QALLM-12b).

Uses the ``openai`` Python SDK.  Reads configuration from env vars:
  - OPENAI_API_KEY   (required)
  - OPENAI_MODEL     (default: gpt-4o-mini)
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.llm.base import LLMProvider, LLMResponse, TokenTracker

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """GPT-5-mini, GPT-4o-mini (or any OpenAI chat model)."""

    def name(self) -> str:
        return "openai"

    def is_configured(self) -> bool:
        return bool(settings.OPENAI_API_KEY)

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
                error="OPENAI_API_KEY not configured",
            )

        if tracker and tracker.remaining <= 0:
            return LLMResponse(
                content="",
                provider=self.name(),
                error=f"Token budget exhausted ({tracker.budget} tokens used)",
            )

        try:
            import openai
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

            kwargs = dict(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
            )

            # GPT-5 family requires max_completion_tokens
            if settings.OPENAI_MODEL.startswith("gpt-5"):
                kwargs["max_completion_tokens"] = 4096
            else:
                kwargs["max_tokens"] = 4096

            response = client.chat.completions.create(**kwargs)

            choice = response.choices[0]
            usage = response.usage
            resp = LLMResponse(
                content=choice.message.content or "",
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                model=response.model,
                provider=self.name(),
            )

        except Exception as e:
            logger.error("OpenAI API error: %s", e)
            resp = LLMResponse(content="", provider=self.name(), error=str(e))
            logger.info(system)
            logger.info(user)

        if tracker:
            tracker.record(resp)

        return resp
