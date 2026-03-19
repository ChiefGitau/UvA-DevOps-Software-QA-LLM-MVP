from __future__ import annotations

import json
import logging

from app.core.config import settings
from app.llm.base import LLMModel, LLMResponse, TokenTracker

logger = logging.getLogger(__name__)

REPAIR_SCHEMA = {
    "name": "code_repair",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "corrected_code": {
                "type": "string",
                "description": "The corrected code block, raw Python, no markdown.",
            },
        },
        "required": ["corrected_code"],
        "additionalProperties": False,
    },
}


class OpenAIModel(LLMModel):
    def __init__(
        self, model_id: str = "gpt-4o-mini", display_name: str | None = None, use_structured: bool = False
    ) -> None:
        self._model_id = model_id
        self._display_name = display_name or model_id
        self._use_structured = use_structured
        self._is_gpt5 = model_id.startswith("gpt-5")

    def name(self) -> str:
        return self._display_name

    def is_configured(self) -> bool:
        return bool(settings.OPENAI_API_KEY)

    def chat(self, system: str, user: str, tracker: TokenTracker | None = None) -> LLMResponse:
        if not self.is_configured():
            return LLMResponse(
                content="", provider="openai", model=self._model_id, error="OPENAI_API_KEY not configured"
            )
        if tracker and tracker.remaining <= 0:
            return LLMResponse(content="", provider="openai", model=self._model_id, error="Token budget exhausted")
        try:
            import openai

            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            kwargs: dict = {
                "model": self._model_id,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            }
            if self._is_gpt5:
                kwargs["max_completion_tokens"] = 4096
            else:
                kwargs["temperature"] = 0.1
                kwargs["max_tokens"] = 4096
            if self._use_structured:
                kwargs["response_format"] = {"type": "json_schema", "json_schema": REPAIR_SCHEMA}
            response = client.chat.completions.create(**kwargs)
            raw_content = response.choices[0].message.content or ""
            if self._use_structured and raw_content:
                try:
                    raw_content = json.loads(raw_content).get("corrected_code", raw_content)
                except (json.JSONDecodeError, KeyError):
                    pass
            usage = response.usage
            resp = LLMResponse(
                content=raw_content,
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                model=response.model,
                provider="openai",
            )
        except Exception as e:
            logger.error("OpenAI error [%s]: %s", self._model_id, e)
            resp = LLMResponse(content="", provider="openai", model=self._model_id, error=str(e))
        if tracker:
            tracker.record(resp)
        return resp
