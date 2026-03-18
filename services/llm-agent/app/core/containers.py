from __future__ import annotations


def build_llm_registry():
    from app.llm.anthropic_provider import AnthropicModel
    from app.llm.ollama_provider import OllamaModel
    from app.llm.openai_provider import OpenAIModel
    from app.llm.registry import LLMModelRegistry

    registry = LLMModelRegistry()
    registry.register(OpenAIModel(model_id="gpt-4o-mini"))
    registry.register(OpenAIModel(model_id="gpt-5-mini", use_structured=True))
    registry.register(AnthropicModel())
    registry.register(OllamaModel())
    return registry
