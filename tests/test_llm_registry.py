"""Tests for LLM provider registry (QALLM-12b)."""

import pytest

from app.llm.base import LLMProvider, LLMResponse
from app.llm.registry import LLMProviderRegistry


class FakeProvider(LLMProvider):
    def __init__(self, name: str = "fake", configured: bool = True):
        self._name = name
        self._configured = configured

    def name(self) -> str:
        return self._name

    def is_configured(self) -> bool:
        return self._configured

    def chat(self, system, user, tracker=None):
        return LLMResponse(content="fake reply", provider=self._name)


def test_register_and_list():
    reg = LLMProviderRegistry()
    reg.register(FakeProvider("a"))
    reg.register(FakeProvider("b"))
    assert reg.list() == ["a", "b"]


def test_get_existing():
    reg = LLMProviderRegistry()
    reg.register(FakeProvider("openai"))
    assert reg.get("openai") is not None
    assert reg.get("openai").name() == "openai"


def test_get_missing_returns_none():
    reg = LLMProviderRegistry()
    assert reg.get("nonexistent") is None


def test_pick_raises_on_unknown():
    reg = LLMProviderRegistry()
    reg.register(FakeProvider("openai"))
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        reg.pick("nonexistent")


def test_pick_raises_on_unconfigured():
    reg = LLMProviderRegistry()
    reg.register(FakeProvider("openai", configured=False))
    with pytest.raises(ValueError, match="not configured"):
        reg.pick("openai")


def test_list_configured():
    reg = LLMProviderRegistry()
    reg.register(FakeProvider("a", configured=True))
    reg.register(FakeProvider("b", configured=False))
    reg.register(FakeProvider("c", configured=True))
    assert reg.list_configured() == ["a", "c"]


def test_get_default_returns_first_configured():
    reg = LLMProviderRegistry()
    reg.register(FakeProvider("a", configured=False))
    reg.register(FakeProvider("b", configured=True))
    assert reg.get_default().name() == "b"


def test_get_default_none_if_nothing_configured():
    reg = LLMProviderRegistry()
    reg.register(FakeProvider("a", configured=False))
    assert reg.get_default() is None


def test_providers_endpoint():
    """GET /api/llm/providers returns available and configured."""
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    r = client.get("/api/llm/providers")
    assert r.status_code == 200
    data = r.json()
    assert "available" in data
    assert "configured" in data
    assert "default" in data
    assert "openai" in data["available"]
    assert "anthropic" in data["available"]
