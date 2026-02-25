from openai import OpenAI
from app.core.config import settings

class LlmClient:
    def __init__(self):
        self.enabled = bool(settings.OPENAI_API_KEY)
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if self.enabled else None

    def generate_patch(self, model: str, prompt: str):
        if not self.enabled:
            return "", 0

        response = self.client.responses.create(
            model=model,
            input=prompt,
        )

        text = response.output_text or ""
        tokens = getattr(response.usage, "total_tokens", 0) if hasattr(response, "usage") else 0

        idx = text.find("diff --git")
        if idx >= 0:
            return text[idx:], tokens
        return "", tokens
