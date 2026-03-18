from __future__ import annotations

from app.llm.base import LLMModel


class LLMModelRegistry:
    def __init__(self) -> None:
        self._models: dict[str, LLMModel] = {}

    def register(self, model: LLMModel) -> None:
        self._models[model.name()] = model

    def get(self, name: str) -> LLMModel | None:
        return self._models.get(name)

    def pick(self, name: str) -> LLMModel:
        m = self.get(name)
        if m is None:
            raise ValueError(f"Unknown model '{name}'. Available: {', '.join(self.list())}")
        if not m.is_configured():
            raise ValueError(f"Model '{name}' is not configured.")
        return m

    def list(self) -> list[str]:
        return list(self._models.keys())

    def list_configured(self) -> list[str]:
        return [n for n, m in self._models.items() if m.is_configured()]

    def get_default(self) -> LLMModel | None:
        for m in self._models.values():
            if m.is_configured():
                return m
        return None
