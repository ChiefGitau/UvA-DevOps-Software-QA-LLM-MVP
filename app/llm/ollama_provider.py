"""OLLAMA LLM provider (QALLM-12).

Not tested Yet!

Uses the ``anthropic`` Python SDK.  Reads configuration from env vars:
  - OLLAMA_BASE_URL   (default: http://localhost:11434)
  - OLLAMA_MODEL     (default: llama3.1:8b)
"""

from __future__ import annotations

import logging

import ollama

from app.core.config import Settings, settings
from app.llm.base import LLMProvider, LLMResponse, TokenTracker

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Local Ollama chat model using the official Python SDK."""

    def name(self) -> str:
        return "ollama"

    def is_configured(self) -> bool:
        return bool(settings.OLLAMA_BASE_URL)

    def chat(
            self,
            system: str,
            user: str,
            tracker: TokenTracker | None = None,
    ) -> LLMResponse:
        if tracker and tracker.remaining <= 0:
            return LLMResponse(
                content="",
                provider=self.name(),
                error=f"Token budget exhausted ({tracker.budget} tokens used)",
            )

        base_url = settings.OLLAMA_BASE_URL
        model = settings.OLLAMA_MODEL

        # Initialize the Ollama client with the configured base URL
        client = ollama.Client(host=base_url)

        try:
            # The official SDK handles the formatting and 404 errors nicely
            response = client.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                options={
                    "temperature": 0.2,
                }
            )

            content = response.get("message", {}).get("content", "")

            # Extract token counts
            prompt_tokens = response.get("prompt_eval_count", 0)
            completion_tokens = response.get("eval_count", 0)

            resp = LLMResponse(
                content=content,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                model=model,
                provider=self.name(),
            )

        except ollama.ResponseError as e:
            # This catches 404s (model not found) and other API errors
            logger.error("Ollama API error: %s", e.error)
            resp = LLMResponse(content="", provider=self.name(), error=e.error)
        except Exception as e:
            logger.error("Unexpected error connecting to Ollama: %s", e)
            resp = LLMResponse(content="", provider=self.name(), error=str(e))

        if tracker:
            tracker.record(resp)

        return resp
