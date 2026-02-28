"""Tests for OpenAI provider (QALLM-12b — replaces old openai_client tests).

Tests target the actual provider class, not the backward-compat shim.
"""

from unittest.mock import MagicMock, patch

from app.llm.base import TokenTracker
from app.llm.openai_provider import OpenAIProvider


def test_name():
    assert OpenAIProvider().name() == "openai"


def test_token_tracker_accumulates():
    from app.llm.base import LLMResponse

    t = TokenTracker(budget=1000)
    t.record(LLMResponse(content="x", input_tokens=100, output_tokens=50, model="m"))
    t.record(LLMResponse(content="y", input_tokens=200, output_tokens=80, model="m"))
    assert t.total_input == 300
    assert t.total_output == 130
    assert t.total_tokens == 430
    assert t.remaining == 570
    assert t.calls == 2
    assert t.errors == 0


def test_token_tracker_counts_errors():
    from app.llm.base import LLMResponse

    t = TokenTracker(budget=1000)
    t.record(LLMResponse(content="", error="fail", model="m"))
    assert t.errors == 1
    assert t.calls == 1


def test_token_tracker_to_dict():
    from app.llm.base import LLMResponse

    t = TokenTracker(budget=500)
    t.record(LLMResponse(content="x", input_tokens=100, output_tokens=50, model="m"))
    d = t.to_dict()
    assert d["budget"] == 500
    assert d["total_tokens"] == 150
    assert d["remaining"] == 350


def test_chat_returns_error_when_not_configured(monkeypatch):
    monkeypatch.setattr("app.llm.openai_provider.settings.OPENAI_API_KEY", None)
    resp = OpenAIProvider().chat("sys", "user")
    assert resp.error is not None
    assert "not configured" in resp.error
    assert resp.provider == "openai"


def test_chat_respects_budget(monkeypatch):
    monkeypatch.setattr("app.llm.openai_provider.settings.OPENAI_API_KEY", "sk-test")
    tracker = TokenTracker(budget=100)
    tracker.total_input = 100
    resp = OpenAIProvider().chat("sys", "user", tracker)
    assert "exhausted" in resp.error


def test_chat_calls_openai_api(monkeypatch):
    monkeypatch.setattr("app.llm.openai_provider.settings.OPENAI_API_KEY", "sk-test")

    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 50
    mock_usage.completion_tokens = 30

    mock_choice = MagicMock()
    mock_choice.message.content = "fixed code here"

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage
    mock_response.model = "gpt-4o-mini"

    mock_client_instance = MagicMock()
    mock_client_instance.chat.completions.create.return_value = mock_response

    mock_openai_mod = MagicMock()
    mock_openai_mod.OpenAI.return_value = mock_client_instance

    with patch.dict("sys.modules", {"openai": mock_openai_mod}):
        tracker = TokenTracker(budget=1000)
        resp = OpenAIProvider().chat("sys", "fix this", tracker)

    assert resp.content == "fixed code here"
    assert resp.input_tokens == 50
    assert resp.output_tokens == 30
    assert resp.error is None
    assert resp.provider == "openai"
    assert tracker.total_tokens == 80


def test_backward_compat_shim():
    """The old openai_client module still exports the right symbols."""
    from app.llm.openai_client import LLMResponse, TokenTracker, chat_completion

    assert callable(chat_completion)
    assert LLMResponse is not None
    assert TokenTracker is not None
