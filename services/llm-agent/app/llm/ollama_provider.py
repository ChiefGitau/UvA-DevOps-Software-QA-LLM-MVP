from __future__ import annotations

import logging

from app.core.config import settings
from app.llm.base import LLMModel, LLMResponse, TokenTracker

logger = logging.getLogger(__name__)


class OllamaModel(LLMModel):
    def __init__(self, model_id: str | None = None, display_name: str | None = None) -> None:
        self._model_id = model_id or settings.OLLAMA_MODEL
        self._display_name = display_name or f"ollama/{self._model_id}"

    def name(self) -> str:
        return self._display_name

    def is_configured(self) -> bool:
        if not settings.OLLAMA_BASE_URL:
            return False
        try:
            import httpx
            with httpx.Client(timeout=2.0) as client:
                return client.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags").status_code == 200
        except Exception:
            return False

    def chat(self, system: str, user: str, tracker: TokenTracker | None = None) -> LLMResponse:
        if not self.is_configured():
            return LLMResponse(content="", provider="ollama", model=self._model_id, error="Ollama not reachable")
        if tracker and tracker.remaining <= 0:
            return LLMResponse(content="", provider="ollama", model=self._model_id, error="Token budget exhausted")
        try:
            import ollama
            client = ollama.Client(host=settings.OLLAMA_BASE_URL)
            response = client.chat(
                model=self._model_id,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                options={"temperature": 0.1},
            )
            content = response.get("message", {}).get("content", "")
            resp = LLMResponse(
                content=content,
                input_tokens=response.get("prompt_eval_count", 0),
                output_tokens=response.get("eval_count", 0),
                model=self._model_id,
                provider="ollama",
            )
        except Exception as e:
            logger.error("Ollama error [%s]: %s", self._model_id, e)
            resp = LLMResponse(content="", provider="ollama", model=self._model_id, error=str(e))
        if tracker:
            tracker.record(resp)
        return resp
