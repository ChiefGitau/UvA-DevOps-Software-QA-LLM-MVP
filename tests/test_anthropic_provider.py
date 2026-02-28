"""Tests for Anthropic provider (QALLM-12b)."""

from unittest.mock import MagicMock, patch

from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base import TokenTracker


def test_name():
    assert AnthropicProvider().name() == "anthropic"


def test_not_configured_when_no_key(monkeypatch):
    monkeypatch.setattr("app.llm.anthropic_provider.settings.ANTHROPIC_API_KEY", None)
    p = AnthropicProvider()
    assert not p.is_configured()


def test_configured_when_key_set(monkeypatch):
    monkeypatch.setattr("app.llm.anthropic_provider.settings.ANTHROPIC_API_KEY", "sk-ant-test")
    p = AnthropicProvider()
    assert p.is_configured()


def test_chat_returns_error_when_not_configured(monkeypatch):
    monkeypatch.setattr("app.llm.anthropic_provider.settings.ANTHROPIC_API_KEY", None)
    resp = AnthropicProvider().chat("sys", "user")
    assert resp.error is not None
    assert "not configured" in resp.error
    assert resp.provider == "anthropic"


def test_chat_respects_budget(monkeypatch):
    monkeypatch.setattr("app.llm.anthropic_provider.settings.ANTHROPIC_API_KEY", "sk-ant-test")
    tracker = TokenTracker(budget=100)
    tracker.total_input = 100
    resp = AnthropicProvider().chat("sys", "user", tracker)
    assert "exhausted" in resp.error


def test_chat_calls_anthropic_api(monkeypatch):
    monkeypatch.setattr("app.llm.anthropic_provider.settings.ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setattr("app.llm.anthropic_provider.settings.ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")

    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = "fixed code here"

    mock_usage = MagicMock()
    mock_usage.input_tokens = 60
    mock_usage.output_tokens = 40

    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_response.usage = mock_usage
    mock_response.model = "claude-3-5-haiku-20241022"

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    mock_anthropic_mod = MagicMock()
    mock_anthropic_mod.Anthropic.return_value = mock_client

    with patch.dict("sys.modules", {"anthropic": mock_anthropic_mod}):
        tracker = TokenTracker(budget=1000)
        resp = AnthropicProvider().chat("sys", "fix this", tracker)

    assert resp.content == "fixed code here"
    assert resp.input_tokens == 60
    assert resp.output_tokens == 40
    assert resp.provider == "anthropic"
    assert tracker.total_tokens == 100
