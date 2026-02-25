from __future__ import annotations
from openai import OpenAI
from app.core.config import settings

class OpenAiLlmClient:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

    def enabled(self) -> bool:
        return self.client is not None

    def generate_unified_diff(self, model: str, prompt: str) -> tuple[str, int]:
        if not self.client:
            return "", 0

        resp = self.client.responses.create(model=model, input=prompt)
        text = resp.output_text or ""
        diff = self._extract(text)

        tokens_used = 0
        try:
            usage = getattr(resp, "usage", None)
            if usage and getattr(usage, "total_tokens", None) is not None:
                tokens_used = int(usage.total_tokens)
        except Exception:
            tokens_used = 0

        return diff, tokens_used

    def _extract(self, text: str) -> str:
        idx = text.find("diff --git")
        return text[idx:].strip() if idx >= 0 else ""
